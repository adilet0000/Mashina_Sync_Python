from decimal import Decimal

from app.dto import CatalogAttributePayload, CatalogImagePayload, CatalogListingPayload
from app.repositories.catalog_listings import ExistingImage, ExistingListing
from app.services.verification_service import VerificationService


class FakeRepository:
    def __init__(self, listing: ExistingListing | None) -> None:
        self.listing = listing

    def get_by_external_id(
        self,
        *,
        provider: str,
        user_id: int,
        category_id: int,
        external_id: str,
    ) -> ExistingListing | None:
        return self.listing

    def get_by_id(self, listing_id: int) -> ExistingListing | None:
        return self.listing


def _payload() -> CatalogListingPayload:
    return CatalogListingPayload(
        source="autoland",
        external_id="A-1",
        user_id=77,
        category_id=35,
        title="Фара",
        description="Левая фара",
        price=Decimal("1200"),
        currency="KGS",
        status="active",
        attributes=(
            CatalogAttributePayload(
                slug="mileage",
                value={"value": "12345", "suffix": "км"},
            ),
        ),
        images=(
            CatalogImagePayload(
                external_url="https://img.test/1.jpg",
                priority=0,
                hash="hash-1",
                status=1,
                is_blurred=False,
                user_id=77,
            ),
        ),
    )


def _listing(status: str = "active") -> ExistingListing:
    return ExistingListing(
        id=101,
        source="autoland",
        external_id="A-1",
        user_id=77,
        category_id=35,
        title="Фара",
        description="Левая фара",
        price=Decimal("1200"),
        currency="KGS",
        status=status,
        attributes={
            "external_id": "A-1",
            "mileage": {"value": "12345", "suffix": "км"},
        },
        images=(
            ExistingImage(
                id=1,
                external_url="https://img.test/1.jpg",
                hash="hash-1",
                priority=0,
                status=1,
            ),
        ),
    )


def test_verification_service_confirms_written_payload() -> None:
    report = VerificationService().verify_payloads(
        FakeRepository(_listing()),  # type: ignore[arg-type]
        (_payload(),),
    )
    assert report.ok
    assert report.verified_count == 1


def test_verification_service_reports_mismatch() -> None:
    bad_listing = _listing()
    object.__setattr__(bad_listing, "currency", "USD")

    report = VerificationService().verify_payloads(
        FakeRepository(bad_listing),  # type: ignore[arg-type]
        (_payload(),),
    )
    assert not report.ok
    assert "currency mismatch" in report.errors[0]


def test_verification_service_confirms_deactivated_listing() -> None:
    report = VerificationService().verify_deactivated_listings(
        FakeRepository(_listing(status="inactive")),  # type: ignore[arg-type]
        (_listing(status="active"),),
        inactive_status="inactive",
    )
    assert report.ok
    assert report.verified_count == 1
