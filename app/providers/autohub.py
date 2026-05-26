from app.config import Settings
from app.providers.bazon import BazonKeys, GroupedPartsCsvProviderAdapter

AUTOHUB_FEED_URL = "https://baz-on.ru/export/c1010/af1b1/mashina-parts.csv"


class AutohubProviderAdapter(GroupedPartsCsvProviderAdapter):
    provider_key = "autohub"
    feed_url = AUTOHUB_FEED_URL
    import_price = False
    required_fields = (
        BazonKeys.ID,
        BazonKeys.NAME,
        BazonKeys.MAKE,
        BazonKeys.MODEL,
        BazonKeys.YEAR,
        BazonKeys.GENERATION,
    )

    def __init__(self, settings: Settings, **kwargs) -> None:
        super().__init__(settings, **kwargs)
        self.feed_url = settings.sync_provider_autohub_feed_url or AUTOHUB_FEED_URL
