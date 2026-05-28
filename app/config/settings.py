from functools import lru_cache
from typing import Any, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROVIDER_KEYS = (
    "autohub",
    "autoland",
    "shredder",
    "okayamaomsk",
    "banzaimotors",
    "bavaria",
    "shinabar",
    "avtoinstall",
    "allmotors",
    "autoshina",
    "detalkg",
    "toyota",
    "toyota_tradein",
    "lexus",
    "kia",
)


def provider_env_suffix(provider: str) -> str:
    return provider.upper().replace("-", "_")


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    app_env: str = Field(default="local", validation_alias="APP_ENV")
    catalog_database_url: str | None = Field(default=None, validation_alias="CATALOG_DATABASE_URL")

    sync_target: Literal["catalog"] | str = Field(default="catalog", validation_alias="SYNC_TARGET")
    sync_dry_run: bool = Field(default=True, validation_alias="SYNC_DRY_RUN")
    sync_allow_catalog_writes: bool = Field(
        default=False,
        validation_alias="SYNC_ALLOW_CATALOG_WRITES",
    )
    sync_catalog_user_id: int | None = Field(default=None, validation_alias="SYNC_CATALOG_USER_ID")
    sync_catalog_default_status: str = Field(
        default="active",
        validation_alias="SYNC_CATALOG_DEFAULT_STATUS",
    )
    sync_catalog_inactive_status: str = Field(
        default="inactive",
        validation_alias="SYNC_CATALOG_INACTIVE_STATUS",
    )
    sync_catalog_image_status: int = Field(default=1, validation_alias="SYNC_CATALOG_IMAGE_STATUS")
    sync_catalog_image_inactive_status: int = Field(
        default=0,
        validation_alias="SYNC_CATALOG_IMAGE_INACTIVE_STATUS",
    )
    sync_batch_size: int = Field(default=100, validation_alias="SYNC_BATCH_SIZE")
    sync_http_timeout: float = Field(default=30.0, validation_alias="SYNC_HTTP_TIMEOUT")
    sync_log_level: str = Field(default="INFO", validation_alias="SYNC_LOG_LEVEL")
    sync_catalog_phones: str | None = Field(default=None, validation_alias="SYNC_CATALOG_PHONES")
    sync_provider_autoland_feed_url: str | None = Field(
        default=None,
        validation_alias="SYNC_PROVIDER_AUTOLAND_FEED_URL",
    )
    sync_provider_autohub_feed_url: str | None = Field(
        default=None,
        validation_alias="SYNC_PROVIDER_AUTOHUB_FEED_URL",
    )
    sync_provider_shredder_feed_url: str | None = Field(
        default=None,
        validation_alias="SYNC_PROVIDER_SHREDDER_FEED_URL",
    )
    sync_provider_okayamaomsk_feed_url: str | None = Field(
        default=None,
        validation_alias="SYNC_PROVIDER_OKAYAMAOMSK_FEED_URL",
    )
    sync_provider_banzaimotors_parts_feed_url: str | None = Field(
        default=None,
        validation_alias="SYNC_PROVIDER_BANZAIMOTORS_PARTS_FEED_URL",
    )
    sync_provider_banzaimotors_wheels_feed_url: str | None = Field(
        default=None,
        validation_alias="SYNC_PROVIDER_BANZAIMOTORS_WHEELS_FEED_URL",
    )
    sync_provider_bavaria_parts_feed_url: str | None = Field(
        default=None,
        validation_alias="SYNC_PROVIDER_BAVARIA_PARTS_FEED_URL",
    )
    sync_provider_bavaria_wheels_feed_url: str | None = Field(
        default=None,
        validation_alias="SYNC_PROVIDER_BAVARIA_WHEELS_FEED_URL",
    )
    sync_provider_shinabar_feed_url: str | None = Field(
        default=None,
        validation_alias="SYNC_PROVIDER_SHINABAR_FEED_URL",
    )
    sync_provider_avtoinstall_feed_url: str | None = Field(
        default=None,
        validation_alias="SYNC_PROVIDER_AVTOINSTALL_FEED_URL",
    )
    sync_provider_allmotors_base_url: str | None = Field(
        default=None,
        validation_alias="SYNC_PROVIDER_ALLMOTORS_BASE_URL",
    )
    sync_provider_autoshina_base_url: str | None = Field(
        default=None,
        validation_alias="SYNC_PROVIDER_AUTOSHINA_BASE_URL",
    )
    sync_provider_detalkg_parts_feed_url: str | None = Field(
        default=None,
        validation_alias="SYNC_PROVIDER_DETALKG_PARTS_FEED_URL",
    )
    sync_provider_detalkg_base_url: str | None = Field(
        default=None,
        validation_alias="SYNC_PROVIDER_DETALKG_BASE_URL",
    )
    sync_provider_toyota_feed_url: str | None = Field(
        default=None,
        validation_alias="SYNC_PROVIDER_TOYOTA_FEED_URL",
    )
    sync_provider_toyota_tradein_feed_url: str | None = Field(
        default=None,
        validation_alias="SYNC_PROVIDER_TOYOTA_TRADEIN_FEED_URL",
    )
    sync_provider_toyota_tradein_currency_rate: float | None = Field(
        default=None,
        validation_alias="SYNC_PROVIDER_TOYOTA_TRADEIN_CURRENCY_RATE",
    )
    sync_provider_lexus_feed_url: str | None = Field(
        default=None,
        validation_alias="SYNC_PROVIDER_LEXUS_FEED_URL",
    )
    sync_provider_kia_feed_url: str | None = Field(
        default=None,
        validation_alias="SYNC_PROVIDER_KIA_FEED_URL",
    )

    sync_catalog_user_id_autohub: int | None = Field(
        default=None,
        validation_alias="SYNC_CATALOG_USER_ID_AUTOHUB",
    )
    sync_catalog_user_id_autoland: int | None = Field(
        default=None,
        validation_alias="SYNC_CATALOG_USER_ID_AUTOLAND",
    )
    sync_catalog_user_id_shredder: int | None = Field(
        default=None,
        validation_alias="SYNC_CATALOG_USER_ID_SHREDDER",
    )
    sync_catalog_user_id_okayamaomsk: int | None = Field(
        default=None,
        validation_alias="SYNC_CATALOG_USER_ID_OKAYAMAOMSK",
    )
    sync_catalog_user_id_banzaimotors: int | None = Field(
        default=None,
        validation_alias="SYNC_CATALOG_USER_ID_BANZAIMOTORS",
    )
    sync_catalog_user_id_bavaria: int | None = Field(
        default=None,
        validation_alias="SYNC_CATALOG_USER_ID_BAVARIA",
    )
    sync_catalog_user_id_shinabar: int | None = Field(
        default=None,
        validation_alias="SYNC_CATALOG_USER_ID_SHINABAR",
    )
    sync_catalog_user_id_avtoinstall: int | None = Field(
        default=None,
        validation_alias="SYNC_CATALOG_USER_ID_AVTOINSTALL",
    )
    sync_catalog_user_id_allmotors: int | None = Field(
        default=None,
        validation_alias="SYNC_CATALOG_USER_ID_ALLMOTORS",
    )
    sync_catalog_user_id_autoshina: int | None = Field(
        default=None,
        validation_alias="SYNC_CATALOG_USER_ID_AUTOSHINA",
    )
    sync_catalog_user_id_detalkg: int | None = Field(
        default=None,
        validation_alias="SYNC_CATALOG_USER_ID_DETALKG",
    )
    sync_catalog_user_id_toyota: int | None = Field(
        default=None,
        validation_alias="SYNC_CATALOG_USER_ID_TOYOTA",
    )
    sync_catalog_user_id_toyota_tradein: int | None = Field(
        default=None,
        validation_alias="SYNC_CATALOG_USER_ID_TOYOTA_TRADEIN",
    )
    sync_catalog_user_id_lexus: int | None = Field(
        default=None,
        validation_alias="SYNC_CATALOG_USER_ID_LEXUS",
    )
    sync_catalog_user_id_kia: int | None = Field(
        default=None,
        validation_alias="SYNC_CATALOG_USER_ID_KIA",
    )

    # Backward-compatible aliases from the first skeleton. They are not used as old DB business
    # sources, but keeping them harmlessly supports existing local env files.
    old_database_url: str | None = Field(default=None, validation_alias="OLD_DATABASE_URL")
    new_database_url: str | None = Field(default=None, validation_alias="NEW_DATABASE_URL")

    @field_validator("sync_dry_run", "sync_allow_catalog_writes", mode="before")
    @classmethod
    def parse_bool_flags(cls, value: Any) -> bool:
        return _to_bool(value)

    @field_validator("sync_batch_size")
    @classmethod
    def validate_batch_size(cls, value: int) -> int:
        if value < 1:
            return 1
        return value

    @property
    def effective_catalog_database_url(self) -> str | None:
        return self.catalog_database_url or self.new_database_url

    @property
    def normalized_log_level(self) -> Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        level = self.sync_log_level.upper()
        if level in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            return level  # type: ignore[return-value]
        return "INFO"

    @property
    def is_catalog_target(self) -> bool:
        return self.sync_target.lower() == "catalog"

    def catalog_user_id_for_provider(self, provider: str) -> int | None:
        field_name = f"sync_catalog_user_id_{provider.lower().replace('-', '_')}"
        return getattr(self, field_name, None) or self.sync_catalog_user_id

    def phones_for_provider(self, provider: str) -> list[str]:
        _ = provider
        if not self.sync_catalog_phones:
            return []
        return [
            phone.strip() for phone in str(self.sync_catalog_phones).split(",") if phone.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
