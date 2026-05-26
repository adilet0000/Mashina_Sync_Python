import re
from decimal import Decimal, InvalidOperation

_SPACE_RE = re.compile(r"\s+")


def normalize_text(value: object) -> str | None:
    if value is None:
        return None
    normalized = _SPACE_RE.sub(" ", str(value)).strip()
    return normalized or None


def normalize_external_id(value: object) -> str:
    normalized = normalize_text(value)
    if not normalized:
        raise ValueError("provider external_id is required")
    return normalized


def normalize_price(value: object) -> Decimal | None:
    if value in (None, ""):
        return None
    cleaned = str(value).replace(" ", "").replace(",", ".")
    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(f"invalid price value: {value!r}") from exc
