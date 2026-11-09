"""Wholly fictional Lidl format cases: units, weights, discounts and VAT."""
from datetime import date, time
from decimal import Decimal
from pathlib import Path

import pytest

from app.domain.receipts.models import Unit
from app.infrastructure.parsers.lidl import LidlParser
from app.infrastructure.parsers.registry import ParserRegistry

FIXTURE = (Path(__file__).parent / "fixtures" / "lidl_ticket.txt").read_text(
    encoding="utf-8"
)


@pytest.fixture
def parsed():
    return LidlParser().parse(FIXTURE)


def test_registry_detects_lidl():
    parser = ParserRegistry().detect(FIXTURE)
    assert parser is not None and parser.key == "lidl"


def test_header(parsed):
    assert parsed.purchase_date == date(2030, 1, 2)
    assert parsed.purchase_time == time(12, 34)
    assert parsed.total_amount == Decimal("28.65")
    assert parsed.payment_method == "card"
    assert parsed.total_discounts == Decimal("0.80")


def test_all_lines_detected(parsed):
    assert len(parsed.lines) == 6


def test_multi_unit_line(parsed):
    alpha = next(l for l in parsed.lines if "ALFA" in l.description)
    assert alpha.quantity == Decimal("3")
    assert alpha.unit_price == Decimal("2.75")
    assert alpha.line_total == Decimal("8.25")


def test_weight_subline_converts_to_kg(parsed):
    delta = next(l for l in parsed.lines if "DELTA" in l.description)
    assert delta.unit == Unit.KG
    assert delta.quantity == Decimal("0.650")
    assert delta.unit_price == Decimal("10.00")
    assert delta.line_total == Decimal("6.50")


def test_all_weight_items(parsed):
    kg_items = [l for l in parsed.lines if l.unit == Unit.KG]
    assert len(kg_items) == 2  # synthetic DELTA and ETA


def test_discount_sublines_attached(parsed):
    epsilon = next(l for l in parsed.lines if "EPSILON" in l.description)
    assert epsilon.discount_amount == Decimal("0.55")
    zeta = next(l for l in parsed.lines if "ZETA" in l.description)
    assert zeta.discount_amount == Decimal("0.25")
    assert zeta.promotion_text and "LIDL PLUS" in zeta.promotion_text.upper()
    assert parsed.discount_lines_total == Decimal("0.80")


def test_vat_letters_resolved(parsed):
    beta = next(l for l in parsed.lines if l.description == "BETA HELICOIDAL ZY")
    alpha = next(l for l in parsed.lines if "ALFA" in l.description)
    epsilon = next(l for l in parsed.lines if l.description == "EPSILON RADIANT VX")
    assert beta.vat_rate == Decimal("4")     # A
    assert alpha.vat_rate == Decimal("10")   # B
    assert epsilon.vat_rate == Decimal("21")  # C


def test_totals_reconcile(parsed):
    """Synthetic gross lines less two attached discounts reconcile exactly."""
    assert parsed.lines_sum() == Decimal("29.45")
    assert parsed.lines_sum() - parsed.discount_lines_total == parsed.total_amount
    critical = [p for p in parsed.pending_fields
                if p.field_path in ("total_amount", "purchase_date")]
    assert critical == []
    assert parsed.overall_confidence >= 0.9
