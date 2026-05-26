from app.config import Settings
from app.providers.bazon import BazonKeys, TireWheelCsvProviderAdapter
from app.providers.common import ProviderParseStats, clean

SHINABAR_FEED_URL = "https://baz-on.ru/export/c1750/bee92/mashina-wheels.csv"


class ShinabarProviderAdapter(TireWheelCsvProviderAdapter):
    provider_key = "shinabar"
    feed_url = SHINABAR_FEED_URL
    import_price = True
    required_fields = (
        BazonKeys.ID,
        BazonKeys.TIRE_TYPE,
        BazonKeys.TIRE_WIDTH,
        BazonKeys.TIRE_HEIGHT,
        BazonKeys.TIRE_SIZE,
        BazonKeys.TIRE_WHEEL_CONDITION,
        BazonKeys.AVAILABILITY,
    )

    def __init__(self, settings: Settings, **kwargs) -> None:
        super().__init__(settings, **kwargs)
        self.feed_url = settings.sync_provider_shinabar_feed_url or SHINABAR_FEED_URL

    def rows_to_ads(self, rows: tuple[dict[str, object], ...]):
        deduped = {clean(row.get(BazonKeys.ID)): row for row in rows}
        return tuple(self.ad_from_row(row) for row in deduped.values())

    def sanitize_row(
        self,
        raw: dict[str, str],
        *,
        index: int,
        stats: ProviderParseStats,
    ) -> dict[str, object] | None:
        raw = {**raw, BazonKeys.IS_WHEEL_OR_TIRE: raw.get(BazonKeys.IS_WHEEL_OR_TIRE) or "шина"}
        row = super().sanitize_row(raw, index=index, stats=stats)
        if row is None:
            return None
        if clean(row.get(BazonKeys.IS_WHEEL_OR_TIRE)).lower() != "шина":
            stats.skip(f"row={index} skipped: shinabar wheel rows are not imported yet")
            return None
        return row
