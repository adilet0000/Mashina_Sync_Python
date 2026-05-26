import csv
import html
import re
from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from io import StringIO
from typing import Any
from urllib.parse import quote, urljoin, urlparse


@dataclass
class ProviderParseStats:
    read_count: int = 0
    skipped_count: int = 0
    warnings: list[str] = field(default_factory=list)

    def skip(self, message: str) -> None:
        self.skipped_count += 1
        self.warnings.append(message)


def clean(value: Any) -> str:
    return str(value or "").strip()


def lower_clean(value: Any) -> str:
    return clean(value).lower()


def decode_feed_content(content: bytes | str) -> str:
    if isinstance(content, str):
        return content
    for encoding in ("cp1251", "windows-1251", "utf-8-sig", "utf-8"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("cp1251", errors="replace")


def parse_csv_rows(content: bytes | str, *, delimiter: str = ";") -> tuple[dict[str, str], ...]:
    text = decode_feed_content(content)
    reader = csv.DictReader(StringIO(text), delimiter=delimiter)
    return tuple({clean(key): clean(value) for key, value in row.items()} for row in reader)


def parse_decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    cleaned = clean(value).replace("\xa0", "").replace(" ", "").replace("сом", "").replace(",", ".")
    cleaned = re.sub(r"[^0-9.\-]", "", cleaned)
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def parse_int_text(value: Any) -> int | None:
    cleaned = re.sub(r"[^0-9\-]", "", clean(value))
    if not cleaned:
        return None
    try:
        return int(cleaned)
    except ValueError:
        return None


def split_photos(
    value: Any, *, separator: str = ", ", max_count: int | None = None
) -> tuple[str, ...]:
    if not value:
        return ()
    if isinstance(value, (list, tuple)):
        raw_items = value
    else:
        text = clean(value)
        raw_items = text.split(separator) if separator in text else re.split(r"\s*,\s*", text)
    photos = tuple(dict.fromkeys(clean(item) for item in raw_items if clean(item)))
    if max_count is not None:
        return photos[:max_count]
    return photos


def ordered_images(urls: Iterable[str]) -> tuple[str, ...]:
    return tuple(f"{index}|{url}" for index, url in enumerate(urls) if clean(url))


def strip_html(value: Any) -> str:
    text = re.sub(r"<br\s*/?>", "\n", clean(value), flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    return re.sub(r"(\s*\n\s*)+", "\n", text).strip()


def absolute_url(base_url: str, url: str | None) -> str | None:
    if not url:
        return None
    return urljoin(base_url, url)


def filename_encoded_url(url: str) -> str:
    position = url.rfind("/")
    if position < 0:
        return quote(url)
    return url[: position + 1] + quote(url[position + 1 :]).replace("+", "%20")


def mashina_proxy_image_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path or ""
    extension = path.rsplit(".", 1)[1] if "." in path else ""
    base = url[: -(len(extension) + 1)] if extension else url
    return f"https://www.mashina.kg/sync/files?ext={extension}&url={base}"


def group_by(rows: Iterable[dict[str, Any]], key_func: Callable[[dict[str, Any]], tuple[Any, ...]]):
    grouped: dict[tuple[Any, ...], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        grouped[key_func(row)][clean(row.get("Артикул"))] = row
    return tuple(tuple(entries.values()) for entries in grouped.values())


def condition_id_from_text(value: Any, *, default: int = 1) -> int:
    normalized = lower_clean(value)
    if normalized in {"новое", "новый", "новая", "new"}:
        return 2
    if normalized in {"бу", "б/у", "б.у.", "used"}:
        return 1
    return default


def tire_type_from_text(value: Any, *, default: int = 1) -> int:
    normalized = lower_clean(value)
    if "шип" in normalized:
        return 3
    if "зим" in normalized:
        return 2
    if "в/с" in normalized or "всес" in normalized:
        return 3
    if "лет" in normalized:
        return 1
    return default


def parse_tire_dimensions(text: str) -> tuple[str | None, str | None, str | None]:
    match = re.search(r"(\d{3}(?:\.5)?)\s*/\s*(\d{2})\s*/?\s*R?\s*(\d{2})", text, re.IGNORECASE)
    if not match:
        return None, None, None
    return match.group(1), match.group(2), match.group(3)


def active_special_price(
    regular_price: Decimal | None,
    special_value: str | None,
    *,
    now: datetime | None = None,
) -> tuple[Decimal | None, Decimal | None]:
    if regular_price is None or not special_value:
        return regular_price, None
    parts = [clean(part) for part in special_value.split(",")]
    if len(parts) < 5:
        return regular_price, None
    special_price = parse_decimal(parts[2])
    if special_price is None or special_price >= regular_price:
        return regular_price, None
    now = now or datetime.now()
    try:
        start = datetime.fromisoformat(parts[3])
        end = datetime.fromisoformat(parts[4])
    except ValueError:
        return regular_price, None
    if start <= now <= end:
        return special_price, regular_price
    return regular_price, None
