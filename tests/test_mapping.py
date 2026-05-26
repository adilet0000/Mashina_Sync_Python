from decimal import Decimal

import pytest
from app.config.catalog_mapping import map_currency, map_type_id
from app.dto import LegacyAd
from app.mappers.image_mapper import parse_legacy_image


def test_legacy_ad_validates_required_fields() -> None:
    with pytest.raises(ValueError, match="external_id is required"):
        LegacyAd(source="autohub", external_id="", type_id=30)


def test_type_id_mapping() -> None:
    assert map_type_id(1) == 1
    assert map_type_id(30) == 35
    assert map_type_id(31) == 24
    assert map_type_id(32) == 37
    assert map_type_id(33) == 33
    assert map_type_id(36) == 26


def test_currency_mapping() -> None:
    assert map_currency(1) == "KGS"
    assert map_currency("2") == "USD"
    assert map_currency("usd") == "USD"
    assert map_currency(None) is None


def test_legacy_ad_normalizes_decimal_price() -> None:
    ad = LegacyAd(source="autohub", external_id="A-1", type_id=30, price="12 500,50")
    assert ad.price == Decimal("12500.50")


def test_parse_plain_image_url() -> None:
    image = parse_legacy_image(
        "https://example.test/image.jpg",
        fallback_priority=3,
        user_id=7,
        status=1,
    )
    assert image.external_url == "https://example.test/image.jpg"
    assert image.priority == 3
    assert image.status == 1
    assert image.user_id == 7


def test_parse_indexed_image_url() -> None:
    image = parse_legacy_image(
        "5|https://example.test/image.jpg",
        fallback_priority=3,
        user_id=7,
        status=1,
    )
    assert image.external_url == "https://example.test/image.jpg"
    assert image.priority == 5
