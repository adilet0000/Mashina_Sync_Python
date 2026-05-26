import pytest
from app.config.settings import Settings
from app.repositories.catalog_listings import CatalogWritesDisabledError
from app.services.sync_service import SyncService


def test_real_write_requires_env_dry_run_disabled_and_allow_enabled() -> None:
    settings = Settings(
        CATALOG_DATABASE_URL="postgresql://user:pass@10.0.21.112:31762/postgres",
        SYNC_DRY_RUN=1,
        SYNC_ALLOW_CATALOG_WRITES=0,
    )
    service = SyncService(settings, session_factory=None)

    with pytest.raises(CatalogWritesDisabledError, match="SYNC_DRY_RUN=0"):
        service._ensure_can_run(dry_run=False)


def test_real_write_requires_allow_flag_after_env_dry_run_is_disabled() -> None:
    settings = Settings(
        CATALOG_DATABASE_URL="postgresql://user:pass@10.0.21.112:31762/postgres",
        SYNC_DRY_RUN=0,
        SYNC_ALLOW_CATALOG_WRITES=0,
    )
    service = SyncService(settings, session_factory=None)

    with pytest.raises(CatalogWritesDisabledError, match="SYNC_ALLOW_CATALOG_WRITES=1"):
        service._ensure_can_run(dry_run=False)


def test_safety_summary_redacts_password() -> None:
    settings = Settings(
        CATALOG_DATABASE_URL="postgresql://user:secret@10.0.21.112:31762/postgres",
        SYNC_DRY_RUN=1,
    )
    service = SyncService(settings, session_factory=None)

    summary = service._build_safety_summary(
        provider="autoland",
        user_id=77,
        category_ids=(35,),
        dry_run=True,
    )

    assert "secret" not in summary["database"]
    assert "10.0.21.112:31762" in summary["database"]
    assert summary["mode"] == "dry-run"
