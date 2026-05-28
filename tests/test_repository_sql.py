from types import SimpleNamespace

from app.repositories.catalog_listings import CatalogListingsRepository


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
