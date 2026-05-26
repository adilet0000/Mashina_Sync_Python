from app.config import Settings
from app.providers.autocrm import AutocrmProviderAdapter

TOYOTA_FEED_URL = (
    "https://autos.autocrm.ru/api/auto-ru/feed?id=XeDujzeU5NcOmu-BV1cz8A%3D%3D&isUsed=0"
)


class ToyotaProviderAdapter(AutocrmProviderAdapter):
    provider_key = "toyota"
    client_id = "Toyota"
    feed_url = TOYOTA_FEED_URL
    condition_id = 4
    currency_id = 1
    preserve_current_fields = ("description", "price")

    def __init__(self, settings: Settings, **kwargs) -> None:
        super().__init__(settings, **kwargs)
        self.feed_url = settings.sync_provider_toyota_feed_url or TOYOTA_FEED_URL
