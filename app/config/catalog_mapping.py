from dataclasses import dataclass

TYPE_ID_TO_CATEGORY_ID: dict[int, int] = {
    1: 1,
    30: 35,
    31: 24,
    32: 37,
    33: 33,
    36: 26,
}

TYPE_ID_TO_CATEGORY_SLUG: dict[int, str] = {
    1: "car",
    30: "parts_supplies",
    31: "tires",
    32: "wheels",
    33: "accessories",
    36: "commercial_parts",
}

CURRENCY_ID_TO_CODE: dict[int, str] = {
    1: "KGS",
    2: "USD",
}

LEGACY_FIELD_TO_ATTRIBUTE_SLUG: dict[str, str] = {
    "external_id": "external_id",
    "region": "region",
    "town": "city",
    "make": "make",
    "model": "model",
    "year": "year",
    "generation": "generation",
    "body": "body_type",
    "fuel": "fuel_type",
    "transmission": "drive_type",
    "gear_box": "gearbox",
    "modification": "modification",
    "complectation": "complectation",
    "steering_wheel": "steering_wheel",
    "color": "color",
    "mileage": "mileage",
    "customs": "is_customs_cleared",
    "vincode": "vincode",
    "old_price": "old_price",
    "phone": "phone",
    "condition": "condition",
    "tire_width": "tire_width",
    "tire_height": "tire_height",
    "tire_size": "tire_size",
    "tire_type": "tire_type",
    "wheel_type": "wheel_type",
    "wheel_size": "wheel_size",
    "wheel_pcd": "wheel_pcd",
}

REFERENCE_ATTRIBUTE_SLUGS = {
    "region",
    "city",
    "make",
    "model",
    "generation",
    "body_type",
    "fuel_type",
    "drive_type",
    "gearbox",
    "modification",
    "steering_wheel",
    "color",
    "condition",
    "tire_width",
    "tire_height",
    "tire_size",
    "tire_type",
    "wheel_type",
    "wheel_size",
    "wheel_pcd",
}


@dataclass(frozen=True)
class CatalogIdentity:
    source: str
    user_id: int
    category_id: int
    external_id: str


def build_source(provider: str) -> str:
    return provider.lower().replace("-", "_")


def map_type_id(type_id: int) -> int:
    try:
        return TYPE_ID_TO_CATEGORY_ID[int(type_id)]
    except KeyError as exc:
        raise ValueError(f"unsupported legacy type_id={type_id!r}") from exc


def map_currency(currency: int | str | None) -> str | None:
    if currency in (None, ""):
        return None
    if isinstance(currency, str) and not currency.isdigit():
        normalized = currency.strip().upper()
        return normalized or None
    try:
        return CURRENCY_ID_TO_CODE[int(currency)]
    except (KeyError, ValueError) as exc:
        raise ValueError(f"unsupported legacy currency={currency!r}") from exc


def require_catalog_user_id(provider: str, user_id: int | None) -> int:
    if user_id is None:
        raise ValueError(
            f"catalog user_id is not configured for provider {provider!r}; "
            "set SYNC_CATALOG_USER_ID or provider-specific SYNC_CATALOG_USER_ID_<PROVIDER>"
        )
    return user_id
