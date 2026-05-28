from app.config.catalog_mapping import (
    map_currency,
    map_type_id,
    require_catalog_user_id,
)
from app.config.settings import Settings
from app.dto import CatalogAttributePayload, CatalogListingPayload, LegacyAd
from app.mappers.attribute_mapper import map_legacy_attributes
from app.mappers.image_mapper import map_images

TIRE_WHEEL_SPEC_LABELS: tuple[tuple[str, str], ...] = (
    ("tire_width", "Ширина шины"),
    ("tire_height", "Высота шины"),
    ("tire_size", "Диаметр шины"),
    ("tire_type", "Сезонность"),
    ("wheel_type", "Тип диска"),
    ("wheel_size", "Диаметр диска"),
    ("wheel_pcd", "PCD диска"),
)


class ListingMapper:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def to_catalog_payload(self, ad: LegacyAd) -> CatalogListingPayload:
        user_id = require_catalog_user_id(
            ad.source,
            self.settings.catalog_user_id_for_provider(ad.source),
        )
        title = (ad.name or "").strip() or f"{ad.source} {ad.external_id}"
        description = (ad.description or "").strip() or title
        description = self._append_tire_wheel_specs(description, ad)
        phone_values = ad.phones or tuple(self.settings.phones_for_provider(ad.source))
        attribute_payloads = list(map_legacy_attributes(ad))
        if phone_values:
            phone_value: str | list[str] = (
                phone_values[0] if len(phone_values) == 1 else list(phone_values)
            )
            attribute_payloads.append(CatalogAttributePayload(slug="phone", value=phone_value))

        return CatalogListingPayload(
            source=ad.source,
            external_id=ad.external_id,
            user_id=user_id,
            category_id=map_type_id(ad.type_id),
            title=title,
            description=description,
            price=ad.price,
            currency=map_currency(ad.currency),
            status=ad.raw.get("status") or self.settings.sync_catalog_default_status,
            attributes=tuple(attribute_payloads),
            images=map_images(
                ad.images,
                user_id=user_id,
                status=self.settings.sync_catalog_image_status,
            ),
            raw_legacy_ad=ad.raw,
        )

    def _append_tire_wheel_specs(self, description: str, ad: LegacyAd) -> str:
        lines: list[str] = []
        description_lower = description.lower()
        for field_name, label in TIRE_WHEEL_SPEC_LABELS:
            value = getattr(ad, field_name)
            if value in (None, ""):
                continue
            if label.lower() in description_lower:
                continue
            lines.append(f"{label}: {value}")

        if not lines:
            return description
        return f"{description}\n\nХарактеристики:\n" + "\n".join(lines)
