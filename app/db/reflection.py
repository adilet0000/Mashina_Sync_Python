from dataclasses import dataclass

from sqlalchemy import inspect

from app.config import Settings
from app.db.session import create_catalog_engine

REQUIRED_CATALOG_TABLES = (
    "listings",
    "listing_attributes",
    "attributes",
    "attribute_options",
    "images",
    "listing_counters",
    "listing_promotions",
)


@dataclass(frozen=True)
class CatalogTableStatus:
    table_name: str
    exists: bool


@dataclass(frozen=True)
class CatalogInspectionResult:
    configured: bool
    ok: bool
    message: str
    tables: tuple[CatalogTableStatus, ...]


def inspect_catalog_tables(settings: Settings) -> CatalogInspectionResult:
    engine = create_catalog_engine(settings)
    if engine is None:
        return CatalogInspectionResult(
            configured=False,
            ok=False,
            message="CATALOG_DATABASE_URL is not configured",
            tables=(),
        )

    try:
        with engine.connect() as connection:
            inspector = inspect(connection)
            existing_tables = set(inspector.get_table_names())
    except Exception as exc:  # noqa: BLE001 - inspect-db should report any DB/driver error
        return CatalogInspectionResult(
            configured=True,
            ok=False,
            message=str(exc),
            tables=(),
        )

    statuses = tuple(
        CatalogTableStatus(table_name=table_name, exists=table_name in existing_tables)
        for table_name in REQUIRED_CATALOG_TABLES
    )
    missing = [status.table_name for status in statuses if not status.exists]
    message = "ok" if not missing else f"missing tables: {', '.join(missing)}"
    return CatalogInspectionResult(
        configured=True,
        ok=not missing,
        message=message,
        tables=statuses,
    )
