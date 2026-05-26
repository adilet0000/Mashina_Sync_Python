from decimal import Decimal

from app.config import Settings
from app.providers.autocrm import AutocrmProviderAdapter

TOYOTA_TRADEIN_FEED_URL = (
    "https://autos.autocrm.ru/api/auto-ru/feed?id=XeDujzeU5NcOmu-BV1cz8A%3D%3D&isUsed=1"
)


class ToyotaTradeinProviderAdapter(AutocrmProviderAdapter):
    provider_key = "toyota_tradein"
    client_id = "ToyotaTradein"
    feed_url = TOYOTA_TRADEIN_FEED_URL
    condition_id = 1
    currency_id = 2
    preserve_current_fields = ("price", "old_price")

    def __init__(self, settings: Settings, **kwargs) -> None:
        super().__init__(settings, **kwargs)
        self.feed_url = settings.sync_provider_toyota_tradein_feed_url or TOYOTA_TRADEIN_FEED_URL
        self.currency_rate = Decimal(str(settings.sync_provider_toyota_tradein_currency_rate or 1))
