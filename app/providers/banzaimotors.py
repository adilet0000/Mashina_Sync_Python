from collections.abc import Callable, Iterable
from decimal import Decimal
from typing import Any

from app.config import Settings
from app.dto import LegacyAd
from app.providers.base import ProviderAdapter
from app.providers.bazon import BazonKeys, TireWheelCsvProviderAdapter
from app.providers.common import ProviderParseStats, clean, parse_csv_rows, split_photos
from app.utils.http import HttpClientConfig, ProviderHttpClient

BANZAIMOTORS_PARTS_FEED_URL = "https://baz-on.ru/export/c1483/c8ae6/mashina-parts.csv"
BANZAIMOTORS_WHEELS_FEED_URL = "https://baz-on.ru/export/c1483/8fb9b/wheels-wheels.csv"


class BanzaimotorsProviderAdapter(ProviderAdapter):
    provider_key = "banzaimotors"

    def __init__(
        self,
        settings: Settings,
        *,
        fetch_bytes: Callable[[str], bytes] | None = None,
    ) -> None:
        self.settings = settings
        self.parts_feed_url = (
            settings.sync_provider_banzaimotors_parts_feed_url or BANZAIMOTORS_PARTS_FEED_URL
        )
        self.wheels_feed_url = (
            settings.sync_provider_banzaimotors_wheels_feed_url or BANZAIMOTORS_WHEELS_FEED_URL
        )
        self.fetch_bytes = (
            fetch_bytes
            or ProviderHttpClient(HttpClientConfig(timeout=settings.sync_http_timeout)).get_bytes
        )
        self.last_stats = ProviderParseStats()

    def fetch_ads(self, *, limit: int | None = None) -> Iterable[LegacyAd]:
        stats = ProviderParseStats()
        ads = list(self._parts_ads(self.fetch_bytes(self.parts_feed_url), stats=stats))
        ads.extend(self._tire_wheel_ads(self.fetch_bytes(self.wheels_feed_url), stats=stats))
        self.last_stats = stats
        return tuple(ads[:limit]) if limit is not None else tuple(ads)

    def _parts_ads(
        self, content: bytes | str, *, stats: ProviderParseStats
    ) -> tuple[LegacyAd, ...]:
        ads: list[LegacyAd] = []
        for index, raw in enumerate(parse_csv_rows(content), start=2):
            stats.read_count += 1
            row = self._sanitize_parts_row(raw, index=index, stats=stats)
            if row is None:
                continue
            ads.append(
                LegacyAd(
                    source=self.provider_key,
                    external_id=clean(row.get(BazonKeys.ID)),
                    type_id=30,
                    name=self._parts_name(row),
                    description=self._parts_description(row),
                    price=Decimal("0"),
                    currency=1,
                    make=clean(row.get(BazonKeys.MAKE)) or None,
                    model=clean(row.get(BazonKeys.MODEL)) or None,
                    year=clean(row.get(BazonKeys.YEAR)) or None,
                    generation=clean(row.get(BazonKeys.GENERATION)) or None,
                    condition=1,
                    phone=tuple(self.settings.phones_for_provider(self.provider_key)),
                    images=tuple(row[BazonKeys.PHOTOS]),
                    raw=row,
                )
            )
        return tuple(ads)

    def _tire_wheel_ads(
        self,
        content: bytes | str,
        *,
        stats: ProviderParseStats,
    ) -> tuple[LegacyAd, ...]:
        helper = _BanzaiTireWheelAdapter(self.settings, fetch_bytes=self.fetch_bytes)
        rows = []
        for index, raw in enumerate(parse_csv_rows(content), start=2):
            stats.read_count += 1
            row = helper.sanitize_row(raw, index=index, stats=stats)
            if row is not None:
                rows.append(row)
        return tuple(helper.ad_from_row(row) for row in rows)

    def _sanitize_parts_row(
        self,
        raw: dict[str, str],
        *,
        index: int,
        stats: ProviderParseStats,
    ) -> dict[str, Any] | None:
        for field in (BazonKeys.ID, BazonKeys.NAME, BazonKeys.MAKE, BazonKeys.MODEL):
            if not raw.get(field):
                stats.skip(f"row={index} skipped: missing {field}")
                return None
        photos = split_photos(raw.get(BazonKeys.PHOTOS), max_count=12)
        if not photos:
            stats.skip(f"row={index} skipped: missing photos")
            return None
        return {**raw, BazonKeys.PHOTOS: photos}

    def _parts_name(self, row: dict[str, Any]) -> str:
        chunks = [clean(row.get(BazonKeys.NAME)), clean(row.get(BazonKeys.GENERATION))]
        return " ".join(chunk for chunk in chunks if chunk)

    def _parts_description(self, row: dict[str, Any]) -> str:
        chunks = []
        for field in (
            BazonKeys.NAME,
            BazonKeys.MAKE,
            BazonKeys.MODEL,
            BazonKeys.GENERATION,
            BazonKeys.ENGINE,
            BazonKeys.YEAR,
            BazonKeys.TOP_BOTTOM,
            BazonKeys.FRONT_REAR,
            BazonKeys.LEFT_RIGHT,
            BazonKeys.COLOR,
            BazonKeys.COMMENT,
        ):
            if clean(row.get(field)):
                chunks.append(clean(row.get(field)))
        return " ".join(chunks)


class _BanzaiTireWheelAdapter(TireWheelCsvProviderAdapter):
    provider_key = "banzaimotors"
    feed_url = BANZAIMOTORS_WHEELS_FEED_URL
    import_price = False
