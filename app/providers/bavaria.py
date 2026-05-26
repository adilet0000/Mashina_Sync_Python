from collections import defaultdict
from collections.abc import Callable, Iterable
from decimal import Decimal
from typing import Any

from app.config import Settings
from app.dto import LegacyAd
from app.providers.base import ProviderAdapter
from app.providers.bazon import BazonKeys, TireWheelCsvProviderAdapter
from app.providers.common import ProviderParseStats, clean, parse_csv_rows, split_photos
from app.utils.http import HttpClientConfig, ProviderHttpClient

BAVARIA_PARTS_FEED_URL = "https://baz-on.ru/export/c935/01051/mashina-bavariab-parts.csv"
BAVARIA_WHEELS_FEED_URL = "https://baz-on.ru/export/c935/77e63/disk-wheels.csv"
REPLACE_MAKES = {"depo", "bosch", "дубликат"}


class BavariaProviderAdapter(ProviderAdapter):
    provider_key = "bavaria"

    def __init__(
        self,
        settings: Settings,
        *,
        fetch_bytes: Callable[[str], bytes] | None = None,
    ) -> None:
        self.settings = settings
        self.parts_feed_url = (
            settings.sync_provider_bavaria_parts_feed_url or BAVARIA_PARTS_FEED_URL
        )
        self.wheels_feed_url = (
            settings.sync_provider_bavaria_wheels_feed_url or BAVARIA_WHEELS_FEED_URL
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
        rows = []
        for index, raw in enumerate(parse_csv_rows(content), start=2):
            stats.read_count += 1
            row = self._sanitize_parts_row(raw, index=index, stats=stats)
            if row is not None:
                rows.append(row)

        grouped: dict[tuple[str, ...], dict[str, dict[str, Any]]] = defaultdict(dict)
        for row in rows:
            key = tuple(
                clean(row.get(field))
                for field in (
                    BazonKeys.NAME,
                    BazonKeys.MAKE,
                    BazonKeys.MODEL,
                    BazonKeys.YEAR,
                    BazonKeys.GENERATION,
                )
            )
            grouped[key][clean(row.get(BazonKeys.ID))] = row

        return tuple(
            self._parts_ad_from_group(tuple(entries.values())) for entries in grouped.values()
        )

    def _parts_ad_from_group(self, rows: tuple[dict[str, Any], ...]) -> LegacyAd:
        first = rows[0]
        if len(rows) == 1:
            return self._parts_ad_from_row(first)
        external_id = ",".join(row[BazonKeys.ID] for row in rows)
        description = f"{self._parts_name(first, multiple=True)}\n{len(rows)} шт. в наличии:\n"
        description += "\n".join(
            f"{index}) {self._parts_description(row, multiple=True)}"
            for index, row in enumerate(rows, start=1)
        )
        photos = tuple(dict.fromkeys(photo for row in rows for photo in row[BazonKeys.PHOTOS]))
        return LegacyAd(
            source=self.provider_key,
            external_id=external_id,
            type_id=30,
            name=self._parts_name(first, multiple=True),
            description=description,
            price=None,
            currency=1,
            make=first.get(BazonKeys.MAKE),
            model=first.get(BazonKeys.MODEL),
            year=first.get(BazonKeys.YEAR),
            generation=first.get(BazonKeys.GENERATION),
            condition=1,
            phone=tuple(self.settings.phones_for_provider(self.provider_key)),
            images=photos,
            raw={"grouped_articles": [row[BazonKeys.ID] for row in rows], "rows": list(rows)},
        )

    def _parts_ad_from_row(self, row: dict[str, Any]) -> LegacyAd:
        return LegacyAd(
            source=self.provider_key,
            external_id=clean(row.get(BazonKeys.ID)),
            type_id=30,
            name=self._parts_name(row),
            description=self._parts_description(row),
            price=None,
            currency=1,
            make=row.get(BazonKeys.MAKE),
            model=row.get(BazonKeys.MODEL),
            year=row.get(BazonKeys.YEAR),
            generation=row.get(BazonKeys.GENERATION),
            condition=1,
            phone=tuple(self.settings.phones_for_provider(self.provider_key)),
            images=tuple(row[BazonKeys.PHOTOS]),
            raw=row,
        )

    def _sanitize_parts_row(
        self,
        raw: dict[str, str],
        *,
        index: int,
        stats: ProviderParseStats,
    ) -> dict[str, Any] | None:
        for field in (
            BazonKeys.ID,
            BazonKeys.NAME,
            BazonKeys.MAKE,
            BazonKeys.MODEL,
            BazonKeys.YEAR,
            BazonKeys.GENERATION,
        ):
            if not raw.get(field):
                stats.skip(f"row={index} skipped: missing {field}")
                return None
        photos = split_photos(raw.get(BazonKeys.PHOTOS), max_count=12)
        if not photos:
            stats.skip(f"row={index} skipped: missing photos")
            return None
        row = {**raw, BazonKeys.PHOTOS: photos}
        if clean(row.get(BazonKeys.MAKE)).lower() in REPLACE_MAKES:
            row[BazonKeys.MAKE] = "bmw"
        return row

    def _parts_name(self, row: dict[str, Any], *, multiple: bool = False) -> str:
        chunks = [clean(row.get(BazonKeys.NAME)), clean(row.get(BazonKeys.GENERATION))]
        if not multiple and clean(row.get(BazonKeys.PART_NUMBER)):
            chunks.append(clean(row.get(BazonKeys.PART_NUMBER)))
        return ", ".join(chunk for chunk in chunks if chunk)

    def _parts_description(self, row: dict[str, Any], *, multiple: bool = False) -> str:
        chunks = []
        if clean(row.get(BazonKeys.NAME)) and not multiple:
            chunks.append(clean(row.get(BazonKeys.NAME)) + "\n")
        if not multiple:
            chunks.extend([clean(row.get(BazonKeys.MAKE)), clean(row.get(BazonKeys.MODEL))])
        for field in (
            BazonKeys.GENERATION,
            BazonKeys.ENGINE,
            BazonKeys.YEAR,
            BazonKeys.TOP_BOTTOM,
            BazonKeys.FRONT_REAR,
            BazonKeys.LEFT_RIGHT,
            BazonKeys.COLOR,
        ):
            if clean(row.get(field)):
                chunks.append(clean(row.get(field)))
        if not multiple:
            chunks.append(f"\n{BazonKeys.ID}: {clean(row.get(BazonKeys.ID))}")
        if clean(row.get(BazonKeys.COMMENT)):
            chunks.append(("\n" if not multiple else "") + clean(row.get(BazonKeys.COMMENT)))
        if multiple:
            chunks.append(f"{BazonKeys.ID}: {clean(row.get(BazonKeys.ID))}")
        return " ".join(chunk for chunk in chunks if chunk).replace("\n ", "\n")

    def _tire_wheel_ads(
        self,
        content: bytes | str,
        *,
        stats: ProviderParseStats,
    ) -> tuple[LegacyAd, ...]:
        helper = _BavariaTireWheelAdapter(self.settings, fetch_bytes=self.fetch_bytes)
        rows = []
        for index, raw in enumerate(parse_csv_rows(content), start=2):
            stats.read_count += 1
            row = helper.sanitize_row(raw, index=index, stats=stats)
            if row is not None:
                rows.append(row)
        return tuple(helper.ad_from_row(row) for row in rows)


class _BavariaTireWheelAdapter(TireWheelCsvProviderAdapter):
    provider_key = "bavaria"
    feed_url = BAVARIA_WHEELS_FEED_URL
    import_price = True

    def ad_from_row(self, row: dict[str, Any]) -> LegacyAd:
        ad = super().ad_from_row(row)
        return LegacyAd(
            **{
                **ad.__dict__,
                "price": ad.price if ad.price is not None else Decimal("0"),
                "currency": 1,
            }
        )
