# ruff: noqa: E501

import pytest
from app.config.settings import Settings
from app.mappers import ListingMapper
from app.providers import (
    AllmotorsProviderAdapter,
    AutohubProviderAdapter,
    AutoshinaProviderAdapter,
    AvtoinstallProviderAdapter,
    BanzaimotorsProviderAdapter,
    BavariaProviderAdapter,
    DetalKgProviderAdapter,
    KiaProviderAdapter,
    LexusProviderAdapter,
    OkayamaomskProviderAdapter,
    ShinabarProviderAdapter,
    ShredderProviderAdapter,
    ToyotaProviderAdapter,
    ToyotaTradeinProviderAdapter,
)
from app.services.sync_service import SyncService


class FakeSessionFactory:
    def __call__(self) -> "FakeSessionFactory":
        return self

    def __enter__(self) -> "FakeSessionFactory":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None


class FakeCatalogRepository:
    def __init__(self, session: object, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    def get_current_by_provider(
        self,
        *,
        provider: str,
        user_id: int,
        category_ids: tuple[int, ...],
    ) -> dict[str, object]:
        return {}


def settings() -> Settings:
    return Settings(
        CATALOG_DATABASE_URL="postgresql://user:pass@example.test:5432/catalog",
        SYNC_CATALOG_USER_ID=77,
        SYNC_CATALOG_PHONES="+996555000111",
        SYNC_DRY_RUN=1,
        SYNC_ALLOW_CATALOG_WRITES=0,
    )


def cp1251_csv(text: str) -> bytes:
    return text.encode("cp1251")


PARTS_CSV = """Артикул;Наименование;Марка;Модель;Год;Кузов;Двигатель;Верх/Низ;Перед/Зад;Лев/Прав;Цвет;Номер;Комментарий;Цена;Производитель;Фото;Новый/БУ;Статус
P-1;Фара;Toyota;Camry;2012;XV50;2.5;;;;;ABC;Левая;5000;TYC;https://img.test/p1.jpg, https://img.test/p2.jpg;БУ;В наличии
P-2;Фара;Toyota;Camry;2012;XV50;2.5;;;;;ABC;Правая;6000;TYC;https://img.test/p3.jpg;БУ;В наличии
C-1;Крыло;MAN;TGA;2008;cab;;;;;;Коммерческая;7000;MAN;https://img.test/c1.jpg;БУ;В наличии
BAD;;Toyota;Camry;2012;XV50;;;;;;;;;;https://img.test/bad.jpg;БУ;В наличии
"""

WHEELS_CSV = """Артикул;Наименование;Марка;Модель;Тип (диск, шина, колесо);Новое/БУ;Диаметр диска;Тип диска;PCD диска;Производитель диска;Модель диска;Вылет диска;Сезон шины (лето, зима, шипы);Ширина профиля шины;Высота профиля шины;Посадочный диаметр шины;Износ шин;Производитель шины;Дата производства;Комментарий;Цена;Фото;Статус
T-1;Шина;Toyota;Camry;шина;Новое;;;;;;;лето;205;55;16;10%;Michelin;2023;Комплект;4500;https://img.test/t1.jpg;В наличии
W-1;Диск;Toyota;Camry;диск;БУ;17;литой;5x114.3;Rays;TE37;45;лето;205;55;17;0%;Michelin;2023;Диск с шиной;5500;https://img.test/w1.jpg;В наличии
BAD;Шина;Toyota;Camry;шина;Новое;;;;;;;лето;;55;16;10%;Michelin;2023;Нет ширины;4500;https://img.test/bad.jpg;В наличии
"""

OKAYAMA_CSV = """Артикул;Наименование;Марка;Модель;Кузов;Двигатель;Номер;Комментарий;Цена;Фото
OK-1;Бампер;Honda;Fit;GE6;1.3;123;Передний;8000;https://img.test/ok1.jpg
BAD;;Honda;Fit;;;;;8000;https://img.test/bad.jpg
"""

SHINABAR_CSV = """Артикул;Тип (диск, шина, колесо);Новое/БУ;Сезон шины (лето, зима, шипы);Ширина профиля шины;Высота профиля шины;Посадочный диаметр шины;Износ шин;Производитель шины;Дата производства;Количество в комплекте;Комментарий;Цена;Фото;Статус
SH-1;шина;Новое;зима;215;60;16;5%;Nokian;2022;4;Хорошее состояние;6000;https://img.test/sh1.jpg;В наличии
SH-1;шина;Новое;зима;215;60;16;5%;Nokian;2022;4;Дубль;6000;https://img.test/sh1b.jpg;В наличии
BAD;шина;Новое;зима;;60;16;5%;Nokian;2022;4;Нет ширины;6000;https://img.test/bad.jpg;В наличии
"""

AVTOINSTALL_CSV = """_ID_;_MAIN_CATEGORY_;_NAME_;_PRICE_;_SPECIAL_;_STOCK_STATUS_;_STATUS_;_ATTRIBUTES_;_IMAGE_;_IMAGES_;_DESCRIPTION_
AV-1;Аудио;Магнитола;12000;0,0,9000,2000-01-01,2099-01-01;В наличии;1;Группа|Бренд|Pioneer;https://img.test/main image.jpg;https://img.test/2.jpg,https://img.test/3.jpg;<p>Описание&nbsp;товара</p>
AV-2;Аудио;Нет в наличии;12000;;Нет;1;;https://img.test/main.jpg;;<p>Нет</p>
"""

ALLMOTORS_LIST_HTML = '<a href="https://allmotors.kg/products/tire-1">Шина</a>'
ALLMOTORS_PRODUCT_HTML = """
<div class="detail-block">
  <div id="owl-single-product"><a href="https://allmotors.kg/uploads/tire.jpg"></a></div>
  <h1 class="name">Toyota Camry, Шина 205/55 R16 летняя</h1>
  <span class="price">4 500 сом</span>
  <div id="description"><p class="text">Описание Allmotors</p></div>
</div>
"""

AUTOSHINA_LIST_HTML = '<a href="/products/101">Tire product</a>'
AUTOSHINA_PRODUCT_HTML = """
<div class="product_show">
  <div class="product_info">
    <div><img src="/uploads/101.jpg"></div>
    <div><div class="block_info">
      <h2>Michelin</h2><h2>Primacy</h2>
      <div class="param">
        <p>Ширина: 205.00</p>
        <p>Высота: 55</p>
        <p>Диаметр диска: 16</p>
        <p>Сезонность: лето</p>
        <p>Цена: 4,500.00 сом</p>
      </div>
    </div></div>
  </div>
  <div class="product_description"><div class="description">Описание Autoshina</div></div>
</div>
"""

DETAL_PARTS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<yml_catalog><shop><offers>
  <offer id="D-1"><name>!Фильтр</name><description>Описание\\ детали</description><vendorCode>VC</vendorCode><price>1000</price><vendor>Detal</vendor><count>3</count><picture>https://img.test/d1.jpg</picture></offer>
  <offer id="D-0"><name>Пусто</name><description>Нет</description><price>1000</price><count>0</count><picture>https://img.test/d0.jpg</picture></offer>
</offers></shop></yml_catalog>
"""

AUTOCRM_XML = """<?xml version="1.0" encoding="UTF-8"?>
<root><cars>
  <car>
    <vin>VIN001</vin><mark_id>Toyota</mark_id><folder_id>Camry</folder_id>
    <year>2024</year><modification_id>2.5</modification_id><body_type>седан</body_type>
    <engine_type>Бензин</engine_type><gearbox>автоматическая</gearbox><drive>Передний</drive>
    <engine_volume>2500</engine_volume><wheel>левый</wheel><color>Белый</color>
    <availability>в наличии</availability><state>new</state><price>25000</price>
    <description>Описание авто</description><extras>ABS,ESP</extras>
    <complectation_name>Comfort</complectation_name>
    <images><image>https://img.test/car1.jpg</image><image>https://img.test/car2.jpg</image></images>
  </car>
  <car>
    <vin>VIN002</vin><mark_id>Toyota</mark_id><folder_id>Camry</folder_id>
    <year>2024</year><modification_id>2.5</modification_id><body_type>седан</body_type>
    <engine_type>Бензин</engine_type><gearbox>автоматическая</gearbox><drive>Передний</drive>
    <engine_volume>2500</engine_volume><wheel>левый</wheel><color>Белый</color>
    <availability>на заказ</availability><price>26000</price>
    <description>Дубль комплектации</description><complectation_name>Comfort</complectation_name>
    <images><image>https://img.test/car3.jpg</image></images>
  </car>
</cars></root>
"""


@pytest.mark.parametrize(
    ("adapter_factory", "expected_source", "expected_count"),
    [
        (
            lambda s: AutohubProviderAdapter(s, fetch_bytes=lambda _url: cp1251_csv(PARTS_CSV)),
            "autohub",
            2,
        ),
        (
            lambda s: ShredderProviderAdapter(s, fetch_bytes=lambda _url: cp1251_csv(PARTS_CSV)),
            "shredder",
            2,
        ),
        (
            lambda s: OkayamaomskProviderAdapter(
                s, fetch_bytes=lambda _url: cp1251_csv(OKAYAMA_CSV)
            ),
            "okayamaomsk",
            1,
        ),
        (
            lambda s: ShinabarProviderAdapter(s, fetch_bytes=lambda _url: cp1251_csv(SHINABAR_CSV)),
            "shinabar",
            1,
        ),
        (
            lambda s: AvtoinstallProviderAdapter(
                s, fetch_bytes=lambda _url: cp1251_csv(AVTOINSTALL_CSV)
            ),
            "avtoinstall",
            1,
        ),
    ],
)
def test_csv_provider_parser_mapper_and_required_skips(
    adapter_factory, expected_source, expected_count
):
    cfg = settings()
    adapter = adapter_factory(cfg)
    ads = tuple(adapter.fetch_ads())
    assert len(ads) == expected_count
    assert all(ad.source == expected_source for ad in ads)
    assert adapter.last_stats.read_count >= expected_count
    assert adapter.last_stats.skipped_count >= 1
    payload = ListingMapper(cfg).to_catalog_payload(ads[0])
    assert payload.external_id == ads[0].external_id
    assert payload.user_id == 77
    assert payload.images


@pytest.mark.parametrize(
    ("adapter_factory", "provider"),
    [
        (
            lambda s: BanzaimotorsProviderAdapter(
                s,
                fetch_bytes=lambda url: cp1251_csv(WHEELS_CSV if "wheels" in url else PARTS_CSV),
            ),
            "banzaimotors",
        ),
        (
            lambda s: BavariaProviderAdapter(
                s,
                fetch_bytes=lambda url: cp1251_csv(
                    WHEELS_CSV if "disk-wheels" in url else PARTS_CSV
                ),
            ),
            "bavaria",
        ),
    ],
)
def test_multi_feed_providers_include_parts_tires_and_wheels(adapter_factory, provider):
    cfg = settings()
    ads = tuple(adapter_factory(cfg).fetch_ads())
    assert {ad.type_id for ad in ads} >= {30, 31, 32}
    assert all(ad.source == provider for ad in ads)
    assert any(ad.tire_width for ad in ads)
    assert any(ad.wheel_size for ad in ads)


def test_allmotors_html_provider_parses_product_and_tire_dimensions():
    cfg = settings()

    def fetch_text(url: str) -> str:
        return ALLMOTORS_PRODUCT_HTML if "/products/" in url else ALLMOTORS_LIST_HTML

    adapter = AllmotorsProviderAdapter(cfg, fetch_text=fetch_text)
    ads = tuple(adapter.fetch_ads(limit=1))
    assert len(ads) == 1
    ad = ads[0]
    assert ad.external_id == "tire-1"
    assert ad.type_id == 31
    assert ad.tire_width == "205"
    assert ad.images[0].startswith("https://www.mashina.kg/sync/files")


def test_autoshina_html_provider_requires_image_brand_model_and_dimensions():
    cfg = settings()

    def fetch_text(url: str) -> str:
        return AUTOSHINA_PRODUCT_HTML if "/products/101" in url else AUTOSHINA_LIST_HTML

    adapter = AutoshinaProviderAdapter(cfg, fetch_text=fetch_text)
    ads = tuple(adapter.fetch_ads(limit=1))
    assert len(ads) == 1
    ad = ads[0]
    assert ad.external_id == "101"
    assert ad.type_id == 31
    assert ad.condition == 2
    assert ad.tire_type == 1


def test_detalkg_xml_parts_provider_skips_count_zero_and_adds_markup():
    cfg = settings()
    adapter = DetalKgProviderAdapter(
        cfg,
        fetch_bytes=lambda _url: DETAL_PARTS_XML.encode(),
        fetch_text=lambda _url: "",
    )
    ads = tuple(adapter.fetch_ads(limit=1))
    assert len(ads) == 1
    assert ads[0].external_id == "D-1"
    assert str(ads[0].price) == "1200"
    assert adapter.last_stats.skipped_count == 1


@pytest.mark.parametrize(
    ("adapter_factory", "provider"),
    [
        (
            lambda s: ToyotaProviderAdapter(s, fetch_bytes=lambda _url: AUTOCRM_XML.encode()),
            "toyota",
        ),
        (
            lambda s: ToyotaTradeinProviderAdapter(
                s, fetch_bytes=lambda _url: AUTOCRM_XML.encode()
            ),
            "toyota_tradein",
        ),
        (lambda s: LexusProviderAdapter(s, fetch_bytes=lambda _url: AUTOCRM_XML.encode()), "lexus"),
        (lambda s: KiaProviderAdapter(s, fetch_bytes=lambda _url: AUTOCRM_XML.encode()), "kia"),
    ],
)
def test_autocrm_xml_providers_parse_images_vin_and_dedupe_kia(adapter_factory, provider):
    cfg = settings()
    adapter = adapter_factory(cfg)
    ads = tuple(adapter.fetch_ads())
    assert ads
    assert all(ad.type_id == 1 for ad in ads)
    assert all(ad.vincode == ad.external_id for ad in ads)
    assert all(str(ad.images[0]).startswith("0|") for ad in ads)
    if provider == "kia":
        assert len(ads) == 1


@pytest.mark.parametrize(
    ("provider", "adapter_factory"),
    [
        (
            "autohub",
            lambda s: AutohubProviderAdapter(s, fetch_bytes=lambda _url: cp1251_csv(PARTS_CSV)),
        ),
        (
            "shredder",
            lambda s: ShredderProviderAdapter(s, fetch_bytes=lambda _url: cp1251_csv(PARTS_CSV)),
        ),
        (
            "okayamaomsk",
            lambda s: OkayamaomskProviderAdapter(
                s, fetch_bytes=lambda _url: cp1251_csv(OKAYAMA_CSV)
            ),
        ),
        (
            "banzaimotors",
            lambda s: BanzaimotorsProviderAdapter(
                s,
                fetch_bytes=lambda url: cp1251_csv(WHEELS_CSV if "wheels" in url else PARTS_CSV),
            ),
        ),
        (
            "bavaria",
            lambda s: BavariaProviderAdapter(
                s,
                fetch_bytes=lambda url: cp1251_csv(
                    WHEELS_CSV if "disk-wheels" in url else PARTS_CSV
                ),
            ),
        ),
        (
            "shinabar",
            lambda s: ShinabarProviderAdapter(s, fetch_bytes=lambda _url: cp1251_csv(SHINABAR_CSV)),
        ),
        (
            "avtoinstall",
            lambda s: AvtoinstallProviderAdapter(
                s, fetch_bytes=lambda _url: cp1251_csv(AVTOINSTALL_CSV)
            ),
        ),
        (
            "allmotors",
            lambda s: AllmotorsProviderAdapter(
                s,
                fetch_text=lambda url: (
                    ALLMOTORS_PRODUCT_HTML if "/products/" in url else ALLMOTORS_LIST_HTML
                ),
            ),
        ),
        (
            "autoshina",
            lambda s: AutoshinaProviderAdapter(
                s,
                fetch_text=lambda url: (
                    AUTOSHINA_PRODUCT_HTML if "/products/101" in url else AUTOSHINA_LIST_HTML
                ),
            ),
        ),
        (
            "detalkg",
            lambda s: DetalKgProviderAdapter(
                s,
                fetch_bytes=lambda _url: DETAL_PARTS_XML.encode(),
                fetch_text=lambda _url: "",
            ),
        ),
        (
            "toyota",
            lambda s: ToyotaProviderAdapter(s, fetch_bytes=lambda _url: AUTOCRM_XML.encode()),
        ),
        (
            "toyota_tradein",
            lambda s: ToyotaTradeinProviderAdapter(
                s, fetch_bytes=lambda _url: AUTOCRM_XML.encode()
            ),
        ),
        ("lexus", lambda s: LexusProviderAdapter(s, fetch_bytes=lambda _url: AUTOCRM_XML.encode())),
        ("kia", lambda s: KiaProviderAdapter(s, fetch_bytes=lambda _url: AUTOCRM_XML.encode())),
    ],
)
def test_remaining_provider_dry_run_sync_with_mocked_repository(provider, adapter_factory):
    cfg = settings()
    service = SyncService(
        cfg,
        session_factory=FakeSessionFactory(),  # type: ignore[arg-type]
        adapters={provider: adapter_factory(cfg)},
        repository_factory=FakeCatalogRepository,  # type: ignore[arg-type]
    )

    result = service.sync_provider(provider, dry_run=True, limit=1)

    assert result.errors == []
    assert result.valid_count == 1
    assert result.inserted_count == 1
    assert result.diff_samples[0]["action"] == "insert"
