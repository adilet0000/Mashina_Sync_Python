from app.config import Settings
from app.providers.autocrm import AutocrmProviderAdapter

LEXUS_FEED_URL = (
    "https://autos.autocrm.ru/api/auto-ru/feed?id=Hx50rUu2S3AW_Tzk-0-7jQ%3D%3D&isUsed=0"
)


class LexusProviderAdapter(AutocrmProviderAdapter):
    provider_key = "lexus"
    client_id = "Lexus"
    feed_url = LEXUS_FEED_URL
    condition_id = 4
    currency_id = 1
    preserve_current_fields = ("price",)

    def __init__(self, settings: Settings, **kwargs) -> None:
        super().__init__(settings, **kwargs)
        self.feed_url = settings.sync_provider_lexus_feed_url or LEXUS_FEED_URL

    def make_fallback(self, vin: str, make: str) -> str:
        return make or "Lexus"

    def model_fallback(self, vin: str, model: str) -> str:
        if model:
            return model
        if len(vin) > 3 and vin[3] == "J":
            return "GX"
        return model
