from decimal import Decimal
from pathlib import Path

from app.config.settings import Settings
from app.mappers import ListingMapper
from app.providers.autoland import AutolandProviderAdapter


def _settings() -> Settings:
    return Settings(
        SYNC_CATALOG_USER_ID=77,
        SYNC_CATALOG_PHONES_AUTOLAND="+996555000111,+996555000222",
    )


def _fixture_bytes() -> bytes:
    path = Path(__file__).parent / "fixtures" / "autoland.csv"
    return path.read_text(encoding="utf-8").encode("cp1251")


def test_autoland_csv_parser_supports_cp1251_fixture() -> None:
    adapter = AutolandProviderAdapter(_settings(), fetch_bytes=lambda _url: _fixture_bytes())
    rows = adapter.parse_csv(_fixture_bytes())
    assert adapter.last_stats.read_count == 4
    assert adapter.last_stats.skipped_count == 1
    assert len(rows) == 3
    assert rows[0].article == "A-1"
    assert rows[0].photos == ("https://img.test/1.jpg", "https://img.test/2.jpg")
    assert rows[0].price == Decimal("1200")


def test_autoland_grouping_joins_articles_by_name_make_model() -> None:
    adapter = AutolandProviderAdapter(_settings(), fetch_bytes=lambda _url: _fixture_bytes())
    ads = adapter.fetch_ads()
    grouped = [ad for ad in ads if ad.external_id == "A-1,A-2"][0]
    assert grouped.name == "Фара"
    assert grouped.make == "Toyota"
    assert grouped.model == "Camry"
    assert "1) Левая фара" in grouped.description
    assert "2) Правая фара" in grouped.description
    assert len(grouped.images) == 3


def test_autoland_condition_rule() -> None:
    adapter = AutolandProviderAdapter(_settings(), fetch_bytes=lambda _url: _fixture_bytes())
    ads = adapter.fetch_ads()
    new_dordoi = [ad for ad in ads if ad.external_id == "B-1"][0]
    grouped_used = [ad for ad in ads if ad.external_id == "A-1,A-2"][0]
    assert new_dordoi.condition == 2
    assert grouped_used.condition == 1


def test_autoland_listing_mapper_applies_category_currency_phone_and_images() -> None:
    adapter = AutolandProviderAdapter(_settings(), fetch_bytes=lambda _url: _fixture_bytes())
    ad = [item for item in adapter.fetch_ads() if item.external_id == "B-1"][0]
    payload = ListingMapper(_settings()).to_catalog_payload(ad)
    assert payload.user_id == 77
    assert payload.category_id == 35
    assert payload.currency == "KGS"
    assert payload.price == Decimal("2500")
    assert payload.attribute_map["phone"].value == ["+996555000111", "+996555000222"]
    assert payload.attribute_map["make"].option_value == "Honda"
    assert payload.attribute_map["model"].option_value == "Fit"
    assert payload.images[0].external_url == "https://img.test/4.jpg"
