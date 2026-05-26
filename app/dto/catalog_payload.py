from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class CatalogImagePayload:
    external_url: str
    priority: int
    hash: str
    status: int
    is_blurred: bool
    user_id: int


@dataclass(frozen=True)
class CatalogAttributePayload:
    slug: str
    value: Any | None = None
    option_old_mysql_id: int | str | None = None
    option_value: str | None = None
    parent_option_id: int | None = None


@dataclass(frozen=True)
class CatalogListingPayload:
    source: str
    external_id: str
    user_id: int
    category_id: int
    title: str
    description: str
    price: Decimal | None
    currency: str | None
    status: str
    attributes: tuple[CatalogAttributePayload, ...] = ()
    images: tuple[CatalogImagePayload, ...] = ()
    raw_legacy_ad: dict[str, Any] = field(default_factory=dict)

    @property
    def attribute_map(self) -> dict[str, CatalogAttributePayload]:
        return {attribute.slug: attribute for attribute in self.attributes}
