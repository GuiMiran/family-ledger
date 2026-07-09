"""Parser de tickets Lidl (Lidl Supermercados S.A.).

Validado contra ticket real (El Prat de Llobregat, 04/07/2026, 151,46 €,
48 líneas). Particularidades del formato Lidl:

- Precios de línea CON IVA (PVP), letra de grupo de IVA al final:
    'MACARRONS RATLLATS    1,09x  2      2,18 B'   (multi-unidad)
    'SPAGHETTI INTEGRAL                  1,09 B'   (unidad simple)
- Productos a peso: sublínea bajo el artículo:
    'FILET D'ANOLL 1ª A                  8,30 B'
    '  0,472 kg x 17,59  EUR/kg'
- Descuentos como sublínea negativa del artículo anterior:
    '  Desc.                            -1,10'
    '    PROMO LIDL PLUS                -0,30'
- Tabla de IVA con letras: 'A  4%  2,10  52,42  54,52' → A=4 %, B=10 %, C=21 %
- La letra final [ABC] es el discriminador fuerte de línea de artículo:
  totales, entregas y tabla de IVA no la llevan.
"""
from __future__ import annotations

import re
from datetime import time as dtime
from decimal import Decimal

from app.domain.receipts.models import (
    FieldConfidence,
    ParsedLine,
    ParsedReceipt,
    PaymentMethod,
    Unit,
)
from app.domain.receipts.parser import ReceiptParser
from app.infrastructure.parsers.base import es_date, es_decimal, normalize_ocr_text

_ITEM_RE = re.compile(
    r"""^(?P<desc>\S.*?)\s+
    (?:(?P<unit_price>\d+,\d{2})x\s+(?P<qty>\d+)\s+)?   # multi-unidad opcional
    (?P<total>\d+,\d{2})\s+
    (?P<vat>[ABC])\s*$
    """,
    re.VERBOSE,
)
_WEIGHT_SUB_RE = re.compile(
    r"^\s*(?P<w>\d+,\d{1,3})\s*kg\s*x\s*(?P<pkg>\d+,\d{2})\s+EUR/kg\s*$"
)
_DISCOUNT_SUB_RE = re.compile(
    r"^\s*(?P<label>Desc\.|PROMO\s+LIDL\s+PLUS)\s+(?P<amt>-\d+,\d{2})\s*$",
    re.IGNORECASE,
)
_VAT_TABLE_RE = re.compile(
    r"^(?P<letter>[ABC])\s+(?P<rate>\d{1,2})%\s+\d+,\d{2}\s+\d+,\d{2}\s+\d+,\d{2}\s*$"
)
_TOTAL_RE = re.compile(r"^TOTAL\s+(?P<t>\d+(?:\.\d{3})*,\d{2})\s*$")
_DATE_TIME_RE = re.compile(
    r"(?P<date>\d{2}/\d{2}/\d{4})\s+(?P<h>\d{2}):(?P<m>\d{2})(?::\d{2})?"
)
_PAYMENT_RE = re.compile(r"VENTA\s+(DEBIT|CREDIT)", re.IGNORECASE)
_TOTAL_DISCOUNT_RE = re.compile(
    r"Desc\.\s+total\s+en\s+compra\s*\|?\s*$|^\s*\|?\s*(?P<t>\d+,\d{2})\s*EUR\s*\|?\s*$"
)

_CONFIDENCE_THRESHOLD = 0.85


class LidlParser(ReceiptParser):
    key = "lidl"

    def can_parse(self, ocr_text: str) -> float:
        text = ocr_text.upper()
        score = 0.0
        if "LIDL" in text:
            score += 0.7
        if "LIDL PLUS" in text or "EUR/KG" in text:
            score += 0.15
        if re.search(r"\d+,\d{2}\s+[ABC]\s*$", ocr_text, re.MULTILINE):
            score += 0.15
        return min(score, 1.0)

    def parse(self, ocr_text: str) -> ParsedReceipt:
        lines = normalize_ocr_text(ocr_text)
        receipt = ParsedReceipt(supermarket_key=self.key)
        parsed_lines: list[ParsedLine] = []
        vat_by_letter: dict[str, Decimal] = {}
        letter_by_line: dict[int, str] = {}
        expecting_discount_total = False

        for raw in lines:
            stripped = raw.strip()

            # tabla de IVA (antes que artículo: 'A  4% ...' no lleva letra final)
            if m := _VAT_TABLE_RE.match(stripped):
                vat_by_letter[m.group("letter")] = es_decimal(m.group("rate"))
                continue

            if m := _TOTAL_RE.match(stripped):
                receipt.total_amount = es_decimal(m.group("t"))
                continue

            if m := _DATE_TIME_RE.search(stripped):
                receipt.purchase_date = es_date(m.group("date"))
                receipt.purchase_time = dtime(int(m.group("h")), int(m.group("m")))
                continue

            if _PAYMENT_RE.search(stripped):
                receipt.payment_method = PaymentMethod.CARD
                continue

            if "DESC. TOTAL EN COMPRA" in stripped.upper():
                expecting_discount_total = True
                continue
            if expecting_discount_total:
                if m := re.search(r"(?P<t>\d+,\d{2})\s*EUR", stripped):
                    receipt.total_discounts = es_decimal(m.group("t")) or Decimal("0")
                    expecting_discount_total = False
                    continue

            # sublínea de peso → convierte el artículo anterior a kg
            if (m := _WEIGHT_SUB_RE.match(raw)) and parsed_lines:
                prev = parsed_lines[-1]
                prev.quantity = es_decimal(m.group("w")) or prev.quantity
                prev.unit = Unit.KG
                prev.unit_price = es_decimal(m.group("pkg"))
                if prev.unit_price and prev.quantity:
                    err = abs(prev.unit_price * prev.quantity - prev.line_total)
                    prev.confidence = 1.0 if err <= Decimal("0.02") else 0.6
                continue

            # sublínea de descuento → se asocia al artículo anterior
            if (m := _DISCOUNT_SUB_RE.match(raw)) and parsed_lines:
                prev = parsed_lines[-1]
                amount = abs(es_decimal(m.group("amt")) or Decimal("0"))
                prev.discount_amount += amount
                prev.promotion_text = m.group("label").strip()
                receipt.discount_lines_total += amount
                continue

            # línea de artículo (discriminador: letra IVA final)
            if m := _ITEM_RE.match(stripped):
                qty = es_decimal(m.group("qty")) if m.group("qty") else Decimal("1")
                total = es_decimal(m.group("total")) or Decimal("0")
                unit_price = (
                    es_decimal(m.group("unit_price"))
                    if m.group("unit_price")
                    else total
                )
                confidence = 1.0
                if m.group("qty") and unit_price is not None:
                    err = abs(unit_price * qty - total)
                    confidence = 1.0 if err <= Decimal("0.02") else 0.6
                line = ParsedLine(
                    line_number=len(parsed_lines) + 1,
                    raw_text=raw.strip(),
                    description=m.group("desc").strip(),
                    quantity=qty,
                    unit=Unit.UNIT,
                    unit_price=unit_price,
                    line_total=total,
                    confidence=confidence,
                )
                letter_by_line[line.line_number] = m.group("vat")
                parsed_lines.append(line)
                continue

        for line in parsed_lines:
            letter = letter_by_line.get(line.line_number)
            if letter and letter in vat_by_letter:
                line.vat_rate = vat_by_letter[letter]

        receipt.lines = parsed_lines
        self._score(receipt)
        return receipt

    def _score(self, receipt: ParsedReceipt) -> None:
        """Lidl: precios CON IVA → total == suma líneas − descuentos de línea."""
        pending: list[FieldConfidence] = []

        if receipt.purchase_date is None:
            pending.append(FieldConfidence(field_path="purchase_date", confidence=0.0))
        if receipt.total_amount is None:
            pending.append(
                FieldConfidence(
                    field_path="total_amount",
                    confidence=0.0,
                    suggestion=str(
                        receipt.lines_sum() - receipt.discount_lines_total
                    ),
                )
            )
        else:
            expected = receipt.lines_sum() - receipt.discount_lines_total
            if abs(receipt.total_amount - expected) > Decimal("0.05"):
                pending.append(
                    FieldConfidence(
                        field_path="total_amount",
                        confidence=0.5,
                        detected_value=str(receipt.total_amount),
                        suggestion=str(expected),
                    )
                )

        for line in receipt.lines:
            if line.confidence < _CONFIDENCE_THRESHOLD:
                pending.append(
                    FieldConfidence(
                        field_path=f"lines[{line.line_number - 1}].line_total",
                        confidence=line.confidence,
                        detected_value=str(line.line_total),
                    )
                )

        receipt.pending_fields = pending
        line_conf = (
            sum(l.confidence for l in receipt.lines) / len(receipt.lines)
            if receipt.lines
            else 0.0
        )
        header_ok = not any(
            p.field_path in ("purchase_date", "total_amount") for p in pending
        )
        receipt.overall_confidence = round(
            0.6 * line_conf + 0.4 * (1.0 if header_ok else 0.6), 3
        )
