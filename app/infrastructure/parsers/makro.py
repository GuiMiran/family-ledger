# @spectra BR-001
# @spectra BR-002
# @spectra INV-002
# @spectra POL-001
# @spectra SK-001
"""Parser de tickets/facturas Makro (Makro Distribución Mayorista, S.A.).

Formato validado contra ticket real de Makro Barcelona (Zona Franca).

Particularidades del formato Makro:
- Es factura, no ticket simple: precios de línea SIN IVA, desglose al pie.
- Línea de artículo: num_articulo, descripción, Cont (CJ/KG/BL/PQ/BD/BO),
  Prec.Ud., Cont P. (peso o unidades del bulto), Precio, Cant., Importe,
  Imp (grupo de impuesto), y opcionalmente Prec.Ud.* + código DT (promo).
- Sublíneas opcionales bajo el artículo:
    'BC GTIN: <gtin> Lote: <lote>'
    'Fecha consumo preferente: <YYMMDD>'  ← caducidad impresa, va directa
      al inventario sin estimación.
- Descuentos globales: línea 'COMPRA MÁS PAGA MENOS  1,29-  1  <codigo>'.
- Grupos de IVA: '153,12  1=10,00%  15,31' → grupo 1 = 10%.
- Totales: 'Importe' (base), 'Total a pagar' (con IVA), 'Tarjeta' (pago).
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
from app.infrastructure.parsers.base import (
    es_date,
    es_decimal,
    normalize_ocr_text,
    yymmdd_date,
)

# Códigos de contenido Makro → unidad de dominio
_CONT_TO_UNIT = {
    "KG": Unit.KG,
    "CJ": Unit.UNIT,  # caja
    "BL": Unit.UNIT,  # bolsa/blister
    "PQ": Unit.UNIT,  # paquete
    "BD": Unit.UNIT,  # bidón
    "BO": Unit.UNIT,  # bote
    "UD": Unit.UNIT,
}

_ARTICLE_RE = re.compile(
    r"""^\s*
    (?:M\s+)?                                  # marcador 'M' opcional
    (?P<article>\d{5,14})\s+                   # num artículo / GTIN
    (?P<desc>.+?)\s+                           # descripción (lazy)
    (?P<cont>KG|CJ|BL|PQ|BD|BO|UD)\s+          # código contenido
    (?P<prec_ud>\d+(?:,\d+)?)\s+               # precio unitario
    (?P<cont_p>\d+(?:,\d+)?)\s+                # contenido (peso o uds)
    (?P<precio>\d+(?:,\d+)?)\s+                # precio bulto
    (?P<cant>\d+)\s+                           # cantidad de bultos
    (?P<importe>\d+(?:,\d+)?)\s+               # importe línea
    (?P<imp>\d)                                # grupo impuesto
    (?:\s+(?P<prec_promo>\d+(?:,\d+)?)\s+(?P<dt>\d+))?  # promo opcional
    """,
    re.VERBOSE,
)

_GTIN_LOT_RE = re.compile(r"BC\s+GTIN:\s*(?P<gtin>\d+)\s+Lote:\s*(?P<lot>\S+)")
_EXPIRY_RE = re.compile(r"Fecha\s+consumo\s+preferente:\s*(?P<d>\d{6})")
_GLOBAL_DISCOUNT_RE = re.compile(
    r"^(?P<label>[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]+?)\s+(?P<amount>\d+(?:,\d+)?)-\s+\d+\s+(?P<code>\d+)\s*$"
)
_VAT_GROUP_RE = re.compile(
    r"(?P<base>\d+(?:\.\d{3})*,\d{2})\s+(?P<group>\d)\s*=\s*(?P<rate>\d+,\d{2})%\s+(?P<vat>\d+(?:\.\d{3})*,\d{2})"
)
_SALE_DATE_RE = re.compile(r"Fecha\s+de\s+venta:\s*(?P<d>\d{2}/\d{2}/\d{2,4})")
_TOTAL_RE = re.compile(r"Total\s+a\s+pagar\s+(?P<t>\d+(?:\.\d{3})*,\d{2})")
_CARD_RE = re.compile(r"Tarjeta\s+(?P<t>\d+(?:\.\d{3})*,\d{2})")
_CASH_RE = re.compile(r"Efectivo\s+(?P<t>\d+(?:\.\d{3})*,\d{2})")
_INVOICE_RE = re.compile(r"Factura:\s*(?P<inv>\S+)")
_TOTAL_DISCOUNTS_RE = re.compile(
    r"Valor\s+total\s+descuentos\s+(?P<t>\d+(?:,\d+)?)-?"
)

_CONFIDENCE_THRESHOLD = 0.85


class MakroParser(ReceiptParser):
    key = "makro"

    def can_parse(self, ocr_text: str) -> float:
        text = ocr_text.lower()
        score = 0.0
        if "makro" in text:
            score += 0.6
        if "makro distribucion mayorista" in text:
            score += 0.2
        if "fecha consumo preferente" in text or "n.cliente" in text.replace(" ", ""):
            score += 0.2
        return min(score, 1.0)

    def parse(self, ocr_text: str) -> ParsedReceipt:
        lines = normalize_ocr_text(ocr_text)
        receipt = ParsedReceipt(supermarket_key=self.key)
        vat_by_group: dict[str, Decimal] = {}
        parsed_lines: list[ParsedLine] = []
        imp_groups: dict[int, str] = {}  # line_number → grupo de impuesto
        current: ParsedLine | None = None

        for raw in lines:
            # 1) Metadatos de cabecera / pie
            if m := _SALE_DATE_RE.search(raw):
                receipt.purchase_date = es_date(m.group("d"))
                continue
            if m := _INVOICE_RE.search(raw):
                receipt.invoice_number = m.group("inv")
                continue
            if m := _TOTAL_RE.search(raw):
                receipt.total_amount = es_decimal(m.group("t"))
                continue
            if m := _CARD_RE.search(raw):
                receipt.payment_method = PaymentMethod.CARD
                continue
            if _CASH_RE.search(raw):
                receipt.payment_method = PaymentMethod.CASH
                continue
            if m := _TOTAL_DISCOUNTS_RE.search(raw):
                receipt.total_discounts = abs(es_decimal(m.group("t")) or Decimal("0"))
                continue
            if m := _VAT_GROUP_RE.search(raw):
                vat_by_group[m.group("group")] = es_decimal(m.group("rate"))
                receipt.total_vat = (receipt.total_vat or Decimal("0")) + (
                    es_decimal(m.group("vat")) or Decimal("0")
                )
                continue

            # 2) Sublíneas del artículo actual (GTIN/lote/caducidad)
            if current is not None:
                if m := _GTIN_LOT_RE.search(raw):
                    current.gtin = m.group("gtin")
                    current.lot_code = m.group("lot")
                    continue
                if m := _EXPIRY_RE.search(raw):
                    current.expiry_date = yymmdd_date(m.group("d"))
                    continue

            # 3) Línea de artículo
            if m := _ARTICLE_RE.match(raw):
                cont = m.group("cont")
                unit = _CONT_TO_UNIT.get(cont, Unit.UNIT)
                prec_ud = es_decimal(m.group("prec_ud")) or Decimal("0")
                cont_p = es_decimal(m.group("cont_p")) or Decimal("1")
                cant = es_decimal(m.group("cant")) or Decimal("1")
                importe = es_decimal(m.group("importe")) or Decimal("0")

                # cantidad real = contenido del bulto × nº de bultos
                quantity = cont_p * cant

                line = ParsedLine(
                    line_number=len(parsed_lines) + 1,
                    raw_text=raw.strip(),
                    description=m.group("desc").strip(),
                    quantity=quantity,
                    unit=unit,
                    unit_price=prec_ud,  # €/kg si KG, €/subunidad si no
                    line_total=importe,
                    vat_rate=None,  # se resuelve al final con vat_by_group
                    promotion_text=(
                        f"DT {m.group('dt')} → {m.group('prec_promo')} €/ud"
                        if m.group("dt")
                        else None
                    ),
                    confidence=self._line_confidence(prec_ud, quantity, importe, cant),
                )
                imp_groups[line.line_number] = m.group("imp")
                parsed_lines.append(line)
                current = line
                continue

            # 4) Descuento global (COMPRA MÁS PAGA MENOS ...)
            if m := _GLOBAL_DISCOUNT_RE.match(raw.strip()):
                amount = abs(es_decimal(m.group("amount")) or Decimal("0"))
                receipt.discount_lines_total += amount
                current = None
                continue

            current = None  # línea no reconocida corta la asociación de sublíneas

        # Resolver IVA por grupo (1=10%, 5=4% en el ticket de referencia)
        for line in parsed_lines:
            group = imp_groups.get(line.line_number)
            if group and group in vat_by_group:
                line.vat_rate = vat_by_group[group]

        receipt.lines = parsed_lines
        self._score(receipt)
        return receipt

    @staticmethod
    def _line_confidence(
        prec_ud: Decimal, quantity: Decimal, importe: Decimal, cant: Decimal
    ) -> float:
        """La línea es fiable si prec_ud × contenido ≈ importe/cant."""
        if cant == 0:
            return 0.3
        expected = prec_ud * (quantity / cant)
        if importe == 0:
            return 0.3
        error = abs(expected - (importe / cant)) / (importe / cant)
        if error <= Decimal("0.01"):
            return 1.0
        if error <= Decimal("0.05"):
            return 0.9
        return 0.6

    def _score(self, receipt: ParsedReceipt) -> None:
        """Calcula confianza global y marca pending_fields.

        Makro: los importes de línea son SIN IVA → se reconcilia contra
        la base imponible (total - IVA), no contra el total a pagar."""
        pending: list[FieldConfidence] = []

        if receipt.purchase_date is None:
            pending.append(
                FieldConfidence(field_path="purchase_date", confidence=0.0)
            )
        if receipt.total_amount is None:
            pending.append(
                FieldConfidence(
                    field_path="total_amount",
                    confidence=0.0,
                    suggestion=str(receipt.lines_sum()),
                )
            )
        else:
            base = receipt.total_amount - (receipt.total_vat or Decimal("0"))
            expected_base = receipt.lines_sum() - receipt.discount_lines_total
            if abs(base - expected_base) > Decimal("0.05"):
                pending.append(
                    FieldConfidence(
                        field_path="total_amount",
                        confidence=0.5,
                        detected_value=str(receipt.total_amount),
                        suggestion=str(
                            expected_base + (receipt.total_vat or Decimal("0"))
                        ),
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
        header_conf = 1.0 if not any(
            p.field_path in ("purchase_date", "total_amount") for p in pending
        ) else 0.6
        receipt.overall_confidence = round(0.6 * line_conf + 0.4 * header_conf, 3)
