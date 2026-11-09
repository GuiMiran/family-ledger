"""Mercadona-format receipt parser.

Synthetic format examples are maintained only in tests/fixtures. Receipt line
prices include VAT; quantity and weight formats, missing fields and totals are
validated without embedding an individual's shopping record in source code.
"""
from __future__ import annotations

import re
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

_DATE_TIME_RE = re.compile(
    r"(?P<date>\d{2}/\d{2}/\d{4})\s+(?P<time>\d{2}:\d{2})"
)
_INVOICE_RE = re.compile(r"FACTURA\s+SIMPLIFICADA:\s*(?P<inv>[\d\-]+)")
_TOTAL_RE = re.compile(r"TOTAL\s*\(€\)\s+(?P<t>\d+(?:\.\d{3})*,\d{2})")
_CARD_RE = re.compile(r"TARJETA\s+(?:BANCARIA\s+)?(?P<t>\d+(?:\.\d{3})*,\d{2})")
_CASH_RE = re.compile(r"EFECTIVO\s+(?P<t>\d+(?:\.\d{3})*,\d{2})")
_VAT_LINE_RE = re.compile(
    r"^(?P<rate>\d{1,2})%\s+(?P<base>\d+(?:\.\d{3})*,\d{2})\s+(?P<vat>\d+(?:\.\d{3})*,\d{2})\s*$"
)

# '2 GALLETA RELIEVE  1,22  2,44'  |  '1 LECHE ENTERA 6X1L  5,10'
_UNIT_LINE_RE = re.compile(
    r"""^\s*
    (?P<qty>\d{1,2})\s+
    (?P<desc>[A-ZÁÉÍÓÚÑ0-9][A-ZÁÉÍÓÚÑ0-9\s%/.+\-]*?)\s+
    (?:(?P<unit_price>\d+,\d{2})\s+)?
    (?P<total>\d+,\d{2})\s*$
    """,
    re.VERBOSE,
)

# '0,536 kg PLATANO 2,29 €/kg 1,23' (una línea)
_WEIGHT_LINE_RE = re.compile(
    r"""^\s*
    (?P<weight>\d+,\d{1,3})\s*kg\s+
    (?P<desc>[A-ZÁÉÍÓÚÑ0-9][A-ZÁÉÍÓÚÑ0-9\s%/.+\-]*?)\s+
    (?P<price_kg>\d+,\d{2})\s*€/kg\s+
    (?P<total>\d+,\d{2})\s*$
    """,
    re.VERBOSE,
)

# peso en línea propia: '0,536 kg' → la siguiente línea trae desc + €/kg + total
_WEIGHT_ONLY_RE = re.compile(r"^\s*(?P<weight>\d+,\d{1,3})\s*kg\s*$")
_DESC_PRICE_RE = re.compile(
    r"""^\s*
    (?P<desc>[A-ZÁÉÍÓÚÑ0-9][A-ZÁÉÍÓÚÑ0-9\s%/.+\-]*?)\s+
    (?P<price_kg>\d+,\d{2})\s+
    (?P<total>\d+,\d{2})\s*$
    """,
    re.VERBOSE,
)

_SKIP_PREFIXES = (
    "MERCADONA",
    "TELÉFONO",
    "TELEFONO",
    "DESCRIPCIÓN",
    "DESCRIPCION",
    "IVA",
    "TOTAL",
    "SE ADMITEN",
    "N.C.",
)

_CONFIDENCE_THRESHOLD = 0.85


class MercadonaParser(ReceiptParser):
    key = "mercadona"

    def can_parse(self, ocr_text: str) -> float:
        text = ocr_text.upper()
        score = 0.0
        if "MERCADONA" in text:
            score += 0.7
        if "FACTURA SIMPLIFICADA" in text:
            score += 0.2
        if "A-46103834" in text:  # NIF de Mercadona
            score += 0.1
        return min(score, 1.0)

    def parse(self, ocr_text: str) -> ParsedReceipt:
        lines = normalize_ocr_text(ocr_text)
        receipt = ParsedReceipt(supermarket_key=self.key)
        parsed_lines: list[ParsedLine] = []
        pending_weight: Decimal | None = None
        in_vat_block = False

        for raw in lines:
            stripped = raw.strip()
            upper = stripped.upper()

            if m := _DATE_TIME_RE.search(stripped):
                receipt.purchase_date = es_date(m.group("date"))
                from datetime import time as _t

                h, mi = m.group("time").split(":")
                receipt.purchase_time = _t(int(h), int(mi))
                continue
            if m := _INVOICE_RE.search(upper):
                receipt.invoice_number = m.group("inv")
                continue
            if m := _TOTAL_RE.search(upper):
                receipt.total_amount = es_decimal(m.group("t"))
                in_vat_block = False
                continue
            if m := _CARD_RE.search(upper):
                receipt.payment_method = PaymentMethod.CARD
                continue
            if _CASH_RE.search(upper):
                receipt.payment_method = PaymentMethod.CASH
                continue
            if upper.startswith("IVA"):
                in_vat_block = True
                continue
            if in_vat_block and (m := _VAT_LINE_RE.match(stripped)):
                receipt.total_vat = (receipt.total_vat or Decimal("0")) + (
                    es_decimal(m.group("vat")) or Decimal("0")
                )
                continue

            # línea de peso partida en dos renglones
            if m := _WEIGHT_ONLY_RE.match(stripped):
                pending_weight = es_decimal(m.group("weight"))
                continue
            if pending_weight is not None and (m := _DESC_PRICE_RE.match(stripped)):
                parsed_lines.append(
                    self._weight_line(
                        raw, m.group("desc"), pending_weight,
                        es_decimal(m.group("price_kg")),
                        es_decimal(m.group("total")),
                        len(parsed_lines) + 1,
                    )
                )
                pending_weight = None
                continue
            pending_weight = None

            # línea de peso en un solo renglón
            if m := _WEIGHT_LINE_RE.match(stripped):
                parsed_lines.append(
                    self._weight_line(
                        raw, m.group("desc"),
                        es_decimal(m.group("weight")),
                        es_decimal(m.group("price_kg")),
                        es_decimal(m.group("total")),
                        len(parsed_lines) + 1,
                    )
                )
                continue

            if any(upper.startswith(p) for p in _SKIP_PREFIXES):
                continue

            # línea por unidades
            if m := _UNIT_LINE_RE.match(stripped):
                qty = es_decimal(m.group("qty")) or Decimal("1")
                total = es_decimal(m.group("total")) or Decimal("0")
                unit_price = es_decimal(m.group("unit_price")) if m.group(
                    "unit_price"
                ) else (total / qty if qty else None)
                confidence = 1.0
                if unit_price is not None and qty > 0:
                    err = abs(unit_price * qty - total)
                    confidence = 1.0 if err <= Decimal("0.02") else 0.6
                parsed_lines.append(
                    ParsedLine(
                        line_number=len(parsed_lines) + 1,
                        raw_text=raw.strip(),
                        description=m.group("desc").strip(),
                        quantity=qty,
                        unit=Unit.UNIT,
                        unit_price=unit_price,
                        line_total=total,
                        confidence=confidence,
                    )
                )
                continue

        receipt.lines = parsed_lines
        self._score(receipt)
        return receipt

    @staticmethod
    def _weight_line(
        raw: str,
        desc: str,
        weight: Decimal | None,
        price_kg: Decimal | None,
        total: Decimal | None,
        number: int,
    ) -> ParsedLine:
        weight = weight or Decimal("0")
        total = total or Decimal("0")
        confidence = 1.0
        if price_kg is not None and weight > 0:
            err = abs(price_kg * weight - total)
            confidence = 1.0 if err <= Decimal("0.02") else 0.6
        return ParsedLine(
            line_number=number,
            raw_text=raw.strip(),
            description=desc.strip(),
            quantity=weight,
            unit=Unit.KG,
            unit_price=price_kg,
            line_total=total,
            confidence=confidence,
        )

    def _score(self, receipt: ParsedReceipt) -> None:
        """Mercadona: precios CON IVA → la suma de líneas debe cuadrar
        directamente con el TOTAL (€)."""
        pending: list[FieldConfidence] = []

        if receipt.purchase_date is None:
            pending.append(FieldConfidence(field_path="purchase_date", confidence=0.0))
        if receipt.total_amount is None:
            pending.append(
                FieldConfidence(
                    field_path="total_amount",
                    confidence=0.0,
                    suggestion=str(receipt.lines_sum()),
                )
            )
        elif abs(receipt.total_amount - receipt.lines_sum()) > Decimal("0.05"):
            pending.append(
                FieldConfidence(
                    field_path="total_amount",
                    confidence=0.5,
                    detected_value=str(receipt.total_amount),
                    suggestion=str(receipt.lines_sum()),
                )
            )

        for line in receipt.lines:
            if line.confidence < _CONFIDENCE_THRESHOLD:
                idx = line.line_number - 1
                pending.append(
                    FieldConfidence(
                        field_path=f"lines[{idx}].line_total",
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
