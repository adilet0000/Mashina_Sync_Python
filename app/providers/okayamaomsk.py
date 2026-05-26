from app.config import Settings
from app.dto import LegacyAd
from app.providers.bazon import BazonCsvProviderAdapter, BazonKeys
from app.providers.common import clean, parse_decimal

OKAYAMAOMSK_FEED_URL = "https://baz-on.ru/export/c614/e5dc9/car-kg-parts.csv"
OKAYAMA_DELIVERY_TEXT = (
    "\n\nДоставка в Кыргызстан. Оплата наличными или переводом после согласования с менеджером."
)


class OkayamaomskProviderAdapter(BazonCsvProviderAdapter):
    provider_key = "okayamaomsk"
    feed_url = OKAYAMAOMSK_FEED_URL
    import_price = True
    required_fields = (BazonKeys.ID, BazonKeys.NAME, BazonKeys.MAKE)

    def __init__(self, settings: Settings, **kwargs) -> None:
        super().__init__(settings, **kwargs)
        self.feed_url = settings.sync_provider_okayamaomsk_feed_url or OKAYAMAOMSK_FEED_URL

    def ad_from_row(self, row: dict[str, object]) -> LegacyAd:
        description = self.description_from_row(row)
        return LegacyAd(
            source=self.provider_key,
            external_id=clean(row.get(BazonKeys.ID)),
            type_id=30,
            name=self.name_from_row(row),
            description=description,
            price=parse_decimal(row.get(BazonKeys.PRICE)),
            currency=1,
            region=9,
            town=62,
            make=clean(row.get(BazonKeys.MAKE)) or None,
            model=clean(row.get(BazonKeys.MODEL)) or None,
            condition=1,
            phone=self.phones(),
            images=tuple(row[BazonKeys.PHOTOS]),
            raw={
                **row,
                "featured_option": 2,
                "comment_allowed": 2,
            },
        )

    def name_from_row(self, row: dict[str, object]) -> str:
        chunks = [
            clean(row.get(BazonKeys.NAME)),
            clean(row.get(BazonKeys.MAKE)),
            clean(row.get(BazonKeys.MODEL)),
        ]
        return " ".join(chunk for chunk in chunks if chunk)

    def description_from_row(self, row: dict[str, object]) -> str:
        chunks = []
        for field in (
            BazonKeys.NAME,
            BazonKeys.MAKE,
            BazonKeys.MODEL,
            BazonKeys.GENERATION,
            BazonKeys.ENGINE,
            BazonKeys.YEAR,
            BazonKeys.PART_NUMBER,
            BazonKeys.COMMENT,
        ):
            if clean(row.get(field)):
                label = f"{field}: " if field in {BazonKeys.PART_NUMBER} else ""
                chunks.append(label + clean(row.get(field)))
        return " ".join(chunks).strip() + OKAYAMA_DELIVERY_TEXT
