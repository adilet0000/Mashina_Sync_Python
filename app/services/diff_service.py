from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.dto import CatalogImagePayload, CatalogListingPayload
from app.repositories.catalog_listings import ExistingImage, ExistingListing


@dataclass(frozen=True)
class ListingUpdate:
    existing: ExistingListing
    payload: CatalogListingPayload
    changed_fields: tuple[str, ...]


@dataclass(frozen=True)
class ImageInsert:
    listing_id: int
    payload: CatalogImagePayload


@dataclass(frozen=True)
class ImageDeactivate:
    listing_id: int
    image: ExistingImage


@dataclass(frozen=True)
class SyncPlan:
    insert: tuple[CatalogListingPayload, ...] = ()
    update: tuple[ListingUpdate, ...] = ()
    unchanged: tuple[CatalogListingPayload, ...] = ()
    deactivate: tuple[ExistingListing, ...] = ()
    image_insert: tuple[ImageInsert, ...] = ()
    image_deactivate: tuple[ImageDeactivate, ...] = ()
    duplicate_external_ids: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


class DiffService:
    def diff(
        self,
        incoming: tuple[CatalogListingPayload, ...],
        current: dict[str, ExistingListing],
    ) -> SyncPlan:
        seen: set[str] = set()
        duplicate_external_ids: list[str] = []
        insert: list[CatalogListingPayload] = []
        update: list[ListingUpdate] = []
        unchanged: list[CatalogListingPayload] = []
        image_insert: list[ImageInsert] = []
        image_deactivate: list[ImageDeactivate] = []

        for payload in incoming:
            if payload.external_id in seen:
                duplicate_external_ids.append(payload.external_id)
                continue
            seen.add(payload.external_id)

            existing = current.get(payload.external_id)
            if existing is None:
                insert.append(payload)
                continue

            changed_fields = self.changed_fields(existing, payload)
            new_image_insert = self.image_inserts(existing, payload)
            new_image_deactivate = self.image_deactivations(existing, payload)
            if self.image_metadata_changed(existing, payload):
                changed_fields.append("images")
            image_insert.extend(new_image_insert)
            image_deactivate.extend(new_image_deactivate)
            if changed_fields or new_image_insert or new_image_deactivate:
                update.append(
                    ListingUpdate(
                        existing=existing,
                        payload=payload,
                        changed_fields=tuple(changed_fields),
                    )
                )
            else:
                unchanged.append(payload)

        deactivate = [listing for listing in current.values() if listing.external_id not in seen]
        warnings = tuple(
            f"duplicate provider external_id skipped: {external_id}"
            for external_id in duplicate_external_ids
        )
        return SyncPlan(
            insert=tuple(insert),
            update=tuple(update),
            unchanged=tuple(unchanged),
            deactivate=tuple(deactivate),
            image_insert=tuple(image_insert),
            image_deactivate=tuple(image_deactivate),
            duplicate_external_ids=tuple(duplicate_external_ids),
            warnings=warnings,
        )

    def changed_fields(
        self,
        existing: ExistingListing,
        payload: CatalogListingPayload,
    ) -> list[str]:
        changed: list[str] = []
        preserve_fields = set(payload.raw_legacy_ad.get("preserve_current_fields") or ())
        comparisons = {
            "title": (existing.title, payload.title),
            "description": (existing.description, payload.description),
            "price": (
                self._normalize_decimal(existing.price),
                self._normalize_decimal(payload.price),
            ),
            "currency": (existing.currency, payload.currency),
            "status": (existing.status, payload.status),
        }
        for field_name, (current_value, new_value) in comparisons.items():
            if field_name in preserve_fields:
                continue
            if current_value != new_value:
                changed.append(field_name)

        current_attributes = existing.attributes
        for attribute in payload.attributes:
            if attribute.slug in preserve_fields:
                continue
            current_value = current_attributes.get(attribute.slug)
            if self._normalize_attribute_value(current_value) != self._normalize_attribute_value(
                attribute.value
            ):
                changed.append(f"attr:{attribute.slug}")
        return changed

    def image_inserts(
        self,
        existing: ExistingListing,
        payload: CatalogListingPayload,
    ) -> tuple[ImageInsert, ...]:
        current_hashes = {image.hash for image in existing.images}
        return tuple(
            ImageInsert(listing_id=existing.id, payload=image)
            for image in payload.images
            if image.hash not in current_hashes
        )

    def image_deactivations(
        self,
        existing: ExistingListing,
        payload: CatalogListingPayload,
    ) -> tuple[ImageDeactivate, ...]:
        new_hashes = {image.hash for image in payload.images}
        return tuple(
            ImageDeactivate(listing_id=existing.id, image=image)
            for image in existing.images
            if image.hash not in new_hashes
        )

    def image_metadata_changed(
        self,
        existing: ExistingListing,
        payload: CatalogListingPayload,
    ) -> bool:
        existing_by_hash = {image.hash: image for image in existing.images}
        for image in payload.images:
            existing_image = existing_by_hash.get(image.hash)
            if existing_image is None:
                continue
            if existing_image.priority != image.priority:
                return True
            if existing_image.external_url != image.external_url:
                return True
            if existing_image.status != image.status:
                return True
        return False

    def _normalize_decimal(self, value: Any) -> Decimal | None:
        if value in (None, ""):
            return None
        return Decimal(str(value))

    def _normalize_attribute_value(self, value: Any) -> Any:
        if isinstance(value, bool):
            return value
        if isinstance(value, Decimal):
            return str(value.normalize())
        if isinstance(value, int | float):
            return str(Decimal(str(value)).normalize())
        if isinstance(value, list | tuple):
            return tuple(value)
        return value
