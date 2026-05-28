from pathlib import Path

from app.config.settings import Settings
from app.providers.autoland import AutolandProviderAdapter
from app.services.sync_service import SyncService


class FakeSessionFactory:
    def __call__(self) -> "FakeSessionFactory":
        return self

    def __enter__(self) -> "FakeSessionFactory":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None


class FakeCatalogRepository:
    def __init__(self, session: object, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    def get_current_by_provider(
        self,
        *,
        provider: str,
        user_id: int,
        category_ids: tuple[int, ...],
    ) -> dict[str, object]:
        return {}


def _settings() -> Settings:
    return Settings(
        CATALOG_DATABASE_URL="postgresql://user:pass@example.test:5432/catalog",
        SYNC_CATALOG_USER_ID=77,
        SYNC_CATALOG_PHONES="+996555000111",
        SYNC_DRY_RUN=1,
        SYNC_ALLOW_CATALOG_WRITES=0,
    )


def _fixture_bytes() -> bytes:
    path = Path(__file__).parent / "fixtures" / "autoland.csv"
    return path.read_text(encoding="utf-8").encode("cp1251")


def test_autoland_sync_dry_run_with_mocked_repository() -> None:
    settings = _settings()
    adapter = AutolandProviderAdapter(settings, fetch_bytes=lambda _url: _fixture_bytes())
    service = SyncService(
        settings,
        session_factory=FakeSessionFactory(),  # type: ignore[arg-type]
        adapters={"autoland": adapter},
        repository_factory=FakeCatalogRepository,  # type: ignore[arg-type]
    )

    result = service.sync_provider("autoland", dry_run=True)

    assert result.read_count == 4
    assert result.valid_count == 2
    assert result.skipped_count == 1
    assert result.inserted_count == 2
    assert result.updated_count == 0
    assert result.deactivated_count == 0
    assert result.legacy_samples
    assert result.payload_samples
    assert result.diff_samples[0]["action"] == "insert"
