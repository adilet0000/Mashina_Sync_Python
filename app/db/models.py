from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    category_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(16), nullable=True)
    status: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    slug: Mapped[str | None] = mapped_column(String(500), nullable=True)
    upped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ListingAttribute(Base):
    __tablename__ = "listing_attributes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"), nullable=False, index=True)
    attribute_id: Mapped[int] = mapped_column(
        ForeignKey("attributes.id"),
        nullable=False,
        index=True,
    )
    attribute_options_id: Mapped[int | None] = mapped_column(
        ForeignKey("attribute_options.id"),
        nullable=True,
        index=True,
    )
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_number: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    value_boolean: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    value_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    value_json: Mapped[Any | None] = mapped_column(JSON, nullable=True)


class Attribute(Base):
    __tablename__ = "attributes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)


class AttributeOption(Base):
    __tablename__ = "attribute_options"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    attribute_id: Mapped[int] = mapped_column(
        ForeignKey("attributes.id"),
        nullable=False,
        index=True,
    )
    parent_option_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    old_mysql_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    is_active: Mapped[bool | None] = mapped_column(Boolean, nullable=True)


class Image(Base):
    __tablename__ = "images"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"), nullable=False, index=True)
    hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_blurred: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    external_url: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ListingCounter(Base):
    __tablename__ = "listing_counters"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"), nullable=False, index=True)


class ListingPromotion(Base):
    __tablename__ = "listing_promotions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"), nullable=False, index=True)
