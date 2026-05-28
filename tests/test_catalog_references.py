from app.repositories.catalog_references import CatalogReferenceResolver


class FakeResult:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows

    def mappings(self) -> "FakeResult":
        return self

    def first(self) -> dict[str, object] | None:
        return self.rows[0] if self.rows else None


class FakeSession:
    def execute(self, statement: object, params: dict[str, object]) -> FakeResult:
        sql = str(statement)
        if "FROM attributes" in sql:
            if params["slug"] == "make":
                return FakeResult(
                    [
                        {
                            "id": 11,
                            "slug": "make",
                            "name_ru": "Марка",
                            "name_en": "Make",
                            "name_kg": None,
                        }
                    ]
                )
            return FakeResult([])
        if "FROM attribute_options" in sql and "old_mysql_id" in sql:
            return FakeResult(
                [
                    {
                        "id": 22,
                        "attribute_id": 11,
                        "value": "toyota",
                        "label": "Toyota",
                        "old_mysql_id": 1,
                        "parent_option_id": None,
                    }
                ]
            )
        return FakeResult([])


def test_reference_resolver_resolves_attribute_id() -> None:
    resolver = CatalogReferenceResolver(FakeSession())  # type: ignore[arg-type]
    assert resolver.resolve_attribute_id_by_slug("make") == 11


def test_reference_resolver_resolves_option_by_old_mysql_id() -> None:
    resolver = CatalogReferenceResolver(FakeSession())  # type: ignore[arg-type]
    option = resolver.resolve_option_by_attribute_slug_and_old_mysql_id("make", 1)
    assert option is not None
    assert option.id == 22
    assert option.old_mysql_id == 1


def test_reference_resolver_query_uses_real_attribute_name_columns() -> None:
    session = FakeSession()
    resolver = CatalogReferenceResolver(session)  # type: ignore[arg-type]
    attribute = resolver.resolve_attribute_by_slug("make")
    assert attribute is not None
    assert attribute.name == "Марка"
