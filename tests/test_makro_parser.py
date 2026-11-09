"""Wholly fictional receipts cover Makro format, arithmetic and metadata."""
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.infrastructure.parsers.makro import MakroParser
from app.infrastructure.parsers.registry import ParserRegistry
from app.domain.receipts.models import Unit

FIXTURE = (Path(__file__).parent / "fixtures" / "makro_ticket.txt").read_text(
    encoding="utf-8"
)


@pytest.fixture
def parsed():
    return MakroParser().parse(FIXTURE)


def test_registry_detects_makro():
    parser = ParserRegistry().detect(FIXTURE)
    assert parser is not None and parser.key == "makro"


def test_header(parsed):
    assert parsed.purchase_date == date(2030, 1, 2)
    assert parsed.total_amount == Decimal("36.12")
    assert parsed.total_vat == Decimal("2.72")
    assert parsed.payment_method == "card"
    assert parsed.invoice_number == "SYNTHETIC-MAKRO-001"


def test_all_lines_detected(parsed):
    # Eight wholly synthetic article rows
    assert len(parsed.lines) == 8


def test_weighted_batches(parsed):
    """Three fictional weighted batches remain distinct kg rows."""
    batches = [l for l in parsed.lines if "SINTETICO DELTA" in l.description]
    assert len(batches) == 3
    assert all(l.unit == Unit.KG for l in batches)
    assert all(l.unit_price == Decimal("8.000") for l in batches)
    assert sorted(l.quantity for l in batches) == [
        Decimal("0.625"),
        Decimal("0.750"),
        Decimal("0.875"),
    ]


def test_expiry_date_from_ticket(parsed):
    """Makro imprime la caducidad → va directa al inventario."""
    gamma = next(l for l in parsed.lines if "GAMMA" in l.description)
    assert gamma.expiry_date == date(2030, 2, 15)
    assert gamma.gtin == "00000000000001"
    assert gamma.lot_code == "SYNTHETIC-LOT-A"


def test_multi_quantity_line(parsed):
    """Two packs of two subunits produce quantity four, without double counting."""
    alpha = next(l for l in parsed.lines if "ALFA" in l.description)
    assert alpha.quantity == Decimal("4")
    assert alpha.line_total == Decimal("7.20")


def test_vat_groups_resolved(parsed):
    """Grupo 1 = 10%, grupo 5 = 4%."""
    gamma = next(l for l in parsed.lines if "GAMMA" in l.description)
    beta = next(l for l in parsed.lines if "BETA" in l.description)
    assert gamma.vat_rate == Decimal("4.00")
    assert beta.vat_rate == Decimal("10.00")


def test_promotion_detected(parsed):
    promoted = [l for l in parsed.lines if "SINTETICO DELTA" in l.description and l.promotion_text]
    assert len(promoted) == 2
    assert all(l.promotion_text and "90701" in l.promotion_text for l in promoted)


def test_global_discount(parsed):
    assert parsed.discount_lines_total == Decimal("1.00")
    assert parsed.total_discounts == Decimal("1.00")


def test_totals_reconcile_no_pending(parsed):
    """Gross total minus VAT equals synthetic net lines minus discount."""
    assert parsed.lines_sum() == Decimal("34.40")
    critical = [p for p in parsed.pending_fields
                if p.field_path in ("total_amount", "purchase_date")]
    assert critical == []
    assert parsed.overall_confidence >= 0.9
