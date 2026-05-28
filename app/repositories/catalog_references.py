import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AttributeReference:
    id: int
    slug: str
    name: str | None = None


@dataclass(frozen=True)
class AttributeOptionReference:
    id: int
    attribute_id: int
    value: str | None
    label: str | None = None
    old_mysql_id: int | None = None
    parent_option_id: int | None = None


class CatalogReferenceResolver:
    def __init__(self, session: Session) -> None:
        self.session = session
        self._attributes_by_slug: dict[str, AttributeReference | None] = {}
        self._options_by_old_id: dict[
            tuple[str, str, int | None],
            AttributeOptionReference | None,
        ] = {}
        self._options_by_value: dict[
            tuple[str, str, int | None],
            AttributeOptionReference | None,
        ] = {}

    def resolve_attribute_id_by_slug(self, slug: str) -> int | None:
        reference = self.resolve_attribute_by_slug(slug)
        return reference.id if reference else None

    def resolve_attribute_by_slug(self, slug: str) -> AttributeReference | None:
        normalized_slug = slug.strip()
        if normalized_slug in self._attributes_by_slug:
            return self._attributes_by_slug[normalized_slug]

        row = (
            self.session.execute(
                text(
                    """
                    SELECT id, slug, name_ru, name_en, name_kg
                    FROM attributes
                    WHERE slug = :slug
                    LIMIT 1
                    """
                ),
                {"slug": normalized_slug},
            )
            .mappings()
            .first()
        )
        reference = (
            AttributeReference(
                id=int(row["id"]),
                slug=str(row["slug"]),
                name=row.get("name_ru") or row.get("name_en") or row.get("name_kg"),
            )
            if row
            else None
        )
        self._attributes_by_slug[normalized_slug] = reference
        if reference is None:
            logger.warning("catalog attribute slug=%s was not found", normalized_slug)
        return reference

    def resolve_option_by_attribute_slug_and_old_mysql_id(
        self,
        attribute_slug: str,
        old_mysql_id: int | str | None,
        *,
        parent_option_id: int | None = None,
    ) -> AttributeOptionReference | None:
        if old_mysql_id in (None, ""):
            return None
        key = (attribute_slug, str(old_mysql_id), parent_option_id)
        if key in self._options_by_old_id:
            return self._options_by_old_id[key]

        attribute_id = self.resolve_attribute_id_by_slug(attribute_slug)
        if attribute_id is None:
            self._options_by_old_id[key] = None
            return None

        try:
            normalized_old_mysql_id = int(old_mysql_id)
        except (TypeError, ValueError):
            logger.warning(
                "catalog option old_mysql_id is not numeric attribute=%s old_mysql_id=%s",
                attribute_slug,
                old_mysql_id,
            )
            self._options_by_old_id[key] = None
            return None

        params: dict[str, Any] = {
            "attribute_id": attribute_id,
            "old_mysql_id": normalized_old_mysql_id,
            "parent_option_id": parent_option_id,
        }
        parent_clause = (
            "AND parent_option_id = :parent_option_id" if parent_option_id is not None else ""
        )
        row = (
            self.session.execute(
                text(
                    f"""
                    SELECT id, attribute_id, value, label, old_mysql_id, parent_option_id
                    FROM attribute_options
                    WHERE attribute_id = :attribute_id
                      AND old_mysql_id = :old_mysql_id
                      {parent_clause}
                    ORDER BY is_active DESC NULLS LAST, id ASC
                    LIMIT 1
                    """
                ),
                params,
            )
            .mappings()
            .first()
        )
        reference = self._option_from_row(row)
        self._options_by_old_id[key] = reference
        if reference is None:
            logger.warning(
                "catalog option was not found by old_mysql_id attribute=%s old_mysql_id=%s",
                attribute_slug,
                old_mysql_id,
            )
        return reference

    def resolve_option_by_attribute_slug_and_value(
        self,
        attribute_slug: str,
        value: str | None = None,
        *,
        label: str | None = None,
        parent_option_id: int | None = None,
    ) -> AttributeOptionReference | None:
        lookup_value = (value or label or "").strip()
        if not lookup_value:
            return None
        key = (attribute_slug, lookup_value.lower(), parent_option_id)
        if key in self._options_by_value:
            return self._options_by_value[key]

        attribute_id = self.resolve_attribute_id_by_slug(attribute_slug)
        if attribute_id is None:
            self._options_by_value[key] = None
            return None

        params: dict[str, Any] = {
            "attribute_id": attribute_id,
            "lookup_value": lookup_value.lower(),
            "parent_option_id": parent_option_id,
        }
        parent_clause = (
            "AND parent_option_id = :parent_option_id" if parent_option_id is not None else ""
        )
        row = (
            self.session.execute(
                text(
                    f"""
                    SELECT id, attribute_id, value, label, old_mysql_id, parent_option_id
                    FROM attribute_options
                    WHERE attribute_id = :attribute_id
                      AND (
                        lower(value) = :lookup_value
                        OR lower(label) = :lookup_value
                      )
                      {parent_clause}
                    ORDER BY is_active DESC NULLS LAST, id ASC
                    LIMIT 1
                    """
                ),
                params,
            )
            .mappings()
            .first()
        )
        reference = self._option_from_row(row)
        self._options_by_value[key] = reference
        if reference is None:
            logger.warning(
                "catalog option was not found by value attribute=%s value=%s",
                attribute_slug,
                lookup_value,
            )
        return reference

    def _option_from_row(self, row: Any) -> AttributeOptionReference | None:
        if not row:
            return None
        return AttributeOptionReference(
            id=int(row["id"]),
            attribute_id=int(row["attribute_id"]),
            value=row.get("value"),
            label=row.get("label"),
            old_mysql_id=row.get("old_mysql_id"),
            parent_option_id=row.get("parent_option_id"),
        )
