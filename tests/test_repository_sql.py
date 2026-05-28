from types import SimpleNamespace

from app.repositories.catalog_listings import CatalogListingsRepository
from app.utils.identity import listing_identity_key


def test_eav_current_query_uses_external_id_without_source_attribute() -> None:
    repository = CatalogListingsRepository.__new__(CatalogListingsRepository)
    statement = repository.build_eav_current_query((35,))
    sql = str(statement)
    assert "ext_def.slug = 'external_id'" in sql
    assert "source_def.slug = 'source'" not in sql
    assert ":source AS source" in sql
    assert "l.category_id IN" in sql


def test_write_guard_blocks_when_disabled() -> None:
    from app.repositories.catalog_listings import (
        CatalogWritesDisabledError,
        assert_catalog_writes_allowed,
    )

    settings = SimpleNamespace(sync_allow_catalog_writes=False)
    try:
        assert_catalog_writes_allowed(settings)  # type: ignore[arg-type]
    except CatalogWritesDisabledError as exc:
        assert "catalog writes are disabled" in str(exc)
    else:
        raise AssertionError("write guard did not raise")


class FakeCurrentResult:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows

    def mappings(self) -> "FakeCurrentResult":
        return self

    def all(self) -> list[dict[str, object]]:
        return self.rows


class FakeCurrentSession:
    def execute(self, statement: object, params: dict[str, object]) -> FakeCurrentResult:
        return FakeCurrentResult(
            [
                _listing_row(1, "A-1", 35),
                _listing_row(2, "A-1", 35),
                _listing_row(3, "A-1", 36),
            ]
        )


def _listing_row(listing_id: int, external_id: str, category_id: int) -> dict[str, object]:
    return {
        "id": listing_id,
        "external_id": external_id,
        "source": "autoland",
        "user_id": 77,
        "category_id": category_id,
        "title": "Part",
        "description": "Description",
        "price": None,
        "currency": "KGS",
        "status": "active",
        "slug": "part",
    }


def test_current_lookup_identity_includes_category_and_skips_ambiguous_duplicates() -> None:
    repository = CatalogListingsRepository.__new__(CatalogListingsRepository)
    repository.session = FakeCurrentSession()
    repository.settings = SimpleNamespace()
    repository.last_duplicate_external_ids = ()
    repository.get_listing_attributes = lambda listing_id: {"external_id": "A-1"}  # type: ignore[method-assign]
    repository.get_listing_images = lambda listing_id: []  # type: ignore[method-assign]

    current = repository.get_current_by_provider(
        provider="autoland",
        user_id=77,
        category_ids=(35, 36),
    )

    assert listing_identity_key(35, "A-1") not in current
    assert listing_identity_key(36, "A-1") in current
    assert repository.last_duplicate_external_ids == (listing_identity_key(35, "A-1"),)
