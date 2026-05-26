from types import SimpleNamespace

import pytest
from app.dto import CatalogAttributePayload
from app.repositories.catalog_listings import CatalogListingsRepository


class FakeResult:
    def __init__(
        self,
        *,
        row: dict[str, object] | None = None,
        rows: list[dict[str, object]] | None = None,
        rowcount: int = 0,
    ) -> None:
        self.row = row
        self.rows = rows or ([] if row is None else [row])
        self.rowcount = rowcount

    def mappings(self) -> "FakeResult":
        return self

    def first(self) -> dict[str, object] | None:
        return self.row

    def one(self) -> dict[str, object]:
        if self.row is None:
            raise AssertionError("expected one row")
        return self.row

    def all(self) -> list[dict[str, object]]:
        return self.rows


class FakeSession:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def execute(self, statement: object, params: dict[str, object]) -> FakeResult:
        sql = str(statement)
        self.calls.append((sql, params))
        if "SELECT id" in sql and "FROM listing_attributes" in sql:
            return FakeResult(row=None)
        if "SELECT id" in sql and "FROM images" in sql:
            return FakeResult(row=None)
        if "RETURNING id" in sql:
            return FakeResult(row={"id": 101})
        return FakeResult(rowcount=2)


class FakeResolver:
    def __init__(self, attribute_id: int | None = 10) -> None:
        self.attribute_id = attribute_id

    def resolve_attribute_id_by_slug(self, slug: str) -> int | None:
        return self.attribute_id

    def resolve_option_by_attribute_slug_and_old_mysql_id(
        self,
        attribute_slug: str,
        old_mysql_id: int | str | None,
        *,
        parent_option_id: int | None = None,
    ) -> None:
        return None

    def resolve_option_by_attribute_slug_and_value(
        self,
        attribute_slug: str,
        value: str | None = None,
        *,
        label: str | None = None,
        parent_option_id: int | None = None,
    ) -> None:
        return None


def _settings() -> SimpleNamespace:
    return SimpleNamespace(
        sync_allow_catalog_writes=True,
        sync_catalog_image_inactive_status=0,
        sync_catalog_inactive_status="inactive",
    )


def test_upsert_attribute_inserts_without_unique_constraint_requirement() -> None:
    session = FakeSession()
    repository = CatalogListingsRepository(
        session,  # type: ignore[arg-type]
        _settings(),  # type: ignore[arg-type]
        reference_resolver=FakeResolver(),  # type: ignore[arg-type]
    )

    ok = repository.upsert_attribute(
        101,
        CatalogAttributePayload(slug="external_id", value="A-1"),
    )

    assert ok is True
    assert any("INSERT INTO listing_attributes" in sql for sql, _params in session.calls)


def test_required_external_id_attribute_missing_raises() -> None:
    repository = CatalogListingsRepository(
        FakeSession(),  # type: ignore[arg-type]
        _settings(),  # type: ignore[arg-type]
        reference_resolver=FakeResolver(attribute_id=None),  # type: ignore[arg-type]
    )

    with pytest.raises(RuntimeError, match="external_id"):
        repository.upsert_attribute(
            101,
            CatalogAttributePayload(slug="external_id", value="A-1"),
        )


def test_deactivate_missing_images_uses_configured_inactive_status() -> None:
    session = FakeSession()
    repository = CatalogListingsRepository(
        session,  # type: ignore[arg-type]
        _settings(),  # type: ignore[arg-type]
        reference_resolver=FakeResolver(),  # type: ignore[arg-type]
    )

    count = repository.deactivate_missing_images(
        listing_id=101,
        current_urls={"https://img.test/old.jpg"},
        new_urls=set(),
    )

    assert count == 2
    assert session.calls[-1][1]["inactive_status"] == 0
