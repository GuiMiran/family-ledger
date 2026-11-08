"""ORM SQLAlchemy 2.0 — implementación del modelo de datos spec (Fase 1).

Diseñado para PostgreSQL 16 (JSONB, UUID nativo, pg_trgm). Los TypeDecorators
GUID/JSONField permiten ejecutar la misma capa sobre SQLite en tests.
"""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric,
    SmallInteger, String, Text, TypeDecorator, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class GUID(TypeDecorator):
    """UUID nativo en PostgreSQL, CHAR(36) en SQLite."""
    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return value if dialect.name == "postgresql" else str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value if isinstance(value, uuid.UUID) else uuid.UUID(value)


class JSONField(TypeDecorator):
    """JSONB en PostgreSQL, TEXT-JSON en SQLite."""
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if value is None or dialect.name == "postgresql":
            return value
        return json.dumps(value, ensure_ascii=False)

    def process_result_value(self, value, dialect):
        if value is None or dialect.name == "postgresql":
            return value
        return json.loads(value)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


# ────────────────────── Identidad ──────────────────────
class Family(TimestampMixin, Base):
    __tablename__ = "families"
    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text)
    members_count: Mapped[int] = mapped_column(SmallInteger, default=1)


# ────────────────────── Catálogo ──────────────────────
class Supermarket(TimestampMixin, Base):
    __tablename__ = "supermarkets"
    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, unique=True)
    parser_key: Mapped[str] = mapped_column(Text)


class Category(TimestampMixin, Base):
    __tablename__ = "categories"
    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("categories.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(Text)


class Product(TimestampMixin, Base):
    __tablename__ = "products"
    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    family_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("families.id"), nullable=True
    )  # NULL = producto global compartido
    canonical_name: Mapped[str] = mapped_column(Text)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("categories.id"), nullable=True
    )
    brand: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_unit: Mapped[str] = mapped_column(
        String(8), CheckConstraint("default_unit IN ('unit','kg','l')"), default="unit"
    )
    typical_shelf_life_days: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True
    )
    is_freezable: Mapped[bool] = mapped_column(Boolean, default=False)

    aliases: Mapped[list["ProductAlias"]] = relationship(back_populates="product")


class ProductAlias(TimestampMixin, Base):
    """El corazón de la normalización: texto de ticket → producto canónico.
    'MACARRONS RATLLATS' (Lidl) y 'MACARRON PLUMA 3 ARO 5KG' (Makro)
    apuntan al mismo Product para poder comparar €/kg entre cadenas."""
    __tablename__ = "product_aliases"
    __table_args__ = (
        UniqueConstraint("family_id", "product_id", "supermarket_id", "alias_text", name="uq_alias_scoped"),
        Index("ix_alias_text", "alias_text"),
        # En PostgreSQL, además: CREATE INDEX ... USING gin (alias_text gin_trgm_ops)
    )
    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("products.id"))
    family_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("families.id"), nullable=True
    )  # NULL only for deliberately shared aliases
    supermarket_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("supermarkets.id"), nullable=True
    )  # NULL = alias válido en cualquier cadena
    alias_text: Mapped[str] = mapped_column(Text)
    match_type: Mapped[str] = mapped_column(
        String(8), CheckConstraint("match_type IN ('exact','fuzzy','ai','manual')")
    )
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3), default=Decimal("1"))

    product: Mapped[Product] = relationship(back_populates="aliases")


# ────────────────────── Tickets ──────────────────────
class Receipt(TimestampMixin, Base):
    __tablename__ = "receipts"
    __table_args__ = (Index("ix_receipts_family_date", "family_id", "purchase_date"),)
    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    family_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("families.id"))
    supermarket_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("supermarkets.id"), nullable=True
    )
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    total_vat: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    total_discounts: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    payment_method: Mapped[str | None] = mapped_column(String(8), nullable=True)
    invoice_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_ocr: Mapped[dict | None] = mapped_column(JSONField, nullable=True)
    ocr_confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3), default=0)
    status: Mapped[str] = mapped_column(
        String(16),
        CheckConstraint("status IN ('pending_review','confirmed','rejected')"),
        default="pending_review",
    )

    lines: Mapped[list["ReceiptLine"]] = relationship(
        back_populates="receipt", cascade="all, delete-orphan"
    )


class ReceiptLine(TimestampMixin, Base):
    __tablename__ = "receipt_lines"
    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    receipt_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("receipts.id"))
    line_number: Mapped[int] = mapped_column(SmallInteger)
    raw_text: Mapped[str] = mapped_column(Text)
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("products.id"), nullable=True
    )  # NULL hasta normalizar
    description: Mapped[str] = mapped_column(Text)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 3), default=1)
    unit: Mapped[str] = mapped_column(String(8), default="unit")
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    line_total: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    promotion_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    vat_rate: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    match_type: Mapped[str | None] = mapped_column(String(12), nullable=True)
    match_confidence: Mapped[Decimal | None] = mapped_column(
        Numeric(4, 3), nullable=True
    )

    receipt: Mapped[Receipt] = relationship(back_populates="lines")


class ProductPriceHistory(TimestampMixin, Base):
    """Una fila por línea normalizada. Base de la comparativa €/kg
    entre supermercados y de la inflación familiar."""
    __tablename__ = "product_price_history"
    __table_args__ = (
        Index("ix_pph_product_market_date", "product_id", "supermarket_id", "date"),
    )
    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("products.id"))
    supermarket_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("supermarkets.id"), nullable=True
    )
    family_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("families.id"))
    date: Mapped[date] = mapped_column(Date)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    unit: Mapped[str] = mapped_column(String(8))
    had_promotion: Mapped[bool] = mapped_column(Boolean, default=False)


class NormalizationReview(TimestampMixin, Base):
    """Cola de revisión: líneas que ningún matcher pudo resolver con
    confianza suficiente. El usuario confirma UNA vez → alias aprendido."""
    __tablename__ = "normalization_reviews"
    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    receipt_line_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("receipt_lines.id")
    )
    alias_text: Mapped[str] = mapped_column(Text)
    supermarket_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("supermarkets.id"), nullable=True
    )
    ai_proposal: Mapped[dict | None] = mapped_column(JSONField, nullable=True)
    status: Mapped[str] = mapped_column(String(12), default="pending")


class ReceiptSubmission(TimestampMixin, Base):
    """Idempotency is family scoped and survives process restarts."""
    __tablename__ = "receipt_submissions"
    __table_args__ = (UniqueConstraint("family_id", "key", name="uq_submission_family_key"),)
    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    family_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("families.id"))
    key: Mapped[str] = mapped_column(String(128))
    request_digest: Mapped[str] = mapped_column(String(64))
    receipt_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("receipts.id"))
    payload: Mapped[dict] = mapped_column(JSONField)


class ReceiptEvent(TimestampMixin, Base):
    __tablename__ = "receipt_events"
    __table_args__ = (UniqueConstraint("receipt_id", "event_type", name="uq_receipt_event"),)
    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    family_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("families.id"))
    receipt_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("receipts.id"))
    event_type: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSONField)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)


class InventoryEntry(TimestampMixin, Base):
    """Purchase projection; consumption/reservations remain a separate workflow."""
    __tablename__ = "inventory_entries"
    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    family_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("families.id"))
    receipt_line_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("receipt_lines.id"), unique=True)
    product_id: Mapped[uuid.UUID | None] = mapped_column(GUID, ForeignKey("products.id"), nullable=True)
    description: Mapped[str] = mapped_column(Text)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    unit: Mapped[str] = mapped_column(String(8))
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)


# @spectra INV-006
class ShoppingProfileRow(TimestampMixin, Base):
    __tablename__ = "shopping_profiles"
    family_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("families.id"), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSONField)


class PriceObservationRow(TimestampMixin, Base):
    """Snapshots belong to the requesting household, including personalized quotes."""
    __tablename__ = "price_observations"
    __table_args__ = (Index("ix_price_observations_family", "family_id"),)
    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    family_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("families.id"))
    payload: Mapped[dict] = mapped_column(JSONField)


class ShoppingAuditRow(TimestampMixin, Base):
    __tablename__ = "shopping_audits"
    __table_args__ = (Index("ix_shopping_audits_family", "family_id"),)
    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    family_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("families.id"))
    payload: Mapped[dict] = mapped_column(JSONField)
