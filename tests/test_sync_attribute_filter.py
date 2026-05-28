from decimal import Decimal
from types import SimpleNamespace

from app.dto import CatalogAttributePayload, CatalogListingPayload, SyncResult
from app.services.sync_service import SyncService


class FakeResolver:
    def resolve_attribute_id_by_slug(self, slug: str) -> int | None:
        if slug == "external_id":
            return 1
        return None


def test_sync_filters_unsupported_optional_attributes_before_diff() -> None:
    payload = CatalogListingPayload(
        source="autoshina",
        external_id="T-1",
        user_id=77,
        category_id=24,
        title="Tire",
        description="Tire description\n\nХарактеристики:\nШирина шины: 205",
        price=Decimal("1000"),
        currency="KGS",
        status="active",
        attributes=(
            CatalogAttributePayload(slug="external_id", value="T-1"),
            CatalogAttributePayload(slug="tire_width", value="205"),
        ),
    )
    result = SyncResult(provider="autoshina", dry_run=True)
    repository = SimpleNamespace(reference_resolver=FakeResolver())
    service = SyncService.__new__(SyncService)

    filtered = service._filter_supported_attributes(  # noqa: SLF001
        (payload,),
        repository,  # type: ignore[arg-type]
        result,
    )

    assert [attribute.slug for attribute in filtered[0].attributes] == ["external_id"]
    assert result.warnings
    assert "tire_width" in result.warnings[0]
