"""Tests del parser Lidl contra el ticket real de referencia
(El Prat de Llobregat, 04/07/2026, 151,46 EUR, 48 lineas)."""
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
    assert parsed.purchase_date == date(2026, 7, 4)
    assert parsed.purchase_time == time(19, 59)
    assert parsed.total_amount == Decimal("151.46")
    assert parsed.payment_method == "card"
    assert parsed.total_discounts == Decimal("2.18")


def test_all_lines_detected(parsed):
    assert len(parsed.lines) == 48


def test_multi_unit_line(parsed):
    mac = next(l for l in parsed.lines if "MACARRONS" in l.description)
    assert mac.quantity == Decimal("2")
    assert mac.unit_price == Decimal("1.09")
    assert mac.line_total == Decimal("2.18")


def test_weight_subline_converts_to_kg(parsed):
    filet = next(l for l in parsed.lines if "ANOLL" in l.description)
    assert filet.unit == Unit.KG
    assert filet.quantity == Decimal("0.472")
    assert filet.unit_price == Decimal("17.59")
    assert filet.line_total == Decimal("8.30")


def test_all_weight_items(parsed):
    kg_items = [l for l in parsed.lines if l.unit == Unit.KG]
    assert len(kg_items) == 5  # anoll, alberginia, llom, banana, carbasso


def test_discount_sublines_attached(parsed):
    xampu = next(l for l in parsed.lines if "H&S" in l.description)
    assert xampu.discount_amount == Decimal("1.10")
    gel = next(l for l in parsed.lines if "GEL DE BANY" in l.description)
    assert gel.discount_amount == Decimal("0.30")
    assert gel.promotion_text and "LIDL PLUS" in gel.promotion_text.upper()
    assert parsed.discount_lines_total == Decimal("2.18")


def test_vat_letters_resolved(parsed):
    pa = next(l for l in parsed.lines if l.description == "PA RATLLAT")
    mac = next(l for l in parsed.lines if "MACARRONS" in l.description)
    cola = next(l for l in parsed.lines if l.description == "COLA 2L")
    assert pa.vat_rate == Decimal("4")     # A
    assert mac.vat_rate == Decimal("10")   # B
    assert cola.vat_rate == Decimal("21")  # C


def test_totals_reconcile(parsed):
    """suma lineas (153,64) - descuentos (2,18) == TOTAL (151,46)."""
    assert parsed.lines_sum() == Decimal("153.64")
    assert parsed.lines_sum() - parsed.discount_lines_total == parsed.total_amount
    critical = [p for p in parsed.pending_fields
                if p.field_path in ("total_amount", "purchase_date")]
    assert critical == []
    assert parsed.overall_confidence >= 0.9
