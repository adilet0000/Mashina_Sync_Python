import re
from collections.abc import Callable, Iterable
from decimal import Decimal

from defusedxml import ElementTree

from app.config import Settings
from app.dto import LegacyAd
from app.providers.base import ProviderAdapter
from app.providers.common import ProviderParseStats, clean, ordered_images, parse_decimal
from app.utils.http import HttpClientConfig, ProviderHttpClient


class AutocrmProviderAdapter(ProviderAdapter):
    feed_url: str
    client_id: str
    condition_id = 4
    currency_id: int = 1
    currency_rate: Decimal = Decimal("1")
    preserve_current_fields: tuple[str, ...] = ()

    def __init__(
        self,
        settings: Settings,
        *,
        fetch_bytes: Callable[[str], bytes] | None = None,
    ) -> None:
        self.settings = settings
        self.fetch_bytes = (
            fetch_bytes
            or ProviderHttpClient(HttpClientConfig(timeout=settings.sync_http_timeout)).get_bytes
        )
        self.last_stats = ProviderParseStats()

    def fetch_ads(self, *, limit: int | None = None) -> Iterable[LegacyAd]:
        stats = ProviderParseStats()
        ads = list(self.parse_feed(self.fetch_bytes(self.feed_url), stats=stats))
        ads = self.post_process_ads(ads)
        self.last_stats = stats
        return tuple(ads[:limit]) if limit is not None else tuple(ads)

    def parse_feed(
        self, content: bytes | str, *, stats: ProviderParseStats
    ) -> tuple[LegacyAd, ...]:
        root = ElementTree.fromstring(content)
        cars = root.findall(".//car")
        if not cars and root.tag == "car":
            cars = [root]
        ads: list[LegacyAd] = []
        for car in cars:
            stats.read_count += 1
            ad = self.ad_from_car(car, stats=stats)
            if ad is not None:
                ads.append(ad)
        return tuple(ads)

    def post_process_ads(self, ads: list[LegacyAd]) -> list[LegacyAd]:
        return ads

    def ad_from_car(self, car, *, stats: ProviderParseStats) -> LegacyAd | None:
        vin = self.text(car, "vin")
        if not vin:
            stats.skip("car skipped: missing VIN")
            return None
        images = self.images_from_car(car)
        if not images:
            stats.skip(f"car={vin} skipped: missing images")
            return None
        make = self.make_fallback(vin, self.text(car, "mark_id"))
        model = self.model_fallback(vin, self.text(car, "folder_id"))
        year = self.text(car, "year")
        if not make or not model:
            stats.skip(f"car={vin} skipped: missing make/model")
            return None
        featured_option = self.featured_option_from_availability(self.text(car, "availability"))
        price = self.price_from_car(car)
        description = self.description_from_car(car)
        return LegacyAd(
            source=self.provider_key,
            external_id=vin,
            type_id=1,
            name=" ".join(part for part in (make, model, year) if part),
            description=description,
            price=price,
            currency=self.currency_id,
            make=make,
            model=model,
            generation=self.text(car, "modification_id") or None,
            body=self.text(car, "body_type") or None,
            fuel=self.text(car, "engine_type") or "Бензин",
            transmission=self.text(car, "drive") or "Передний",
            gear_box=self.text(car, "gearbox") or None,
            modification=self.text(car, "engine_volume")
            or self.text(car, "modification_id")
            or None,
            complectation=self.text(car, "complectation_name") or None,
            steering_wheel=self.text(car, "wheel") or None,
            color=self.text(car, "color") or "Серебряный",
            mileage=self.text(car, "run") or None,
            customs=1 if featured_option == 1 else 0,
            vincode=vin,
            condition=self.condition_id,
            phone=tuple(self.settings.phones_for_provider(self.provider_key)),
            images=ordered_images(images),
            year=year or None,
            raw={
                "client_id": self.client_id,
                "featured_option": featured_option,
                "preserve_current_fields": list(self.preserve_current_fields),
            },
        )

    def text(self, car, name: str) -> str:
        node = car.find(name)
        if node is None:
            node = car.find(f".//{name}")
        return clean(node.text if node is not None else "")

    def images_from_car(self, car) -> tuple[str, ...]:
        urls: list[str] = []
        for node in car.findall(".//images/image"):
            if clean(node.text):
                urls.append(clean(node.text))
        if not urls:
            for node in car.findall(".//image"):
                if clean(node.text):
                    urls.append(clean(node.text))
        return tuple(dict.fromkeys(urls))

    def featured_option_from_availability(self, availability: str) -> int:
        normalized = availability.lower()
        if normalized == "на заказ":
            return 3
        return 1

    def price_from_car(self, car) -> Decimal | None:
        price = parse_decimal(self.text(car, "price"))
        if price is None:
            return None
        if self.currency_id != 1 and self.currency_rate:
            return (price / self.currency_rate).quantize(Decimal("1"))
        return price

    def description_from_car(self, car) -> str:
        description = self.text(car, "description")
        if description:
            return description
        extras = self.text(car, "extras")
        return re.sub(r"([,])([А-Яа-яA-Za-z])", r"\1 \2", extras)

    def make_fallback(self, vin: str, make: str) -> str:
        return make

    def model_fallback(self, vin: str, model: str) -> str:
        return model
