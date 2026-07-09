"""Domain models — Receipt parsing (Fase 1 MVP).

Estas entidades son independientes de FastAPI, de la BD y del proveedor OCR.
El parser recibe texto OCR crudo y devuelve un ParsedReceipt con confianza
por campo, siguiendo la regla de oro: solo se pide confirmación de campos
ambiguos, nunca del ticket completo.
"""
from __future__ import annotations

from datetime import date, time
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class Unit(str, Enum):
    UNIT = "unit"
    KG = "kg"
    L = "l"


class PaymentMethod(str, Enum):
    CARD = "card"
    CASH = "cash"
    OTHER = "other"


class FieldConfidence(BaseModel):
    """Confianza de un campo detectado. field_path usa notación
    JSONPath simplificada: 'total_amount', 'lines[3].quantity'..."""

    field_path: str
    confidence: float = Field(ge=0.0, le=1.0)
    detected_value: str | None = None
    suggestion: str | None = None  # valor alternativo por heurística


class ParsedLine(BaseModel):
    line_number: int
    raw_text: str
    description: str
    quantity: Decimal = Decimal("1")
    unit: Unit = Unit.UNIT
    unit_price: Decimal | None = None  # €/kg, €/l o €/unidad
    line_total: Decimal
    discount_amount: Decimal = Decimal("0")
    promotion_text: str | None = None
    vat_rate: Decimal | None = None  # 4 / 10 / 21
    expiry_date: date | None = None  # si el ticket lo imprime (Makro sí)
    lot_code: str | None = None
    gtin: str | None = None
    confidence: float = 1.0


class ParsedReceipt(BaseModel):
    supermarket_key: str  # 'makro', 'mercadona', 'generic'...
    purchase_date: date | None = None
    purchase_time: time | None = None
    total_amount: Decimal | None = None
    total_vat: Decimal | None = None
    total_discounts: Decimal = Decimal("0")  # valor declarado en el ticket
    discount_lines_total: Decimal = Decimal("0")  # suma de líneas de descuento
    payment_method: PaymentMethod | None = None
    invoice_number: str | None = None
    lines: list[ParsedLine] = []
    pending_fields: list[FieldConfidence] = []
    overall_confidence: float = 0.0

    def lines_sum(self) -> Decimal:
        return sum((l.line_total for l in self.lines), Decimal("0"))

    def totals_reconcile(self, tolerance: Decimal = Decimal("0.05")) -> bool:
        """El total del ticket debe cuadrar con la suma de líneas
        menos descuentos globales (heurística de validación clave)."""
        if self.total_amount is None:
            return False
        expected = self.lines_sum() - self.total_discounts
        # En Makro el total incluye IVA aparte; en Mercadona el precio de
        # línea ya lleva IVA. El parser decide qué comparar.
        return abs(self.total_amount - expected) <= tolerance
