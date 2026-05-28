from decimal import Decimal

import pytest
from app.config.catalog_mapping import map_currency, map_type_id
from app.config.settings import Settings
from app.dto import LegacyAd
from app.mappers.attribute_mapper import map_legacy_attributes
from app.mappers.image_mapper import parse_legacy_image
from app.mappers.listing_mapper import ListingMapper


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


def test_mileage_maps_to_catalog_json_shape() -> None:
    ad = LegacyAd(source="toyota", external_id="VIN-1", type_id=1, mileage="12 345 км")

    attributes = {attribute.slug: attribute.value for attribute in map_legacy_attributes(ad)}

    assert attributes["mileage"] == {"value": "12345", "suffix": "км"}


def test_listing_mapper_preserves_tire_specs_in_description() -> None:
    settings = Settings(SYNC_CATALOG_USER_ID=77)
    ad = LegacyAd(
        source="autoshina",
        external_id="T-1",
        type_id=31,
        name="Michelin Primacy",
        description="Летняя шина",
        currency=1,
        tire_width="205",
        tire_height="55",
        tire_size="16",
        tire_type=1,
    )

    payload = ListingMapper(settings).to_catalog_payload(ad)

    assert "Характеристики" in payload.description
    assert "Ширина шины: 205" in payload.description
    assert "Диаметр шины: 16" in payload.description


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
