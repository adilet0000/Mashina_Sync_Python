import re
from decimal import Decimal
from typing import Any

from app.config.catalog_mapping import (
    LEGACY_FIELD_TO_ATTRIBUTE_SLUG,
    REFERENCE_ATTRIBUTE_SLUGS,
)
from app.dto import CatalogAttributePayload, LegacyAd


def _is_empty(value: Any) -> bool:
    return value is None or value == "" or value == ()


def _to_boolish(value: Any) -> bool | None:
    if _is_empty(value):
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "да", "растаможен", "растаможена"}:
        return True
    if normalized in {"0", "false", "no", "нет"}:
        return False
    return None


def _is_int_like(value: Any) -> bool:
    if isinstance(value, int):
        return True
    if isinstance(value, str):
        return value.strip().isdigit()
    return False


def _attribute_payload(slug: str, value: Any) -> CatalogAttributePayload | None:
    if _is_empty(value):
        return None

    if slug == "is_customs_cleared":
        boolean_value = _to_boolish(value)
        return CatalogAttributePayload(slug=slug, value=boolean_value)

    if slug == "mileage":
        return CatalogAttributePayload(slug=slug, value=_mileage_json(value))

    if slug in REFERENCE_ATTRIBUTE_SLUGS:
        if _is_int_like(value):
            return CatalogAttributePayload(slug=slug, value=value, option_old_mysql_id=value)
        return CatalogAttributePayload(slug=slug, value=value, option_value=str(value))

    if slug in {"old_price", "year"} and not isinstance(value, Decimal):
        return CatalogAttributePayload(slug=slug, value=value)

    return CatalogAttributePayload(slug=slug, value=value)


def _mileage_json(value: Any) -> dict[str, str]:
    text = str(value).strip()
    match = re.search(r"\d[\d\s,.]*", text)
    mileage_value = match.group(0).replace(" ", "").replace(",", ".").strip(".") if match else text
    return {"value": mileage_value, "suffix": "км"}


def map_legacy_attributes(ad: LegacyAd) -> tuple[CatalogAttributePayload, ...]:
    payloads: list[CatalogAttributePayload] = [
        CatalogAttributePayload(slug="external_id", value=ad.external_id),
    ]

    for legacy_field, attribute_slug in LEGACY_FIELD_TO_ATTRIBUTE_SLUG.items():
        if legacy_field in {"external_id", "phone"}:
            continue
        value = getattr(ad, legacy_field)
        payload = _attribute_payload(attribute_slug, value)
        if payload is not None:
            payloads.append(payload)

    return tuple(payloads)
