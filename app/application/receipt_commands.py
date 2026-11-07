# @spectra BR-009
# @spectra INV-005
# @spectra EVT-001
# @spectra WF-004
"""Validation and transactional projections for receipt commands."""
import hashlib
import json
import math
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.receipts.models import ParsedReceipt, FieldConfidence
from app.infrastructure.db.orm import Receipt, ReceiptEvent, InventoryEntry


def validated_receipt(value: ParsedReceipt) -> ParsedReceipt:
    parsed = value.model_copy(deep=True)
    if not parsed.lines or len(parsed.lines) > 1000:
        raise ValueError("A receipt needs 1–1000 lines")
    if len({x.line_number for x in parsed.lines}) != len(parsed.lines):
        raise ValueError("Line numbers must be unique")
    for line in parsed.lines:
        if not 1 <= line.line_number <= 32767 or len(line.description) > 2000 or len(line.raw_text) > 4000:
            raise ValueError("Invalid line number or text length")
        for amount in (line.quantity, line.line_total, line.discount_amount, line.unit_price):
            if amount is not None and (not amount.is_finite() or amount < 0):
                raise ValueError("Receipt values must be finite and nonnegative")
        if line.quantity <= 0:
            raise ValueError("Quantity must be positive")
        _storage_decimal(line.quantity, 10, 3)
        _storage_decimal(line.line_total, 10, 2)
        _storage_decimal(line.discount_amount, 10, 2)
        _storage_decimal(line.unit_price, 10, 4)
        _storage_decimal(line.vat_rate, 4, 2)
        if not math.isfinite(line.confidence) or not 0 <= line.confidence <= 1:
            raise ValueError("Confidence must be between zero and one")
    for amount in (parsed.total_amount, parsed.total_vat, parsed.total_discounts, parsed.discount_lines_total):
        if amount is not None and (not amount.is_finite() or amount < 0):
            raise ValueError("Totals must be finite and nonnegative")
        _storage_decimal(amount, 10, 2)
    if parsed.total_amount is not None and parsed.total_vat is not None and parsed.total_vat > parsed.total_amount:
        raise ValueError("VAT cannot exceed the paid total")
    if not math.isfinite(parsed.overall_confidence) or not 0 <= parsed.overall_confidence <= 1:
        raise ValueError("Confidence must be between zero and one")
    _storage_decimal(Decimal(str(parsed.overall_confidence)), 4, 3)
    fields = {f.field_path: f for f in parsed.pending_fields}
    if parsed.purchase_date is None:
        fields["purchase_date"] = FieldConfidence(field_path="purchase_date", confidence=0)
    else:
        fields.pop("purchase_date", None)
    if parsed.total_amount is None:
        fields["total_amount"] = FieldConfidence(field_path="total_amount", confidence=0)
    else:
        expected = parsed.lines_sum() - parsed.discount_lines_total
        if parsed.supermarket_key == "makro":
            if parsed.total_vat is None:
                fields["total_vat"] = FieldConfidence(field_path="total_vat", confidence=0)
            else:
                expected += parsed.total_vat
                fields.pop("total_vat", None)
        comparable = parsed.supermarket_key != "makro" or parsed.total_vat is not None
        difference = abs(expected - parsed.total_amount)
        if expected < 0 or (comparable and difference > Decimal("0.05")):
            raise ValueError("Receipt totals do not reconcile")
        if comparable and difference != 0:
            fields["total_amount"] = FieldConfidence(field_path="total_amount", confidence=0.5,
                                                     detected_value=str(parsed.total_amount), suggestion=str(expected))
        else:
            fields.pop("total_amount", None)
    for line in parsed.lines:
        if line.confidence < 0.9:
            key = f"lines[{line.line_number - 1}].line_total"
            fields[key] = FieldConfidence(field_path=key, confidence=line.confidence)
    parsed.pending_fields = list(fields.values())
    return parsed


def _storage_decimal(value, precision, scale):
    if value is None:
        return
    quantum = Decimal(1).scaleb(-scale)
    if (not value.is_finite() or value < 0 or value >= Decimal(10) ** (precision - scale)
            or value.quantize(quantum) != value):
        raise ValueError("A numeric value exceeds its storage precision or range")


def request_digest(action: str, parsed: ParsedReceipt) -> str:
    body = json.dumps({"action": action, "receipt": parsed.model_dump(mode="json")},
                      sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(body.encode()).hexdigest()


def project_confirmed(session: Session, receipt: Receipt) -> None:
    """Outbox fact and purchase projection commit together with the receipt."""
    if receipt.status != "confirmed":
        return
    existing = session.execute(select(ReceiptEvent).where(
        ReceiptEvent.receipt_id == receipt.id, ReceiptEvent.event_type == "ReceiptConfirmed"
    )).scalar_one_or_none()
    if existing:
        return
    event = ReceiptEvent(family_id=receipt.family_id, receipt_id=receipt.id,
                         event_type="ReceiptConfirmed", payload={"receipt_id": str(receipt.id)}, processed=False)
    session.add(event)
    for line in receipt.lines:
        session.add(InventoryEntry(family_id=receipt.family_id, receipt_line_id=line.id,
                                  product_id=line.product_id, description=line.description,
                                  quantity=line.quantity, unit=line.unit, expiry_date=line.expiry_date))
    session.flush()
    event.processed = True
