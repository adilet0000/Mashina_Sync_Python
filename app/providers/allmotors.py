from collections.abc import Callable, Iterable
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.config import Settings
from app.dto import LegacyAd
from app.providers.base import ProviderAdapter
from app.providers.common import (
    ProviderParseStats,
    clean,
    mashina_proxy_image_url,
    parse_decimal,
    parse_tire_dimensions,
    strip_html,
    tire_type_from_text,
)
from app.utils.http import HttpClientConfig, ProviderHttpClient

ALLMOTORS_SITE_URL = "https://allmotors.kg"

ALLMOTORS_CATEGORY_TYPES = {
    "shiny-diski": 31,
    "masla-filtry": 30,
    "aksessuary/dvorniki-poliki-steklopodemniki": 33,
    "aksessuary/sistemy-osnashcheniya-salona-gadzhety": 33,
    "akkumulyatory": 30,
    "kuzovnye-zapchasti/zamki-petli-ruchki": 30,
    "kuzovnye-zapchasti/balki-krepleniya-kpp": 30,
    "kuzovnye-zapchasti/elektrolyuki": 30,
    "kuzovnye-zapchasti/reshetki-radiatorov": 30,
    "kuzovnye-zapchasti/kryshki-bagazhnikov": 30,
    "kuzovnye-zapchasti/moldingi": 30,
    "kuzovnye-zapchasti/porogi": 30,
    "kuzovnye-zapchasti/bampera": 30,
    "kuzovnye-zapchasti/kapoty": 30,
    "kuzovnye-zapchasti/krylya": 30,
    "kuzovnye-zapchasti/dveri": 30,
    "kuzovnye-zapchasti/zerkala": 30,
    "dvigateli-i-navesnoe-oborudovanie": 30,
    "podveska-hodovaya-chast/rulevaya-chast": 30,
    "transmissiya-korobka-peredach-privod-i-t-d": 30,
    "optika/povorotniki": 30,
    "optika/protivotumanki": 30,
    "optika/fonari": 30,
    "optika/fary": 30,
    "sistemy-ohlazhdeniya": 30,
    "stekla": 30,
    "toplivnaya-sistema": 30,
    "elektronika/audiosistema-zvuk": 30,
    "elektronika/datchiki": 30,
    "elektronika/bloki": 30,
    "elektronika/kompyutery": 30,
    "salon/podushki-bezopasnosti": 30,
    "salon/obshivki-paneli-oblicovki-salona": 30,
    "tormoznaya-sistema": 30,
    "sistemy-kondicionirovaniya-ventilyacii-i-obogreva-salona": 30,
    "bachki-patrubki-vozduhovody-1/bachki-patrubki-vozduhovody-shlangi": 30,
}


class AllmotorsProviderAdapter(ProviderAdapter):
    provider_key = "allmotors"

    def __init__(
        self,
        settings: Settings,
        *,
        fetch_text: Callable[[str], str] | None = None,
    ) -> None:
        self.settings = settings
        self.site_url = settings.sync_provider_allmotors_base_url or ALLMOTORS_SITE_URL
        self.fetch_text = (
            fetch_text
            or ProviderHttpClient(HttpClientConfig(timeout=settings.sync_http_timeout)).get_text
        )
        self.last_stats = ProviderParseStats()

    def fetch_ads(self, *, limit: int | None = None) -> Iterable[LegacyAd]:
        stats = ProviderParseStats()
        ads: list[LegacyAd] = []
        for category in ALLMOTORS_CATEGORY_TYPES:
            page = 1
            while True:
                product_links = self.product_links_for_category(category, page=page)
                if not product_links:
                    break
                for link in product_links:
                    stats.read_count += 1
                    ad = self.parse_product_page(link, category, stats=stats)
                    if ad is not None:
                        ads.append(ad)
                        if limit is not None and len(ads) >= limit:
                            self.last_stats = stats
                            return tuple(ads)
                page += 1
        self.last_stats = stats
        return tuple(ads)

    def product_links_for_category(self, category: str, *, page: int) -> tuple[str, ...]:
        url = f"{self.site_url}/categories/{category}" + (f"?page={page}" if page > 1 else "")
        soup = BeautifulSoup(self.fetch_text(url), "html.parser")
        links: list[str] = []
        for anchor in soup.select("div.category-product h3.name a, a[href*='/products/']"):
            href = anchor.get("href")
            if href and "/products/" in href:
                links.append(urljoin(self.site_url, href))
        return tuple(dict.fromkeys(links))

    def parse_product_page(
        self,
        product_url: str,
        category: str,
        *,
        stats: ProviderParseStats,
    ) -> LegacyAd | None:
        soup = BeautifulSoup(self.fetch_text(product_url), "html.parser")
        product_block = soup.select_one("div.detail-block") or soup
        slug = urlparse(product_url).path.rstrip("/").split("/")[-1]
        category_id = ALLMOTORS_CATEGORY_TYPES.get(category, 30)
        if category not in ALLMOTORS_CATEGORY_TYPES:
            stats.warnings.append(f"category unknown: {category}; fallback type_id=30")
        images = self.images_from_product(product_block)
        if not images:
            stats.skip(f"product={slug} skipped: missing images")
            return None
        title_node = product_block.select_one("h1.name, h1")
        if title_node is None:
            stats.skip(f"product={slug} skipped: missing title")
            return None
        full_title = title_node.get_text(" ", strip=True)
        title = full_title.split(", ")[-1] if ", " in full_title else full_title
        width, height, size = parse_tire_dimensions(title)
        if category == "shiny-diski" and not all((width, height, size)):
            stats.skip(f"product={slug} skipped: tire dimensions not found")
            return None
        price_node = product_block.select_one("span.price, .price")
        description_node = product_block.select_one(
            "#description p.text, .product-tabs #description, .description"
        )
        return LegacyAd(
            source=self.provider_key,
            external_id=slug,
            type_id=category_id,
            name=title,
            description=strip_html(description_node.get_text(" ", strip=True))
            if description_node
            else full_title,
            price=parse_decimal(price_node.get_text(" ", strip=True)) if price_node else None,
            currency=1,
            condition=2 if category in {"masla-filtry", "akkumulyatory"} else 1,
            phone=tuple(self.settings.phones_for_provider(self.provider_key)),
            images=images,
            tire_width=width,
            tire_height=height,
            tire_size=size,
            tire_type=tire_type_from_text(title) if category == "shiny-diski" else None,
            raw={"category": category, "product_url": product_url, "full_title": full_title},
        )

    def images_from_product(self, product_block) -> tuple[str, ...]:
        urls: list[str] = []
        for node in product_block.select("div#owl-single-product a[href], .gallery-holder a[href]"):
            url = clean(node.get("href"))
            if url:
                urls.append(mashina_proxy_image_url(urljoin(self.site_url, url)))
        if not urls:
            for node in product_block.select("img[src]"):
                url = clean(node.get("src"))
                if url:
                    urls.append(mashina_proxy_image_url(urljoin(self.site_url, url)))
        return tuple(dict.fromkeys(urls))
