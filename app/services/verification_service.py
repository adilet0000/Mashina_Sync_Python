from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from app.dto import CatalogAttributePayload, CatalogListingPayload
from app.repositories.catalog_listings import CatalogListingsRepository, ExistingListing


@dataclass
class VerificationReport:
    verified_count: int = 0
    failed_count: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.failed_count == 0 and not self.errors


class VerificationService:
    def verify_sync(
        self,
        repository: CatalogListingsRepository,
        *,
        payloads: tuple[CatalogListingPayload, ...],
        deactivated_listings: tuple[ExistingListing, ...],
        inactive_status: str,
    ) -> VerificationReport:
        report = self.verify_payloads(repository, payloads)
        deactivation_report = self.verify_deactivated_listings(
            repository,
            deactivated_listings,
            inactive_status=inactive_status,
        )
        report.verified_count += deactivation_report.verified_count
        report.failed_count += deactivation_report.failed_count
        report.errors.extend(deactivation_report.errors)
        return report

    def verify_payloads(
        self,
        repository: CatalogListingsRepository,
        payloads: tuple[CatalogListingPayload, ...],
    ) -> VerificationReport:
        report = VerificationReport()
        for payload in payloads:
            listing = repository.get_by_external_id(
                provider=payload.source,
                user_id=payload.user_id,
                category_id=payload.category_id,
                external_id=payload.external_id,
            )
            if listing is None:
                report.failed_count += 1
                report.errors.append(
                    f"listing was not found after write source={payload.source} "
                    f"external_id={payload.external_id}"
                )
                continue

            mismatches = self._mismatches(payload, listing)
            if mismatches:
                report.failed_count += 1
                report.errors.extend(
                    f"listing_id={listing.id} external_id={payload.external_id}: {mismatch}"
                    for mismatch in mismatches
                )
                continue
            report.verified_count += 1
        return report

    def verify_deactivated_listings(
        self,
        repository: CatalogListingsRepository,
        listings: tuple[ExistingListing, ...],
        *,
        inactive_status: str,
    ) -> VerificationReport:
        report = VerificationReport()
        for listing in listings:
            current = repository.get_by_id(listing.id)
            if current is None:
                report.failed_count += 1
                report.errors.append(f"deactivated listing_id={listing.id} was not found")
                continue
            if current.status != inactive_status:
                report.failed_count += 1
                report.errors.append(
                    f"listing_id={listing.id} inactive status mismatch "
                    f"expected={inactive_status!r} actual={current.status!r}"
                )
                continue
            report.verified_count += 1
        return report

    def _mismatches(
        self,
        payload: CatalogListingPayload,
        listing: ExistingListing,
    ) -> list[str]:
        mismatches: list[str] = []
        attributes: dict[str, object] = listing.attributes
        if attributes.get("external_id") != payload.external_id:
            mismatches.append("external_id attribute mismatch")
        if listing.source and listing.source != payload.source:
            mismatches.append("provider identity mismatch")
        if listing.title != payload.title:
            mismatches.append("title mismatch")
        if listing.category_id != payload.category_id:
            mismatches.append("category_id mismatch")
        if listing.user_id != payload.user_id:
            mismatches.append("user_id mismatch")
        if listing.description != payload.description:
            mismatches.append("description mismatch")
        if self._decimal_or_none(listing.price) != self._decimal_or_none(payload.price):
            mismatches.append(f"price mismatch expected={payload.price!r} actual={listing.price!r}")
        if listing.currency != payload.currency:
            mismatches.append("currency mismatch")
        if listing.status != payload.status:
            mismatches.append(
                f"status mismatch expected={payload.status!r} actual={listing.status!r}"
            )
        mismatches.extend(self._attribute_mismatches(payload, attributes))
        mismatches.extend(self._image_mismatches(payload, listing))
        return mismatches

    def _attribute_mismatches(
        self,
        payload: CatalogListingPayload,
        attributes: dict[str, object],
    ) -> list[str]:
        mismatches: list[str] = []
        for attribute in payload.attributes:
            if attribute.slug not in attributes:
                mismatches.append(f"attribute missing slug={attribute.slug}")
                continue
            if not self._should_compare_attribute_value(attribute):
                continue
            expected = self._normalize_attribute_value(attribute.value)
            actual = self._normalize_attribute_value(attributes.get(attribute.slug))
            if actual != expected:
                mismatches.append(
                    f"attribute value mismatch slug={attribute.slug} "
                    f"expected={expected!r} actual={actual!r}"
                )
        return mismatches

    def _image_mismatches(
        self,
        payload: CatalogListingPayload,
        listing: ExistingListing,
    ) -> list[str]:
        mismatches: list[str] = []
        saved_by_url = {image.external_url: image for image in listing.images}
        if len(saved_by_url) < len(payload.images):
            mismatches.append(
                f"image count mismatch expected_at_least={len(payload.images)} "
                f"actual={len(saved_by_url)}"
            )
        for image in payload.images:
            saved_image = saved_by_url.get(image.external_url)
            if saved_image is None:
                mismatches.append(f"image missing external_url={image.external_url}")
                continue
            if saved_image.priority != image.priority:
                mismatches.append(
                    f"image priority mismatch external_url={image.external_url} "
                    f"expected={image.priority} actual={saved_image.priority}"
                )
            if saved_image.hash != image.hash:
                mismatches.append(f"image hash mismatch external_url={image.external_url}")
            if saved_image.status != image.status:
                mismatches.append(
                    f"image status mismatch external_url={image.external_url} "
                    f"expected={image.status} actual={saved_image.status}"
                )
            if saved_image.user_id is not None and saved_image.user_id != image.user_id:
                mismatches.append(
                    f"image user_id mismatch external_url={image.external_url} "
                    f"expected={image.user_id} actual={saved_image.user_id}"
                )
        return mismatches

    def _decimal_or_none(self, value: object) -> Decimal | None:
        if value in (None, ""):
            return None
        return Decimal(str(value))

    def _should_compare_attribute_value(self, attribute: CatalogAttributePayload) -> bool:
        if attribute.option_old_mysql_id is not None or attribute.option_value is not None:
            return False
        return attribute.value is not None

    def _normalize_attribute_value(self, value: Any) -> Any:
        if isinstance(value, bool):
            return value
        if isinstance(value, Decimal):
            return str(value.normalize())
        if isinstance(value, int | float):
            return str(Decimal(str(value)).normalize())
        if isinstance(value, dict):
            return value
        if isinstance(value, list | tuple):
            return tuple(value)
        if value in (None, ""):
            return value
        return str(value)
