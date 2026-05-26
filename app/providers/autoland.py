import csv
from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from io import StringIO
from typing import Any

from app.config import Settings
from app.dto import LegacyAd
from app.providers.base import ProviderAdapter
from app.utils.http import HttpClientConfig, ProviderHttpClient

AUTOLAND_FEED_URL = "https://baz-on.ru/export/c2095/9d8bf/autolandkg-parts.csv"


@dataclass(frozen=True)
class AutolandRow:
    article: str
    name: str
    make: str
    model: str | None
    comment: str | None
    price: Decimal | None
    photos: tuple[str, ...]
    condition_raw: str | None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class AutolandParseStats:
    read_count: int = 0
    skipped_count: int = 0
    warnings: list[str] = field(default_factory=list)


class AutolandProviderAdapter(ProviderAdapter):
    provider_key = "autoland"

    key_article = "Артикул"
    key_name = "Наименование"
    key_make = "Марка"
    key_model = "Модель"
    key_comment = "Комментарий"
    key_price = "Цена"
    key_photos = "Фото"
    key_condition = "Новый/БУ"

    required_fields = (key_article, key_name, key_make)

    def __init__(
        self,
        settings: Settings,
        *,
        fetch_bytes: Callable[[str], bytes] | None = None,
    ) -> None:
        self.settings = settings
        self.feed_url = settings.sync_provider_autoland_feed_url or AUTOLAND_FEED_URL
        self.fetch_bytes = (
            fetch_bytes
            or ProviderHttpClient(HttpClientConfig(timeout=settings.sync_http_timeout)).get_bytes
        )
        self.last_stats = AutolandParseStats()

    def fetch_ads(self, *, limit: int | None = None) -> Iterable[LegacyAd]:
        content = self.fetch_bytes(self.feed_url)
        rows = self.parse_csv(content)
        ads = self.rows_to_legacy_ads(rows)
        if limit is not None:
            return tuple(ads[:limit])
        return tuple(ads)

    def parse_csv(self, content: bytes | str) -> tuple[AutolandRow, ...]:
        text = self.decode_content(content)
        reader = csv.DictReader(StringIO(text), delimiter=";")
        stats = AutolandParseStats()
        rows: list[AutolandRow] = []

        for index, raw_row in enumerate(reader, start=2):
            stats.read_count += 1
            row = self.sanitize_row(raw_row, index=index, stats=stats)
            if row is None:
                stats.skipped_count += 1
                continue
            rows.append(row)

        self.last_stats = stats
        return tuple(rows)

    def rows_to_legacy_ads(self, rows: tuple[AutolandRow, ...]) -> tuple[LegacyAd, ...]:
        grouped: dict[tuple[str, str, str], dict[str, AutolandRow]] = defaultdict(dict)
        for row in rows:
            key = (row.name, row.make, row.model or "")
            grouped[key][row.article] = row

        ads: list[LegacyAd] = []
        for entries_by_article in grouped.values():
            entries = tuple(entries_by_article.values())
            if len(entries) == 1:
                ads.append(self.legacy_ad_from_single(entries[0]))
            else:
                ads.append(self.legacy_ad_from_group(entries))
        return tuple(ads)

    def sanitize_row(
        self,
        raw_row: dict[str, Any],
        *,
        index: int,
        stats: AutolandParseStats,
    ) -> AutolandRow | None:
        normalized = {str(key).strip(): self._clean(value) for key, value in raw_row.items()}
        for field_name in self.required_fields:
            if not normalized.get(field_name):
                stats.warnings.append(f"row={index} skipped: missing {field_name}")
                return None

        photos = self.split_photos(normalized.get(self.key_photos))
        if not photos:
            stats.warnings.append(f"row={index} skipped: missing photos")
            return None

        return AutolandRow(
            article=normalized[self.key_article],
            name=normalized[self.key_name],
            make=normalized[self.key_make],
            model=normalized.get(self.key_model),
            comment=normalized.get(self.key_comment),
            price=self.parse_price(normalized.get(self.key_price), stats=stats),
            photos=photos,
            condition_raw=normalized.get(self.key_condition),
            raw=normalized,
        )

    def legacy_ad_from_single(self, row: AutolandRow) -> LegacyAd:
        return LegacyAd(
            source=self.provider_key,
            external_id=row.article,
            type_id=30,
            name=row.name,
            description=self.description_from_row(row, multiple=False),
            price=row.price,
            currency=1,
            make=row.make,
            model=row.model,
            condition=self.condition_from_row(row),
            phone=tuple(self.settings.phones_for_provider(self.provider_key)),
            images=row.photos,
            raw=row.raw,
        )

    def legacy_ad_from_group(self, rows: tuple[AutolandRow, ...]) -> LegacyAd:
        first = rows[0]
        external_id = ",".join(row.article for row in rows)
        description_items = [
            f"{index}) {self.description_from_row(row, multiple=True)}"
            for index, row in enumerate(rows, start=1)
        ]
        description = f"{first.name}\n\n" + "\n".join(description_items)
        photos = tuple(dict.fromkeys(photo for row in rows for photo in row.photos))
        return LegacyAd(
            source=self.provider_key,
            external_id=external_id,
            type_id=30,
            name=first.name,
            description=description,
            price=first.price,
            currency=1,
            make=first.make,
            model=first.model,
            condition=self.condition_from_row(first),
            phone=tuple(self.settings.phones_for_provider(self.provider_key)),
            images=photos,
            raw={
                "grouped_articles": [row.article for row in rows],
                "rows": [row.raw for row in rows],
            },
        )

    def decode_content(self, content: bytes | str) -> str:
        if isinstance(content, str):
            return content
        for encoding in ("cp1251", "windows-1251", "utf-8-sig", "utf-8"):
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                continue
        return content.decode("cp1251", errors="replace")

    def split_photos(self, value: str | None) -> tuple[str, ...]:
        if not value:
            return ()
        return tuple(photo.strip() for photo in value.split(", ") if photo.strip())

    def parse_price(self, value: str | None, *, stats: AutolandParseStats) -> Decimal | None:
        if not value:
            return None
        cleaned = value.replace(" ", "").replace(",", ".")
        try:
            return Decimal(cleaned)
        except InvalidOperation:
            stats.warnings.append(f"invalid price skipped value={value!r}")
            return None

    def condition_from_row(self, row: AutolandRow) -> int:
        if row.condition_raw == "Новый" and row.name == "Товары из Дордоя":
            return 2
        return 1

    def description_from_row(self, row: AutolandRow, *, multiple: bool) -> str:
        if row.comment:
            return row.comment
        if row.name and not multiple:
            return row.name
        return ""

    def _clean(self, value: Any) -> str:
        return str(value or "").strip()
