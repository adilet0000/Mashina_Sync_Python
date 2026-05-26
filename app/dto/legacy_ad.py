from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any


def _normalize_required_string(value: object, field_name: str) -> str:
    normalized = str(value).strip() if value is not None else ""
    if not normalized:
        raise ValueError(f"{field_name} is required")
    return normalized


def _normalize_decimal(value: object) -> Decimal | None:
    if value in (None, ""):
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value).replace(" ", "").replace(",", "."))
    except InvalidOperation as exc:
        raise ValueError(f"invalid decimal value: {value!r}") from exc


def _normalize_int(value: object, field_name: str) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer") from exc


@dataclass(frozen=True)
class LegacyAd:
    source: str
    external_id: str
    type_id: int
    name: str | None = None
    description: str | None = None
    price: Decimal | None = None
    old_price: Decimal | None = None
    currency: int | str | None = None
    region: Any | None = None
    town: Any | None = None
    make: Any | None = None
    model: Any | None = None
    year: Any | None = None
    body: Any | None = None
    generation: Any | None = None
    fuel: Any | None = None
    transmission: Any | None = None
    gear_box: Any | None = None
    modification: Any | None = None
    complectation: Any | None = None
    steering_wheel: Any | None = None
    color: Any | None = None
    mileage: Any | None = None
    customs: Any | None = None
    vincode: Any | None = None
    condition: Any | None = None
    phone: str | tuple[str, ...] | list[str] | None = None
    images: tuple[Any, ...] = ()
    tire_width: Any | None = None
    tire_height: Any | None = None
    tire_size: Any | None = None
    tire_type: Any | None = None
    wheel_type: Any | None = None
    wheel_size: Any | None = None
    wheel_pcd: Any | None = None
    raw: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(self, "source", _normalize_required_string(self.source, "source"))
        object.__setattr__(
            self,
            "external_id",
            _normalize_required_string(self.external_id, "external_id"),
        )
        object.__setattr__(self, "type_id", _normalize_int(self.type_id, "type_id"))
        object.__setattr__(self, "price", _normalize_decimal(self.price))
        object.__setattr__(self, "old_price", _normalize_decimal(self.old_price))
        object.__setattr__(self, "images", tuple(self.images or ()))

    @property
    def phones(self) -> tuple[str, ...]:
        if self.phone is None:
            return ()
        if isinstance(self.phone, str):
            return tuple(part.strip() for part in self.phone.split(",") if part.strip())
        return tuple(str(part).strip() for part in self.phone if str(part).strip())
