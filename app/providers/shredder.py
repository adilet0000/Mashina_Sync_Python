from app.config import Settings
from app.providers.bazon import BazonKeys, GroupedPartsCsvProviderAdapter

SHREDDER_FEED_URL = "https://baz-on.ru/export/c3846/2bd53/mashinakg-parts.csv"


class ShredderProviderAdapter(GroupedPartsCsvProviderAdapter):
    provider_key = "shredder"
    feed_url = SHREDDER_FEED_URL
    import_price = False
    required_fields = (BazonKeys.ID, BazonKeys.NAME, BazonKeys.MAKE, BazonKeys.MODEL)
    include_generation_in_name = False

    def __init__(self, settings: Settings, **kwargs) -> None:
        super().__init__(settings, **kwargs)
        self.feed_url = settings.sync_provider_shredder_feed_url or SHREDDER_FEED_URL
