from collections.abc import Callable, Iterable

from app.config import Settings
from app.dto import LegacyAd
from app.providers.base import ProviderAdapter
from app.providers.common import (
    ProviderParseStats,
    active_special_price,
    clean,
    filename_encoded_url,
    ordered_images,
    parse_csv_rows,
    parse_decimal,
    split_photos,
    strip_html,
)
from app.utils.http import HttpClientConfig, ProviderHttpClient

AVTOINSTALL_FEED_URL = "https://avtoinstall.kg/csvprice_pro/2024-04-11_1712816810_data.csv"


class AvtoinstallProviderAdapter(ProviderAdapter):
    provider_key = "avtoinstall"

    def __init__(
        self,
        settings: Settings,
        *,
        fetch_bytes: Callable[[str], bytes] | None = None,
    ) -> None:
        self.settings = settings
        self.feed_url = settings.sync_provider_avtoinstall_feed_url or AVTOINSTALL_FEED_URL
        self.fetch_bytes = (
            fetch_bytes
            or ProviderHttpClient(HttpClientConfig(timeout=settings.sync_http_timeout)).get_bytes
        )
        self.last_stats = ProviderParseStats()

    def fetch_ads(self, *, limit: int | None = None) -> Iterable[LegacyAd]:
        ads = self.parse_feed(self.fetch_bytes(self.feed_url))
        return tuple(ads[:limit]) if limit is not None else tuple(ads)

    def parse_feed(self, content: bytes | str) -> tuple[LegacyAd, ...]:
        stats = ProviderParseStats()
        ads: list[LegacyAd] = []
        for index, row in enumerate(parse_csv_rows(content), start=2):
            stats.read_count += 1
            ad = self.ad_from_row(row, index=index, stats=stats)
            if ad is not None:
                ads.append(ad)
        self.last_stats = stats
        return tuple(ads)

    def ad_from_row(
        self,
        row: dict[str, str],
        *,
        index: int,
        stats: ProviderParseStats,
    ) -> LegacyAd | None:
        if clean(row.get("_STOCK_STATUS_")) != "В наличии" or clean(row.get("_STATUS_")) != "1":
            stats.skip(f"row={index} skipped: product is not active/in stock")
            return None
        if not row.get("_ID_") or not row.get("_NAME_"):
            stats.skip(f"row={index} skipped: missing _ID_ or _NAME_")
            return None
        images = self.images_from_row(row)
        if not images:
            stats.skip(f"row={index} skipped: missing images")
            return None
        price, old_price = active_special_price(
            parse_decimal(row.get("_PRICE_")),
            row.get("_SPECIAL_"),
        )
        return LegacyAd(
            source=self.provider_key,
            external_id=clean(row.get("_ID_")),
            type_id=33,
            name=clean(row.get("_NAME_")),
            description=self.description_from_row(row),
            price=price,
            old_price=old_price,
            currency=1,
            condition=2,
            phone=tuple(self.settings.phones_for_provider(self.provider_key)),
            images=ordered_images(images),
            raw={**row, "comment_allowed": 2, "featured_option": 1},
        )

    def images_from_row(self, row: dict[str, str]) -> tuple[str, ...]:
        urls: list[str] = []
        if clean(row.get("_IMAGE_")):
            urls.append(filename_encoded_url(clean(row.get("_IMAGE_"))))
        urls.extend(
            filename_encoded_url(url) for url in split_photos(row.get("_IMAGES_"), separator=",")
        )
        return tuple(dict.fromkeys(url for url in urls if url))

    def description_from_row(self, row: dict[str, str]) -> str:
        chunks = []
        if row.get("_DESCRIPTION_"):
            chunks.append(strip_html(row.get("_DESCRIPTION_")))
        if row.get("_ATTRIBUTES_"):
            grouped: dict[str, list[str]] = {}
            for line in clean(row.get("_ATTRIBUTES_")).splitlines():
                parts = line.split("|")
                if len(parts) != 3:
                    continue
                grouped.setdefault(parts[0], []).append(f"{parts[1]}: {parts[2]}")
            for group, values in grouped.items():
                chunks.append("\n" + group)
                chunks.extend(values)
        return "\n".join(chunk for chunk in chunks if chunk)
