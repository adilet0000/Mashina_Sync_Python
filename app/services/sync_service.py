import logging
from collections.abc import Iterable
from contextlib import nullcontext
from typing import Any, Protocol

from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.config.catalog_mapping import map_type_id
from app.config.providers import get_provider_config, list_provider_configs
from app.db.safety import describe_database_url
from app.db.session import create_catalog_session_factory
from app.dto import CatalogListingPayload, LegacyAd, SyncResult
from app.mappers import ListingMapper
from app.providers import (
    AllmotorsProviderAdapter,
    AutohubProviderAdapter,
    AutolandProviderAdapter,
    AutoshinaProviderAdapter,
    AvtoinstallProviderAdapter,
    BanzaimotorsProviderAdapter,
    BavariaProviderAdapter,
    DetalKgProviderAdapter,
    KiaProviderAdapter,
    LexusProviderAdapter,
    NotImplementedProviderAdapter,
    OkayamaomskProviderAdapter,
    ProviderAdapter,
    ProviderNotImplementedError,
    ShinabarProviderAdapter,
    ShredderProviderAdapter,
    ToyotaProviderAdapter,
    ToyotaTradeinProviderAdapter,
)
from app.repositories.catalog_listings import CatalogListingsRepository, CatalogWritesDisabledError
from app.services.diff_service import DiffService, SyncPlan
from app.services.verification_service import VerificationService

logger = logging.getLogger(__name__)


class RepositoryFactory(Protocol):
    def __call__(self, session: Session, settings: Settings) -> CatalogListingsRepository: ...


class SyncTargetError(RuntimeError):
    pass


class SyncService:
    def __init__(
        self,
        settings: Settings,
        *,
        session_factory: sessionmaker[Session] | None = None,
        diff_service: DiffService | None = None,
        mapper: ListingMapper | None = None,
        verification_service: VerificationService | None = None,
        adapters: dict[str, ProviderAdapter] | None = None,
        repository_factory: RepositoryFactory | None = None,
    ) -> None:
        self.settings = settings
        self.session_factory = session_factory or create_catalog_session_factory(settings)
        self.diff_service = diff_service or DiffService()
        self.mapper = mapper or ListingMapper(settings)
        self.verification_service = verification_service or VerificationService()
        self.adapters = adapters or {}
        self.repository_factory = repository_factory or CatalogListingsRepository

    def sync_provider(
        self,
        provider: str,
        *,
        dry_run: bool | None = None,
        limit: int | None = None,
        verify: bool = False,
        debug_record: str | None = None,
    ) -> SyncResult:
        provider_config = get_provider_config(provider)
        effective_dry_run = self._effective_dry_run(dry_run)
        result = SyncResult(provider=provider_config.key, dry_run=effective_dry_run, verify=verify)
        try:
            self._ensure_can_run(effective_dry_run)
            adapter = self._adapter_for_provider(provider_config.key)
            records = tuple(adapter.fetch_ads(limit=limit))
        except ProviderNotImplementedError:
            result.warnings.append(
                "provider adapter is not implemented yet; "
                "no provider rows were read and no DB writes ran"
            )
            if limit is not None:
                result.warnings.append(f"limit={limit} accepted by core skeleton")
            if debug_record:
                result.warnings.append(f"debug_record={debug_record} accepted by core skeleton")
            return result
        except Exception as exc:  # noqa: BLE001 - sync result should expose provider failures
            result.errors.append(str(exc))
            result.failed_count += 1
            return result

        stats = getattr(adapter, "last_stats", None)
        return self.sync_records(
            provider=provider_config.key,
            records=records,
            dry_run=effective_dry_run,
            verify=verify,
            debug_record=debug_record,
            read_count=getattr(stats, "read_count", None),
            skipped_count=getattr(stats, "skipped_count", 0),
            warnings=tuple(getattr(stats, "warnings", ())),
        )

    def sync_records(
        self,
        *,
        provider: str,
        records: Iterable[LegacyAd],
        dry_run: bool,
        verify: bool = False,
        debug_record: str | None = None,
        read_count: int | None = None,
        skipped_count: int = 0,
        warnings: tuple[str, ...] = (),
    ) -> SyncResult:
        result = SyncResult(provider=provider, dry_run=dry_run, verify=verify)
        try:
            self._ensure_can_run(dry_run)
        except Exception as exc:  # noqa: BLE001
            result.errors.append(str(exc))
            result.failed_count += 1
            return result

        legacy_ads = tuple(records)
        result.read_count = read_count if read_count is not None else len(legacy_ads)
        result.skipped_count = skipped_count
        result.warnings.extend(warnings)
        result.legacy_samples = [self._legacy_sample(ad) for ad in legacy_ads[:3]]
        payloads = self._map_payloads(legacy_ads, result, debug_record=debug_record)
        result.valid_count = len(payloads)
        result.payload_samples = [self._payload_sample(payload) for payload in payloads[:3]]

        if not payloads:
            return result

        category_ids = tuple(sorted({payload.category_id for payload in payloads}))
        user_id = payloads[0].user_id
        result.safety_summary = self._build_safety_summary(
            provider=provider,
            user_id=user_id,
            category_ids=category_ids,
            dry_run=dry_run,
        )

        if self.session_factory is None:
            result.errors.append(
                "CATALOG_DATABASE_URL is not configured; cannot read current catalog rows"
            )
            result.failed_count += 1
            return result

        with self.session_factory() as session:
            repository = self.repository_factory(session, self.settings)
            current = repository.get_current_by_provider(
                provider=provider,
                user_id=user_id,
                category_ids=category_ids,
            )
            plan = self.diff_service.diff(payloads, current)
            self._apply_plan_counts(result, plan)
            result.diff_samples = self._diff_samples(plan)
            result.warnings.extend(plan.warnings)

            if dry_run:
                return result

            logger.warning("catalog write preflight: %s", result.safety_summary)
            self._write_plan_in_batches(session, repository, plan, result)

            if verify:
                changed_payloads = tuple(plan.insert) + tuple(
                    update.payload for update in plan.update
                )
                report = self.verification_service.verify_sync(
                    repository,
                    payloads=changed_payloads,
                    deactivated_listings=tuple(plan.deactivate),
                    inactive_status=self.settings.sync_catalog_inactive_status,
                )
                result.verified_count = report.verified_count
                result.verification_failed_count = report.failed_count
                result.errors.extend(report.errors)
        return result

    def sync_all(
        self,
        *,
        dry_run: bool | None = None,
        limit: int | None = None,
        verify: bool = False,
    ) -> tuple[SyncResult, ...]:
        return tuple(
            self.sync_provider(
                provider_config.key,
                dry_run=dry_run,
                limit=limit,
                verify=verify,
            )
            for provider_config in list_provider_configs()
        )

    def _adapter_for_provider(self, provider: str) -> ProviderAdapter:
        if provider in self.adapters:
            return self.adapters[provider]
        adapter_classes: dict[str, type[ProviderAdapter]] = {
            "allmotors": AllmotorsProviderAdapter,
            "autohub": AutohubProviderAdapter,
            "autoland": AutolandProviderAdapter,
            "autoshina": AutoshinaProviderAdapter,
            "avtoinstall": AvtoinstallProviderAdapter,
            "banzaimotors": BanzaimotorsProviderAdapter,
            "bavaria": BavariaProviderAdapter,
            "detalkg": DetalKgProviderAdapter,
            "kia": KiaProviderAdapter,
            "lexus": LexusProviderAdapter,
            "okayamaomsk": OkayamaomskProviderAdapter,
            "shinabar": ShinabarProviderAdapter,
            "shredder": ShredderProviderAdapter,
            "toyota": ToyotaProviderAdapter,
            "toyota_tradein": ToyotaTradeinProviderAdapter,
        }
        if provider in adapter_classes:
            return adapter_classes[provider](self.settings)
        return NotImplementedProviderAdapter(provider)

    def _effective_dry_run(self, dry_run: bool | None) -> bool:
        if dry_run is True:
            return True
        if dry_run is None:
            return self.settings.sync_dry_run
        return False

    def _ensure_can_run(self, dry_run: bool) -> None:
        if not self.settings.is_catalog_target:
            raise SyncTargetError(
                f"unsupported SYNC_TARGET={self.settings.sync_target!r}; "
                "only 'catalog' is supported"
            )
        if dry_run:
            return
        db_info = describe_database_url(self.settings.effective_catalog_database_url)
        if self.settings.sync_dry_run:
            raise CatalogWritesDisabledError(
                f"real catalog writes require SYNC_DRY_RUN=0; target={db_info.as_safe_string()}"
            )
        if not self.settings.sync_allow_catalog_writes:
            raise CatalogWritesDisabledError(
                "real catalog writes require SYNC_ALLOW_CATALOG_WRITES=1; "
                f"target={db_info.as_safe_string()}"
            )

    def _map_payloads(
        self,
        legacy_ads: tuple[LegacyAd, ...],
        result: SyncResult,
        *,
        debug_record: str | None = None,
    ) -> tuple[CatalogListingPayload, ...]:
        payloads: list[CatalogListingPayload] = []
        for ad in legacy_ads:
            if debug_record and ad.external_id != debug_record:
                continue
            try:
                map_type_id(ad.type_id)
                payloads.append(self.mapper.to_catalog_payload(ad))
                result.warnings.extend(ad.warnings)
                result.errors.extend(ad.errors)
            except Exception as exc:  # noqa: BLE001 - one bad provider row can be skipped safely
                result.skipped_count += 1
                result.warnings.append(f"skipped external_id={ad.external_id}: {exc}")
        return tuple(payloads)

    def _apply_plan_counts(self, result: SyncResult, plan: SyncPlan) -> None:
        result.inserted_count = len(plan.insert)
        result.updated_count = len(plan.update)
        result.unchanged_count = len(plan.unchanged)
        result.deactivated_count = len(plan.deactivate)
        result.image_inserted_count = len(plan.image_insert)
        result.image_deactivated_count = len(plan.image_deactivate)

    def _write_plan_in_batches(
        self,
        session: Session,
        repository: CatalogListingsRepository,
        plan: SyncPlan,
        result: SyncResult,
    ) -> None:
        operations: list[tuple[str, Any]] = []
        operations.extend(("insert", payload) for payload in plan.insert)
        operations.extend(("update", update) for update in plan.update)
        operations.extend(("image_insert", image_insert) for image_insert in plan.image_insert)
        operations.extend(
            ("image_deactivate", image_deactivate) for image_deactivate in plan.image_deactivate
        )
        operations.extend(("deactivate", listing) for listing in plan.deactivate)

        batch_size = max(1, self.settings.sync_batch_size)
        for start in range(0, len(operations), batch_size):
            batch = operations[start : start + batch_size]
            try:
                with session.begin_nested() if session.in_transaction() else nullcontext():
                    self._write_operations(repository, batch)
                session.commit()
            except Exception as exc:  # noqa: BLE001
                session.rollback()
                result.warnings.append(
                    f"batch write failed at offset={start}: {exc}; retrying records individually"
                )
                self._retry_operations_individually(session, repository, batch, result)

    def _retry_operations_individually(
        self,
        session: Session,
        repository: CatalogListingsRepository,
        operations: list[tuple[str, Any]],
        result: SyncResult,
    ) -> None:
        for operation in operations:
            try:
                with session.begin_nested() if session.in_transaction() else nullcontext():
                    self._write_operations(repository, [operation])
                session.commit()
            except Exception as exc:  # noqa: BLE001
                session.rollback()
                result.failed_count += 1
                result.errors.append(f"record-level write failed operation={operation[0]}: {exc}")

    def _write_operations(
        self,
        repository: CatalogListingsRepository,
        operations: list[tuple[str, Any]],
    ) -> None:
        for operation, payload in operations:
            if operation == "insert":
                repository.insert_listing(payload)
            elif operation == "update":
                repository.update_listing(
                    payload.existing.id,
                    payload.payload,
                    changed_fields=payload.changed_fields,
                )
                for image in payload.payload.images:
                    repository.insert_image(payload.existing.id, image)
            elif operation == "image_insert":
                repository.insert_image(payload.listing_id, payload.payload)
            elif operation == "image_deactivate":
                repository.deactivate_missing_images(
                    listing_id=payload.listing_id,
                    current_urls={payload.image.external_url},
                    new_urls=set(),
                )
            elif operation == "deactivate":
                repository.deactivate_listing(payload.id)
            else:
                raise ValueError(f"unsupported write operation={operation!r}")

    def _build_safety_summary(
        self,
        *,
        provider: str,
        user_id: int,
        category_ids: tuple[int, ...],
        dry_run: bool,
    ) -> dict[str, Any]:
        db_info = describe_database_url(self.settings.effective_catalog_database_url)
        return {
            "database": db_info.as_safe_string(),
            "database_is_local": db_info.is_local,
            "provider": provider,
            "user_id": user_id,
            "category_ids": list(category_ids),
            "mode": "dry-run" if dry_run else "write",
            "sync_allow_catalog_writes": self.settings.sync_allow_catalog_writes,
        }

    def _legacy_sample(self, ad: LegacyAd) -> dict[str, Any]:
        return {
            "source": ad.source,
            "external_id": ad.external_id,
            "type_id": ad.type_id,
            "name": ad.name,
            "price": ad.price,
            "currency": ad.currency,
            "make": ad.make,
            "model": ad.model,
            "condition": ad.condition,
            "images_count": len(ad.images),
        }

    def _payload_sample(self, payload: CatalogListingPayload) -> dict[str, Any]:
        return {
            "source": payload.source,
            "external_id": payload.external_id,
            "user_id": payload.user_id,
            "category_id": payload.category_id,
            "title": payload.title,
            "price": payload.price,
            "currency": payload.currency,
            "status": payload.status,
            "attributes": [attribute.slug for attribute in payload.attributes],
            "images_count": len(payload.images),
        }

    def _diff_samples(self, plan: SyncPlan) -> list[dict[str, Any]]:
        samples: list[dict[str, Any]] = []
        samples.extend(
            {"action": "insert", "external_id": payload.external_id} for payload in plan.insert[:3]
        )
        samples.extend(
            {
                "action": "update",
                "external_id": update.payload.external_id,
                "changed_fields": update.changed_fields,
            }
            for update in plan.update[: max(0, 3 - len(samples))]
        )
        samples.extend(
            {
                "action": "deactivate",
                "external_id": listing.external_id,
                "listing_id": listing.id,
            }
            for listing in plan.deactivate[: max(0, 3 - len(samples))]
        )
        samples.extend(
            {"action": "unchanged", "external_id": payload.external_id}
            for payload in plan.unchanged[: max(0, 3 - len(samples))]
        )
        return samples[:3]
