from decimal import Decimal

from app.dto import CatalogAttributePayload, CatalogImagePayload, CatalogListingPayload
from app.repositories.catalog_listings import ExistingImage, ExistingListing
from app.services.diff_service import DiffService


def _payload(price: Decimal = Decimal("100")) -> CatalogListingPayload:
    return CatalogListingPayload(
        source="autohub",
        external_id="A-1",
        user_id=10,
        category_id=35,
        title="Part",
        description="Part description",
        price=price,
        currency="KGS",
        status="active",
        attributes=(CatalogAttributePayload(slug="external_id", value="A-1"),),
        images=(
            CatalogImagePayload(
                external_url="https://example.test/a.jpg",
                priority=0,
                hash="hash-a",
                status=1,
                is_blurred=False,
                user_id=10,
            ),
        ),
    )


def _existing(price: Decimal = Decimal("100")) -> ExistingListing:
    return ExistingListing(
        id=1,
        source="autohub",
        external_id="A-1",
        user_id=10,
        category_id=35,
        title="Part",
        description="Part description",
        price=price,
        currency="KGS",
        status="active",
        attributes={"external_id": "A-1"},
        images=(
            ExistingImage(
                id=1,
                external_url="https://example.test/a.jpg",
                hash="hash-a",
                priority=0,
                status=1,
            ),
        ),
    )


def test_diff_marks_insert_when_listing_missing() -> None:
    plan = DiffService().diff((_payload(),), {})
    assert len(plan.insert) == 1
    assert not plan.update


def test_diff_marks_unchanged_when_payload_matches() -> None:
    plan = DiffService().diff((_payload(),), {"A-1": _existing()})
    assert len(plan.unchanged) == 1
    assert not plan.update


def test_diff_marks_update_when_nonvolatile_field_changes() -> None:
    plan = DiffService().diff((_payload(price=Decimal("150")),), {"A-1": _existing()})
    assert len(plan.update) == 1
    assert "price" in plan.update[0].changed_fields


def test_diff_detects_missing_current_listing() -> None:
    plan = DiffService().diff((), {"A-1": _existing()})
    assert len(plan.deactivate) == 1
