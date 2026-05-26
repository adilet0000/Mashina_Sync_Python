from app.config import Settings
from app.dto import LegacyAd
from app.providers.autocrm import AutocrmProviderAdapter

KIA_FEED_URL = "https://autos.autocrm.ru/api/auto-ru/feed?id=ke1JvLaOSF_46BxK5pERig%3D%3D&isUsed=0"


class KiaProviderAdapter(AutocrmProviderAdapter):
    provider_key = "kia"
    client_id = "Kia"
    feed_url = KIA_FEED_URL
    condition_id = 4
    currency_id = 2

    def __init__(self, settings: Settings, **kwargs) -> None:
        super().__init__(settings, **kwargs)
        self.feed_url = settings.sync_provider_kia_feed_url or KIA_FEED_URL

    def make_fallback(self, vin: str, make: str) -> str:
        return make or "Kia"

    def model_fallback(self, vin: str, model: str) -> str:
        if model:
            return model
        prefix = vin[:5]
        if prefix in {"KNAPV", "KNAPX", "E2203"}:
            return "Sportage"
        if prefix == "E2206":
            return "Stinger"
        return model

    def post_process_ads(self, ads: list[LegacyAd]) -> list[LegacyAd]:
        ordered = sorted(ads, key=lambda ad: int(ad.raw.get("featured_option") or 999))
        seen: set[str] = set()
        result: list[LegacyAd] = []
        for ad in ordered:
            complectation = ad.complectation or "#empty#"
            key = f"{ad.modification}_{complectation}"
            if key == "#empty#":
                result.append(ad)
                continue
            if key in seen:
                continue
            seen.add(key)
            result.append(ad)
        return result
