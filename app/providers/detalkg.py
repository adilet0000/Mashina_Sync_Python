from collections.abc import Callable, Iterable
from decimal import Decimal
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from defusedxml import ElementTree

from app.config import Settings
from app.dto import LegacyAd
from app.providers.base import ProviderAdapter
from app.providers.common import (
    ProviderParseStats,
    clean,
    parse_decimal,
    parse_tire_dimensions,
    strip_html,
    tire_type_from_text,
)
from app.utils.http import HttpClientConfig, ProviderHttpClient

DETALKG_PARTS_FEED_URL = "https://detal.kg/price-yml/6fe6a8a6e6cb710584efc4af0c34ce50.yml"
DETALKG_SITE_URL = "https://detal.kg/"


class DetalKgProviderAdapter(ProviderAdapter):
    provider_key = "detalkg"

    def __init__(
        self,
        settings: Settings,
        *,
        fetch_bytes: Callable[[str], bytes] | None = None,
        fetch_text: Callable[[str], str] | None = None,
    ) -> None:
        self.settings = settings
        self.parts_feed_url = (
            settings.sync_provider_detalkg_parts_feed_url or DETALKG_PARTS_FEED_URL
        )
        self.site_url = settings.sync_provider_detalkg_base_url or DETALKG_SITE_URL
        client = ProviderHttpClient(HttpClientConfig(timeout=settings.sync_http_timeout))
        self.fetch_bytes = fetch_bytes or client.get_bytes
        self.fetch_text = fetch_text or client.get_text
        self.last_stats = ProviderParseStats()

    def fetch_ads(self, *, limit: int | None = None) -> Iterable[LegacyAd]:
        stats = ProviderParseStats()
        ads = list(self.parse_parts_feed(self.fetch_bytes(self.parts_feed_url), stats=stats))
        for detail_url in self.tire_detail_urls():
            if limit is not None and len(ads) >= limit:
                break
            stats.read_count += 1
            ad = self.parse_tire_detail(detail_url, stats=stats)
            if ad is not None:
                ads.append(ad)
        self.last_stats = stats
        return tuple(ads[:limit]) if limit is not None else tuple(ads)

    def parse_parts_feed(
        self,
        content: bytes | str,
        *,
        stats: ProviderParseStats,
    ) -> tuple[LegacyAd, ...]:
        root = ElementTree.fromstring(content)
        ads: list[LegacyAd] = []
        for offer in root.findall(".//offer"):
            stats.read_count += 1
            ad = self.part_ad_from_offer(offer, stats=stats)
            if ad is not None:
                ads.append(ad)
        return tuple(ads)

    def part_ad_from_offer(self, offer, *, stats: ProviderParseStats) -> LegacyAd | None:
        external_id = clean(offer.attrib.get("id"))
        name = clean(offer.findtext("name"))
        description = clean(offer.findtext("description"))
        count = clean(offer.findtext("count"))
        if not external_id or not name or not description:
            stats.skip(f"offer={external_id or '<empty>'} skipped: missing required fields")
            return None
        if count == "0":
            stats.skip(f"offer={external_id} skipped: count=0")
            return None
        images = tuple(clean(node.text) for node in offer.findall("picture") if clean(node.text))
        if not images:
            stats.skip(f"offer={external_id} skipped: missing images")
            return None
        price = parse_decimal(offer.findtext("price"))
        price_with_markup = price + (price * Decimal("0.2")) if price is not None else None
        normalized_name = (
            name.replace("!\\ ", " ").replace("\\", "").replace("!", "").replace("&lt;", "<")
        )
        normalized_description = (
            description.replace("\\", " ").replace("!", "").replace("&lt;", "<")
        )
        return LegacyAd(
            source=self.provider_key,
            external_id=external_id,
            type_id=30,
            name=normalized_name[:75],
            description=normalized_description,
            price=price_with_markup.quantize(Decimal("1"))
            if price_with_markup is not None
            else None,
            currency=1,
            condition=2,
            phone=tuple(self.settings.phones_for_provider(self.provider_key)),
            images=images[:12],
            raw={"offer_id": external_id, "vendor": clean(offer.findtext("vendor"))},
        )

    def tire_detail_urls(self) -> tuple[str, ...]:
        # Legacy only crawled the tires-search category.
        html = self.fetch_text(
            urljoin(self.site_url, "tires-search/?items_per_page=36&curr_page=1")
        )
        soup = BeautifulSoup(html, "html.parser")
        urls = []
        for anchor in soup.select("div.item-list p.item-name a[href], a[href*='show_tire=1']"):
            href = clean(anchor.get("href"))
            if href:
                urls.append(urljoin(self.site_url, href))
        return tuple(dict.fromkeys(urls))

    def parse_tire_detail(self, detail_url: str, *, stats: ProviderParseStats) -> LegacyAd | None:
        soup = BeautifulSoup(self.fetch_text(detail_url), "html.parser")
        params = {}
        for row in soup.select("table#tire-specs tr, #tire-specs tr"):
            cells = [cell.get_text(" ", strip=True) for cell in row.select("td")]
            if len(cells) >= 2:
                params[cells[0].lower()] = cells[1]
        external_id = params.get("артикул") or detail_url.rstrip("/").split("/")[-1]
        title_node = soup.select_one("div#content h1, h1")
        title = title_node.get_text(" ", strip=True) if title_node else ""
        width = params.get("ширина")
        height = params.get("размерность_2")
        size = params.get("диаметр")
        if not all((width, height, size)):
            parsed = parse_tire_dimensions(title + " " + " ".join(params.values()))
            width, height, size = width or parsed[0], height or parsed[1], size or parsed[2]
        if not all((external_id, title, width, height, size)):
            stats.skip(f"tire={detail_url} skipped: missing required fields")
            return None
        image_urls = []
        for image in soup.select("div.pic-container img[src], img[src]"):
            src = clean(image.get("src"))
            if src and "tire_no_photo" not in src:
                image_urls.append(urljoin(self.site_url, src))
        price_node = soup.select_one("#price-and-buy-block b b, #price-and-buy-block")
        description_node = soup.select_one("#tire-catalog-description")
        description = (
            strip_html(description_node.get_text(" ", strip=True)) if description_node else title
        )
        return LegacyAd(
            source=self.provider_key,
            external_id=external_id,
            type_id=31,
            name=f"{title} {width}/{height}/R{size}",
            description=description,
            price=parse_decimal(price_node.get_text(" ", strip=True)) if price_node else None,
            currency=1,
            condition=2,
            phone=tuple(self.settings.phones_for_provider(self.provider_key)),
            images=tuple(dict.fromkeys(image_urls)),
            tire_width=width,
            tire_height=height,
            tire_size=size,
            tire_type=tire_type_from_text(params.get("сезонность") or params.get("шипы")),
            raw={"detail_url": detail_url, "featured_option": 1, "params": params},
        )
