from dataclasses import dataclass

from app.config import Settings
from app.db.session import create_catalog_engine, ping_catalog_database


@dataclass(frozen=True)
class HealthcheckResult:
    configured: bool
    ok: bool
    message: str


def check_catalog_database(settings: Settings) -> HealthcheckResult:
    engine = create_catalog_engine(settings)
    if engine is None:
        return HealthcheckResult(
            configured=False,
            ok=False,
            message="CATALOG_DATABASE_URL is not configured",
        )

    try:
        ping_catalog_database(engine)
    except Exception as exc:  # noqa: BLE001 - healthcheck should report any connection error
        return HealthcheckResult(
            configured=True,
            ok=False,
            message=str(exc),
        )

    return HealthcheckResult(
        configured=True,
        ok=True,
        message="ok",
    )
