from collections import defaultdict
from collections.abc import Callable, Iterable
from decimal import Decimal
from typing import Any

from app.config import Settings
from app.dto import LegacyAd
from app.providers.base import ProviderAdapter
from app.providers.common import (
    ProviderParseStats,
    clean,
    condition_id_from_text,
    parse_csv_rows,
    parse_decimal,
    split_photos,
    tire_type_from_text,
)
from app.utils.http import HttpClientConfig, ProviderHttpClient


class BazonKeys:
    ID = "Артикул"
    NAME = "Наименование"
    MAKE = "Марка"
    MODEL = "Модель"
    YEAR = "Год"
    GENERATION = "Кузов"
    ENGINE = "Двигатель"
    TOP_BOTTOM = "Верх/Низ"
    FRONT_REAR = "Перед/Зад"
    LEFT_RIGHT = "Лев/Прав"
    COLOR = "Цвет"
    PART_NUMBER = "Номер"
    COMMENT = "Комментарий"
    PRICE = "Цена"
    MANUFACTURER = "Производитель"
    PHOTOS = "Фото"
    CONDITION = "Новый/БУ"
    AVAILABILITY = "Статус"
    WHEEL_SIZE = "Диаметр диска"
    WHEEL_TYPE = "Тип диска"
    WHEEL_PCD = "PCD диска"
    WHEEL_MANUFACTURER = "Производитель диска"
    WHEEL_STYLE = "Модель диска"
    WHEEL_SHELF = "Вылет диска"
    TIRE_TYPE = "Сезон шины (лето, зима, шипы)"
    TIRE_WIDTH = "Ширина профиля шины"
    TIRE_HEIGHT = "Высота профиля шины"
    TIRE_SIZE = "Посадочный диаметр шины"
    TIRE_WEAR = "Износ шин"
    TIRE_MANUFACTURER = "Производитель шины"
    TIRE_YEAR = "Дата производства"
    TIRE_WHEEL_CONDITION = "Новое/БУ"
    IS_WHEEL_OR_TIRE = "Тип (диск, шина, колесо)"
    QUANTITY_INCLUDED = "Количество в комплекте"


COMMERCIAL_MAKES = {"setra", "neoplan", "man"}


class BazonCsvProviderAdapter(ProviderAdapter):
    feed_url: str
    max_images = 12
    import_price = False
    require_images = True
    required_fields = (BazonKeys.ID, BazonKeys.NAME, BazonKeys.MAKE, BazonKeys.MODEL)

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
        rows = self.parse_feed(self.fetch_bytes(self.feed_url))
        ads = self.rows_to_ads(rows)
        return tuple(ads[:limit]) if limit is not None else tuple(ads)

    def parse_feed(self, content: bytes | str) -> tuple[dict[str, Any], ...]:
        stats = ProviderParseStats()
        rows: list[dict[str, Any]] = []
        for index, raw in enumerate(parse_csv_rows(content), start=2):
            stats.read_count += 1
            row = self.sanitize_row(raw, index=index, stats=stats)
            if row is not None:
                rows.append(row)
        self.last_stats = stats
        return tuple(rows)

    def sanitize_row(
        self,
        raw: dict[str, str],
        *,
        index: int,
        stats: ProviderParseStats,
    ) -> dict[str, Any] | None:
        for field_name in self.required_fields:
            if not raw.get(field_name):
                stats.skip(f"row={index} skipped: missing {field_name}")
                return None
        photos = split_photos(raw.get(BazonKeys.PHOTOS), max_count=self.max_images)
        if self.require_images and not photos:
            stats.skip(f"row={index} skipped: missing photos")
            return None
        row: dict[str, Any] = dict(raw)
        row[BazonKeys.PHOTOS] = photos
        return row

    def rows_to_ads(self, rows: tuple[dict[str, Any], ...]) -> tuple[LegacyAd, ...]:
        return tuple(self.ad_from_row(row) for row in rows)

    def ad_from_row(self, row: dict[str, Any]) -> LegacyAd:
        raise NotImplementedError

    def phones(self) -> tuple[str, ...]:
        return tuple(self.settings.phones_for_provider(self.provider_key))


class GroupedPartsCsvProviderAdapter(BazonCsvProviderAdapter):
    group_key_fields = (
        BazonKeys.NAME,
        BazonKeys.MAKE,
        BazonKeys.MODEL,
        BazonKeys.YEAR,
        BazonKeys.GENERATION,
    )
    include_generation_in_name = True

    def rows_to_ads(self, rows: tuple[dict[str, Any], ...]) -> tuple[LegacyAd, ...]:
        grouped: dict[tuple[str, ...], dict[str, dict[str, Any]]] = defaultdict(dict)
        for row in rows:
            key = tuple(clean(row.get(field)) for field in self.group_key_fields)
            grouped[key][clean(row.get(BazonKeys.ID))] = row
        return tuple(self.ad_from_group(tuple(entries.values())) for entries in grouped.values())

    def ad_from_group(self, rows: tuple[dict[str, Any], ...]) -> LegacyAd:
        if len(rows) == 1:
            return self.ad_from_row(rows[0])
        first = rows[0]
        external_id = ",".join(clean(row.get(BazonKeys.ID)) for row in rows)
        desc_items = [
            f"{index}) {self.description_from_row(row, multiple=True)}"
            for index, row in enumerate(rows, start=1)
        ]
        description = f"{self.name_from_row(first, multiple=True)}\n{len(rows)} шт. в наличии:\n"
        description += "\n".join(desc_items)
        photos = tuple(dict.fromkeys(photo for row in rows for photo in row[BazonKeys.PHOTOS]))
        base = self.ad_from_row(first)
        return LegacyAd(
            source=self.provider_key,
            external_id=external_id,
            type_id=base.type_id,
            name=self.name_from_row(first, multiple=True),
            description=description,
            price=base.price,
            currency=base.currency,
            make=base.make,
            model=base.model,
            year=base.year,
            generation=base.generation,
            condition=base.condition,
            phone=base.phone,
            images=photos,
            raw={"grouped_articles": [row[BazonKeys.ID] for row in rows], "rows": list(rows)},
        )

    def ad_from_row(self, row: dict[str, Any]) -> LegacyAd:
        is_commercial = clean(row.get(BazonKeys.MAKE)).lower() in COMMERCIAL_MAKES
        return LegacyAd(
            source=self.provider_key,
            external_id=clean(row.get(BazonKeys.ID)),
            type_id=36 if is_commercial else 30,
            name=self.name_from_row(row, is_commercial=is_commercial),
            description=self.description_from_row(row),
            price=self.price_from_row(row),
            currency=1,
            make=None if is_commercial else clean(row.get(BazonKeys.MAKE)) or None,
            model=None if is_commercial else clean(row.get(BazonKeys.MODEL)) or None,
            year=clean(row.get(BazonKeys.YEAR)) or None,
            generation=clean(row.get(BazonKeys.GENERATION)) or None,
            condition=1,
            phone=self.phones(),
            images=tuple(row[BazonKeys.PHOTOS]),
            raw=row,
        )

    def price_from_row(self, row: dict[str, Any]) -> Decimal | None:
        if self.import_price:
            return parse_decimal(row.get(BazonKeys.PRICE))
        return Decimal("0")

    def name_from_row(
        self,
        row: dict[str, Any],
        *,
        is_commercial: bool = False,
        multiple: bool = False,
    ) -> str:
        chunks = [clean(row.get(BazonKeys.NAME))]
        if is_commercial:
            chunks.extend([clean(row.get(BazonKeys.MAKE)), clean(row.get(BazonKeys.MODEL))])
        elif self.include_generation_in_name and clean(row.get(BazonKeys.GENERATION)):
            chunks.append(clean(row.get(BazonKeys.GENERATION)))
        return " ".join(chunk for chunk in chunks if chunk)

    def description_from_row(self, row: dict[str, Any], *, multiple: bool = False) -> str:
        chunks: list[str] = []
        if clean(row.get(BazonKeys.NAME)) and not multiple:
            chunks.append(clean(row.get(BazonKeys.NAME)) + "\n")
        if not multiple:
            chunks.extend([clean(row.get(BazonKeys.MAKE)), clean(row.get(BazonKeys.MODEL))])
        for field in (
            BazonKeys.GENERATION,
            BazonKeys.ENGINE,
            BazonKeys.YEAR,
            BazonKeys.TOP_BOTTOM,
            BazonKeys.FRONT_REAR,
            BazonKeys.LEFT_RIGHT,
            BazonKeys.COLOR,
        ):
            if clean(row.get(field)):
                chunks.append(clean(row.get(field)))
        if clean(row.get(BazonKeys.COMMENT)):
            chunks.append(("\n" if not multiple else "") + clean(row.get(BazonKeys.COMMENT)))
        return " ".join(chunk for chunk in chunks if chunk).replace("\n ", "\n")


class TireWheelCsvProviderAdapter(BazonCsvProviderAdapter):
    required_fields = (
        BazonKeys.ID,
        BazonKeys.TIRE_WHEEL_CONDITION,
        BazonKeys.IS_WHEEL_OR_TIRE,
    )
    import_price = True

    def ad_from_row(self, row: dict[str, Any]) -> LegacyAd:
        kind = clean(row.get(BazonKeys.IS_WHEEL_OR_TIRE)).lower() or "шина"
        type_id = 31 if kind == "шина" else 32
        price = parse_decimal(row.get(BazonKeys.PRICE)) if self.import_price else Decimal("0")
        return LegacyAd(
            source=self.provider_key,
            external_id=clean(row.get(BazonKeys.ID)),
            type_id=type_id,
            name=self.name_from_tire_wheel(row, kind),
            description=self.description_from_tire_wheel(row, kind),
            price=price,
            currency=1,
            condition=condition_id_from_text(row.get(BazonKeys.TIRE_WHEEL_CONDITION)),
            phone=self.phones(),
            images=tuple(row[BazonKeys.PHOTOS]),
            tire_width=clean(row.get(BazonKeys.TIRE_WIDTH)) or None,
            tire_height=clean(row.get(BazonKeys.TIRE_HEIGHT)) or None,
            tire_size=clean(row.get(BazonKeys.TIRE_SIZE)) or None,
            tire_type=tire_type_from_text(row.get(BazonKeys.TIRE_TYPE)) if kind == "шина" else None,
            wheel_type=clean(row.get(BazonKeys.WHEEL_TYPE)) or None,
            wheel_size=clean(row.get(BazonKeys.WHEEL_SIZE)) or None,
            wheel_pcd=clean(row.get(BazonKeys.WHEEL_PCD)).split(",")[0].strip() or None,
            raw=row,
        )

    def sanitize_row(
        self,
        raw: dict[str, str],
        *,
        index: int,
        stats: ProviderParseStats,
    ) -> dict[str, Any] | None:
        row = super().sanitize_row(raw, index=index, stats=stats)
        if row is None:
            return None
        kind = clean(row.get(BazonKeys.IS_WHEEL_OR_TIRE)).lower() or "шина"
        if kind == "шина":
            for field_name in (
                BazonKeys.TIRE_TYPE,
                BazonKeys.TIRE_WIDTH,
                BazonKeys.TIRE_HEIGHT,
                BazonKeys.TIRE_SIZE,
            ):
                if not row.get(field_name):
                    stats.skip(f"row={index} skipped: missing {field_name}")
                    return None
        return row

    def name_from_tire_wheel(self, row: dict[str, Any], kind: str) -> str:
        if kind in {"колесо", "диск"}:
            wheel_size = clean(row.get(BazonKeys.WHEEL_SIZE))
            wheel_pcd = clean(row.get(BazonKeys.WHEEL_PCD))
            name = f"Диск R{wheel_size} {wheel_pcd}".strip()
            if kind == "колесо":
                name += " с шиной"
            return name
        return (
            f"Шина {clean(row.get(BazonKeys.TIRE_WIDTH))}/"
            f"{clean(row.get(BazonKeys.TIRE_HEIGHT))}/R{clean(row.get(BazonKeys.TIRE_SIZE))}"
        )

    def description_from_tire_wheel(self, row: dict[str, Any], kind: str) -> str:
        chunks: list[str] = []
        if kind in {"колесо", "диск"}:
            for field in (
                BazonKeys.WHEEL_MANUFACTURER,
                BazonKeys.WHEEL_STYLE,
                BazonKeys.WHEEL_SHELF,
            ):
                if clean(row.get(field)):
                    chunks.append(f"{field}: {clean(row.get(field))}")
            if kind == "колесо" and all(
                clean(row.get(field))
                for field in (BazonKeys.TIRE_WIDTH, BazonKeys.TIRE_HEIGHT, BazonKeys.TIRE_SIZE)
            ):
                tire_width = row[BazonKeys.TIRE_WIDTH]
                tire_height = row[BazonKeys.TIRE_HEIGHT]
                tire_size = row[BazonKeys.TIRE_SIZE]
                chunks.append(f"Шина: {tire_width}/{tire_height}/R{tire_size}")
        else:
            chunks.append(
                f"Шина: {clean(row.get(BazonKeys.TIRE_WIDTH))}/"
                f"{clean(row.get(BazonKeys.TIRE_HEIGHT))}/R{clean(row.get(BazonKeys.TIRE_SIZE))}"
            )
        for label, field in (
            ("Сезон", BazonKeys.TIRE_TYPE),
            (BazonKeys.TIRE_MANUFACTURER, BazonKeys.TIRE_MANUFACTURER),
            (BazonKeys.TIRE_YEAR, BazonKeys.TIRE_YEAR),
            (BazonKeys.TIRE_WEAR, BazonKeys.TIRE_WEAR),
            (BazonKeys.ID, BazonKeys.ID),
        ):
            if clean(row.get(field)):
                value = clean(row.get(field))
                if label == "Сезон":
                    value = value.lower()
                chunks.append(f"{label}: {value}")
        if clean(row.get(BazonKeys.COMMENT)):
            chunks.append(clean(row.get(BazonKeys.COMMENT)))
        return "\n".join(chunks)
