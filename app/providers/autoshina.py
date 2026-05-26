from collections.abc import Callable, Iterable
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.config import Settings
from app.dto import LegacyAd
from app.providers.base import ProviderAdapter
from app.providers.common import (
    ProviderParseStats,
    clean,
    parse_decimal,
    strip_html,
    tire_type_from_text,
)
from app.utils.http import HttpClientConfig, ProviderHttpClient

AUTOSHINA_SITE_URL = "https://autoshina.kg"


class AutoshinaProviderAdapter(ProviderAdapter):
    provider_key = "autoshina"

    def __init__(
        self,
        settings: Settings,
        *,
        fetch_text: Callable[[str], str] | None = None,
    ) -> None:
        self.settings = settings
        self.site_url = settings.sync_provider_autoshina_base_url or AUTOSHINA_SITE_URL
        self.fetch_text = (
            fetch_text
            or ProviderHttpClient(HttpClientConfig(timeout=settings.sync_http_timeout)).get_text
        )
        self.last_stats = ProviderParseStats()

    def fetch_ads(self, *, limit: int | None = None) -> Iterable[LegacyAd]:
        stats = ProviderParseStats()
        ads: list[LegacyAd] = []
        page = 1
        while True:
            ids = self.product_ids_for_page(page)
            if not ids:
                break
            for product_id in ids:
                stats.read_count += 1
                ad = self.parse_product(product_id, stats=stats)
                if ad is not None:
                    ads.append(ad)
                    if limit is not None and len(ads) >= limit:
                        self.last_stats = stats
                        return tuple(ads)
            page += 1
        self.last_stats = stats
        return tuple(ads)

    def product_ids_for_page(self, page: int) -> tuple[str, ...]:
        suffix = "" if page == 1 else f"&page={page}"
        url = f"{self.site_url}/products?direction=asc&sort=id&search_type%5Bpart_id%5D=1{suffix}"
        soup = BeautifulSoup(self.fetch_text(url), "html.parser")
        ids = []
        for anchor in soup.select("div.product h2 a[href], a[href*='/products/']"):
            href = clean(anchor.get("href"))
            if "/products/" in href:
                ids.append(href.rstrip("/").split("/")[-1])
        return tuple(dict.fromkeys(ids))

    def parse_product(self, product_id: str, *, stats: ProviderParseStats) -> LegacyAd | None:
        product_url = f"{self.site_url}/products/{product_id}"
        soup = BeautifulSoup(self.fetch_text(product_url), "html.parser")
        product_block = soup.select_one("div.product_show") or soup
        image_node = product_block.select_one("div.product_info img[src], img[src]")
        image_url = urljoin(self.site_url, clean(image_node.get("src"))) if image_node else ""
        if not image_url:
            stats.skip(f"product={product_id} skipped: missing image")
            return None
        headings = [
            node.get_text(" ", strip=True)
            for node in product_block.select("div.block_info h2, h2")
            if node.get_text(" ", strip=True)
        ]
        if len(headings) < 2:
            stats.skip(f"product={product_id} skipped: missing brand/model")
            return None
        brand, model = headings[0], headings[1]
        params = self.params_from_block(product_block)
        width = params.get("Ширина")
        height = params.get("Высота")
        size = params.get("Диаметр диска")
        if not all((width, height, size)):
            stats.skip(f"product={product_id} skipped: missing tire dimensions")
            return None
        season = params.get("Сезонность") or "лето"
        price = parse_decimal(params.get("Цена"))
        description_node = product_block.select_one(
            "div.product_description div.description, .description"
        )
        name = f"{brand} {model} {width}/{height}/R{size}"
        return LegacyAd(
            source=self.provider_key,
            external_id=product_id,
            type_id=31,
            name=name,
            description=strip_html(description_node.get_text(" ", strip=True))
            if description_node
            else name,
            price=price,
            currency=1,
            condition=2,
            phone=tuple(self.settings.phones_for_provider(self.provider_key)),
            images=(image_url,),
            tire_width=width.replace(".00", "").replace(".0", "").replace(".50", ".5"),
            tire_height=height,
            tire_size=size,
            tire_type=tire_type_from_text(season),
            raw={"product_url": product_url, "brand": brand, "model": model, "params": params},
        )

    def params_from_block(self, product_block) -> dict[str, str]:
        params: dict[str, str] = {}
        for node in product_block.select("div.param p, .param p, p"):
            text = node.get_text(" ", strip=True)
            if ": " in text:
                key, value = text.split(": ", 1)
                params[key.strip()] = value.strip()
        return params
