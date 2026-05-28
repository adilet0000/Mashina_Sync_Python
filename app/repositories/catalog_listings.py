import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.config import Settings
from app.dto import CatalogAttributePayload, CatalogImagePayload, CatalogListingPayload
from app.repositories.catalog_references import CatalogReferenceResolver
from app.utils.identity import listing_identity_key
from app.utils.slug import stable_slug

logger = logging.getLogger(__name__)


class CatalogWritesDisabledError(RuntimeError):
    pass


def assert_catalog_writes_allowed(settings: Settings) -> None:
    if not settings.sync_allow_catalog_writes:
        raise CatalogWritesDisabledError(
            "catalog writes are disabled; set SYNC_ALLOW_CATALOG_WRITES=1 only after "
            "dry-run and verification are approved"
        )


@dataclass(frozen=True)
class ExistingImage:
    id: int
    external_url: str
    hash: str
    priority: int
    status: int | None
    user_id: int | None = None
    is_blurred: bool | None = None


@dataclass(frozen=True)
class ExistingListing:
    id: int
    external_id: str
    source: str
    user_id: int
    category_id: int
    title: str | None
    description: str | None
    price: Decimal | None
    currency: str | None
    status: str | None
    slug: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    images: tuple[ExistingImage, ...] = ()


@dataclass(frozen=True)
class ListingWriteOutcome:
    listing_id: int
    changed: bool
    missing_attribute_slugs: tuple[str, ...] = ()


class CatalogListingsRepository:
    def __init__(
        self,
        session: Session,
        settings: Settings,
        *,
        reference_resolver: CatalogReferenceResolver | None = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.reference_resolver = reference_resolver or CatalogReferenceResolver(session)
        self.last_duplicate_external_ids: tuple[str, ...] = ()

    def get_current_by_provider(
        self,
        *,
        provider: str,
        user_id: int,
        category_ids: tuple[int, ...] | list[int] | None = None,
    ) -> dict[str, ExistingListing]:
        statement = self.build_eav_current_query(category_ids)
        params: dict[str, Any] = {"source": provider, "user_id": user_id}
        if category_ids:
            params["category_ids"] = tuple(category_ids)

        rows = (
            self.session.execute(
                statement,
                params,
            )
            .mappings()
            .all()
        )
        current: dict[str, ExistingListing] = {}
        duplicate_keys: set[str] = set()
        for row in rows:
            external_id = str(row["external_id"])
            key = listing_identity_key(int(row["category_id"]), external_id)
            if key in current:
                duplicate_keys.add(key)
                continue
            current[key] = self._listing_from_row(row)

        for key in duplicate_keys:
            current.pop(key, None)
        self.last_duplicate_external_ids = tuple(sorted(duplicate_keys))
        if duplicate_keys:
            logger.warning(
                "duplicate current listing identity values found user_id=%s category_ids=%s "
                "identity_keys=%s; skipped ambiguous rows",
                user_id,
                tuple(category_ids or ()),
                tuple(sorted(duplicate_keys)),
            )

        listing_ids = tuple(listing.id for listing in current.values())
        attributes_by_listing_id = self.get_listing_attributes_bulk(listing_ids)
        images_by_listing_id = self.get_listing_images_bulk(listing_ids)
        for listing in current.values():
            object.__setattr__(
                listing,
                "attributes",
                attributes_by_listing_id.get(listing.id, {}),
            )
            object.__setattr__(
                listing,
                "images",
                tuple(images_by_listing_id.get(listing.id, ())),
            )
        return current

    def get_by_external_id(
        self,
        *,
        provider: str,
        user_id: int,
        category_id: int,
        external_id: str,
    ) -> ExistingListing | None:
        current = self.get_current_by_provider(
            provider=provider,
            user_id=user_id,
            category_ids=(category_id,),
        )
        return current.get(listing_identity_key(category_id, external_id))

    def get_by_id(self, listing_id: int) -> ExistingListing | None:
        row = (
            self.session.execute(
                text(
                    """
                    SELECT
                      id, user_id, category_id, title, description, price, currency, status, slug
                    FROM listings
                    WHERE id = :listing_id
                    LIMIT 1
                    """
                ),
                {"listing_id": listing_id},
            )
            .mappings()
            .first()
        )
        if not row:
            return None

        attributes = self.get_listing_attributes(listing_id)
        external_id = str(attributes.get("external_id") or "")
        listing = ExistingListing(
            id=int(row["id"]),
            external_id=external_id,
            source="",
            user_id=int(row["user_id"]),
            category_id=int(row["category_id"]),
            title=row.get("title"),
            description=row.get("description"),
            price=row.get("price"),
            currency=row.get("currency"),
            status=row.get("status"),
            slug=row.get("slug"),
            attributes=attributes,
            images=tuple(self.get_listing_images(listing_id)),
        )
        return listing

    def build_eav_current_query(self, category_ids: tuple[int, ...] | list[int] | None):
        category_filter = "AND l.category_id IN :category_ids" if category_ids else ""
        statement = text(
            f"""
            SELECT
              l.id,
              ext_attr.value_text AS external_id,
              :source AS source,
              l.user_id,
              l.category_id,
              l.title,
              l.description,
              l.price,
              l.currency,
              l.status,
              l.slug
            FROM listings l
            JOIN listing_attributes ext_attr ON ext_attr.listing_id = l.id
            JOIN attributes ext_def
              ON ext_def.id = ext_attr.attribute_id
             AND ext_def.slug = 'external_id'
            WHERE l.user_id = :user_id
              AND ext_attr.value_text IS NOT NULL
              {category_filter}
            """
        )
        if category_ids:
            statement = statement.bindparams(bindparam("category_ids", expanding=True))
        return statement

    def get_listing_attributes(self, listing_id: int) -> dict[str, Any]:
        return self.get_listing_attributes_bulk((listing_id,)).get(listing_id, {})

    def get_listing_attributes_bulk(
        self, listing_ids: tuple[int, ...]
    ) -> dict[int, dict[str, Any]]:
        if not listing_ids:
            return {}
        rows = (
            self.session.execute(
                text(
                    """
                    SELECT
                      la.listing_id,
                      a.slug,
                      la.attribute_options_id,
                      la.value_text,
                      la.value_number,
                      la.value_boolean,
                      la.value_date,
                      la.value_json
                    FROM listing_attributes la
                    JOIN attributes a ON a.id = la.attribute_id
                    WHERE la.listing_id IN :listing_ids
                    """
                ).bindparams(bindparam("listing_ids", expanding=True)),
                {"listing_ids": listing_ids},
            )
            .mappings()
            .all()
        )
        grouped: dict[int, dict[str, Any]] = {}
        for row in rows:
            listing_id = int(row["listing_id"])
            grouped.setdefault(listing_id, {})[str(row["slug"])] = self._attribute_value_from_row(
                row
            )
        return grouped

    def get_listing_images(self, listing_id: int) -> list[ExistingImage]:
        return self.get_listing_images_bulk((listing_id,)).get(listing_id, [])

    def get_listing_images_bulk(
        self, listing_ids: tuple[int, ...]
    ) -> dict[int, list[ExistingImage]]:
        if not listing_ids:
            return {}
        rows = (
            self.session.execute(
                text(
                    """
                    SELECT id, listing_id, external_url, hash, priority, status, user_id,
                           is_blurred
                    FROM images
                    WHERE listing_id IN :listing_ids
                    ORDER BY listing_id ASC, priority ASC, id ASC
                    """
                ).bindparams(bindparam("listing_ids", expanding=True)),
                {"listing_ids": listing_ids},
            )
            .mappings()
            .all()
        )
        grouped: dict[int, list[ExistingImage]] = {}
        for row in rows:
            listing_id = int(row["listing_id"])
            grouped.setdefault(listing_id, []).append(
                ExistingImage(
                    id=int(row["id"]),
                    external_url=str(row["external_url"]),
                    hash=str(row["hash"]),
                    priority=int(row["priority"] or 0),
                    status=row.get("status"),
                    user_id=int(row["user_id"]) if row.get("user_id") is not None else None,
                    is_blurred=bool(row["is_blurred"])
                    if row.get("is_blurred") is not None
                    else None,
                )
            )
        return grouped

    def insert_listing(self, payload: CatalogListingPayload) -> ListingWriteOutcome:
        assert_catalog_writes_allowed(self.settings)
        row = (
            self.session.execute(
                text(
                    """
                    INSERT INTO listings (
                      user_id, category_id, title, description, price, currency, status, slug,
                      created_at, updated_at
                    )
                    VALUES (
                      :user_id, :category_id, :title, :description, :price, :currency, :status,
                      :slug, NOW(), NOW()
                    )
                    RETURNING id
                    """
                ),
                self._listing_params(payload),
            )
            .mappings()
            .one()
        )
        listing_id = int(row["id"])
        missing_slugs: list[str] = []
        for attribute in payload.attributes:
            if not self.upsert_attribute(listing_id, attribute):
                missing_slugs.append(attribute.slug)
        for image in payload.images:
            self.insert_image(listing_id, image)
        return ListingWriteOutcome(
            listing_id=listing_id,
            changed=True,
            missing_attribute_slugs=tuple(missing_slugs),
        )

    def update_listing(
        self,
        listing_id: int,
        payload: CatalogListingPayload,
        *,
        changed_fields: tuple[str, ...] = (),
    ) -> ListingWriteOutcome:
        assert_catalog_writes_allowed(self.settings)
        content_fields = self._base_listing_fields_to_update(changed_fields, payload)
        if content_fields:
            assignments = ",\n                    ".join(
                f"{field_name} = :{field_name}" for field_name in content_fields
            )
            self.session.execute(
                text(
                    f"""
                    UPDATE listings
                    SET {assignments},
                        updated_at = NOW()
                    WHERE id = :listing_id
                    """
                ),
                {
                    **self._listing_params(payload),
                    "listing_id": listing_id,
                },
            )
        elif changed_fields:
            self.session.execute(
                text(
                    """
                    UPDATE listings
                    SET updated_at = NOW()
                    WHERE id = :listing_id
                    """
                ),
                {"listing_id": listing_id},
            )
        missing_slugs: list[str] = []
        for attribute in payload.attributes:
            if not self.upsert_attribute(listing_id, attribute):
                missing_slugs.append(attribute.slug)
        return ListingWriteOutcome(
            listing_id=listing_id,
            changed=bool(changed_fields or content_fields or missing_slugs),
            missing_attribute_slugs=tuple(missing_slugs),
        )

    def upsert_attribute(
        self,
        listing_id: int,
        attribute_slug: str | CatalogAttributePayload,
        value: Any | None = None,
    ) -> bool:
        assert_catalog_writes_allowed(self.settings)
        payload = (
            attribute_slug
            if isinstance(attribute_slug, CatalogAttributePayload)
            else CatalogAttributePayload(slug=attribute_slug, value=value)
        )
        attribute_id = self.reference_resolver.resolve_attribute_id_by_slug(payload.slug)
        if attribute_id is None:
            if payload.slug == "external_id":
                raise RuntimeError(f"required catalog attribute slug={payload.slug!r} is missing")
            logger.warning("catalog attribute slug=%s is missing; skipping", payload.slug)
            return False

        option_id = self._resolve_attribute_option_id(payload)
        params = {
            "listing_id": listing_id,
            "attribute_id": attribute_id,
            "attribute_options_id": option_id,
            **self._value_columns(payload.value),
        }
        existing = (
            self.session.execute(
                text(
                    """
                    SELECT id
                    FROM listing_attributes
                    WHERE listing_id = :listing_id
                      AND attribute_id = :attribute_id
                    LIMIT 1
                    """
                ),
                params,
            )
            .mappings()
            .first()
        )
        if existing:
            self.session.execute(
                text(
                    """
                    UPDATE listing_attributes
                    SET attribute_options_id = :attribute_options_id,
                        value_text = :value_text,
                        value_number = :value_number,
                        value_boolean = :value_boolean,
                        value_date = :value_date,
                        value_json = :value_json
                    WHERE id = :id
                    """
                ),
                {**params, "id": existing["id"]},
            )
        else:
            self.session.execute(
                text(
                    """
                    INSERT INTO listing_attributes (
                      listing_id, attribute_id, attribute_options_id,
                      value_text, value_number, value_boolean, value_date, value_json
                    )
                    VALUES (
                      :listing_id, :attribute_id, :attribute_options_id,
                      :value_text, :value_number, :value_boolean, :value_date, :value_json
                    )
                    """
                ),
                params,
            )
        return True

    def deactivate_listing(self, listing_id: int) -> None:
        assert_catalog_writes_allowed(self.settings)
        self.session.execute(
            text(
                """
                UPDATE listings
                SET status = :inactive_status,
                    updated_at = NOW()
                WHERE id = :listing_id
                """
            ),
            {
                "listing_id": listing_id,
                "inactive_status": self.settings.sync_catalog_inactive_status,
            },
        )
        self.session.execute(
            text(
                """
                UPDATE images
                SET status = :inactive_status
                WHERE listing_id = :listing_id
                """
            ),
            {
                "listing_id": listing_id,
                "inactive_status": self.settings.sync_catalog_image_inactive_status,
            },
        )

    def insert_image(self, listing_id: int, image_payload: CatalogImagePayload) -> int:
        assert_catalog_writes_allowed(self.settings)
        existing = (
            self.session.execute(
                text(
                    """
                    SELECT id
                    FROM images
                    WHERE listing_id = :listing_id
                      AND hash = :hash
                    LIMIT 1
                    """
                ),
                {"listing_id": listing_id, "hash": image_payload.hash},
            )
            .mappings()
            .first()
        )
        if existing:
            self.session.execute(
                text(
                    """
                    UPDATE images
                    SET status = :status,
                        is_blurred = :is_blurred,
                        priority = :priority,
                        external_url = :external_url
                    WHERE id = :id
                    """
                ),
                {"id": existing["id"], **image_payload.__dict__},
            )
            return int(existing["id"])

        row = (
            self.session.execute(
                text(
                    """
                    INSERT INTO images (
                      listing_id, hash, status, is_blurred, priority, external_url, user_id,
                      created_at
                    )
                    VALUES (
                      :listing_id, :hash, :status, :is_blurred, :priority, :external_url, :user_id,
                      NOW()
                    )
                    RETURNING id
                    """
                ),
                {"listing_id": listing_id, **image_payload.__dict__},
            )
            .mappings()
            .one()
        )
        return int(row["id"])

    def deactivate_missing_images(
        self,
        *,
        listing_id: int,
        current_urls: set[str],
        new_urls: set[str],
    ) -> int:
        assert_catalog_writes_allowed(self.settings)
        missing_urls = tuple(sorted(current_urls - new_urls))
        if not missing_urls:
            return 0
        result = self.session.execute(
            text(
                """
                UPDATE images
                SET status = :inactive_status
                WHERE listing_id = :listing_id
                  AND external_url IN :missing_urls
                """
            ).bindparams(bindparam("missing_urls", expanding=True)),
            {
                "listing_id": listing_id,
                "missing_urls": missing_urls,
                "inactive_status": self.settings.sync_catalog_image_inactive_status,
            },
        )
        return int(result.rowcount or 0)

    def _resolve_attribute_option_id(self, payload: CatalogAttributePayload) -> int | None:
        if payload.option_old_mysql_id not in (None, ""):
            option = self.reference_resolver.resolve_option_by_attribute_slug_and_old_mysql_id(
                payload.slug,
                payload.option_old_mysql_id,
                parent_option_id=payload.parent_option_id,
            )
            return option.id if option else None
        if payload.option_value:
            option = self.reference_resolver.resolve_option_by_attribute_slug_and_value(
                payload.slug,
                payload.option_value,
                parent_option_id=payload.parent_option_id,
            )
            return option.id if option else None
        return None

    def _listing_from_row(self, row: Any) -> ExistingListing:
        return ExistingListing(
            id=int(row["id"]),
            external_id=str(row["external_id"]),
            source=str(row["source"]),
            user_id=int(row["user_id"]),
            category_id=int(row["category_id"]),
            title=row.get("title"),
            description=row.get("description"),
            price=row.get("price"),
            currency=row.get("currency"),
            status=row.get("status"),
            slug=row.get("slug"),
        )

    def _listing_params(self, payload: CatalogListingPayload) -> dict[str, Any]:
        return {
            "user_id": payload.user_id,
            "category_id": payload.category_id,
            "title": payload.title,
            "description": payload.description,
            "price": payload.price,
            "currency": payload.currency,
            "status": payload.status,
            "slug": stable_slug(payload.title, payload.external_id),
        }

    def _base_listing_fields_to_update(
        self,
        changed_fields: tuple[str, ...],
        payload: CatalogListingPayload,
    ) -> list[str]:
        allowed_fields = ["title", "description", "price", "currency", "status", "slug"]
        changed = set(changed_fields)
        fields: list[str] = []
        for field_name in allowed_fields:
            if field_name == "slug" and {"title", "external_id"} & changed:
                fields.append(field_name)
                continue
            if field_name not in changed:
                continue
            value = getattr(payload, field_name)
            if field_name in {"title", "description"}:
                if value:
                    fields.append(field_name)
            elif field_name in {"price", "currency"}:
                if value not in (None, ""):
                    fields.append(field_name)
            else:
                fields.append(field_name)
        return fields

    def _value_columns(self, value: Any) -> dict[str, Any]:
        columns = {
            "value_text": None,
            "value_number": None,
            "value_boolean": None,
            "value_date": None,
            "value_json": None,
        }
        if isinstance(value, bool):
            columns["value_boolean"] = value
        elif isinstance(value, int | float | Decimal):
            columns["value_number"] = value
        elif isinstance(value, dict | list | tuple):
            columns["value_json"] = list(value) if isinstance(value, tuple) else value
        elif value is not None:
            columns["value_text"] = str(value)
        return columns

    def _attribute_value_from_row(self, row: Any) -> Any:
        for column in ("value_text", "value_number", "value_boolean", "value_date", "value_json"):
            if row.get(column) is not None:
                return row[column]
        if row.get("attribute_options_id") is not None:
            return row.get("attribute_options_id")
        return None
