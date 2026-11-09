"""Wholly fictional Mercadona-format fixture; no household case data."""
from datetime import date, time
from decimal import Decimal
from pathlib import Path

import pytest

from app.infrastructure.parsers.mercadona import MercadonaParser
from app.infrastructure.parsers.registry import ParserRegistry
from app.domain.receipts.models import Unit

FIXTURE = (Path(__file__).parent / "fixtures" / "mercadona_ticket.txt").read_text(
    encoding="utf-8"
)


@pytest.fixture
def parsed():
    return MercadonaParser().parse(FIXTURE)


def test_registry_detects_mercadona():
    parser = ParserRegistry().detect(FIXTURE)
    assert parser is not None and parser.key == "mercadona"


def test_header(parsed):
    assert parsed.purchase_date == date(2030, 1, 2)
    assert parsed.purchase_time == time(10, 15)
    assert parsed.total_amount == Decimal("32.24")
    assert parsed.total_vat == Decimal("1.94")
    assert parsed.payment_method == "card"
    assert parsed.invoice_number == "0000-000-000001"


def test_lines_count(parsed):
    assert len(parsed.lines) == 6


def test_unit_line_without_price(parsed):
    """Cantidad 1 → columna P.Unit vacia → unit_price = total."""
    alpha = next(l for l in parsed.lines if "ALFA" in l.description)
    assert alpha.quantity == Decimal("1")
    assert alpha.line_total == Decimal("7.75")
    assert alpha.unit_price == Decimal("7.75")


def test_unit_line_with_price(parsed):
    beta = next(l for l in parsed.lines if "BETA" in l.description)
    assert beta.quantity == Decimal("3")
    assert beta.unit_price == Decimal("1.65")
    assert beta.line_total == Decimal("4.95")


def test_weight_split_two_lines(parsed):
    """Synthetic weight on its own row precedes description and amounts."""
    epsilon = next(l for l in parsed.lines if "EPSILON" in l.description)
    assert epsilon.unit == Unit.KG
    assert epsilon.quantity == Decimal("0.720")
    assert epsilon.unit_price == Decimal("4.50")
    assert epsilon.line_total == Decimal("3.24")


def test_weight_single_line(parsed):
    zeta = next(l for l in parsed.lines if "ZETA" in l.description)
    assert zeta.unit == Unit.KG
    assert zeta.quantity == Decimal("1.125")
    assert zeta.unit_price == Decimal("6.00")
    assert zeta.line_total == Decimal("6.75")


def test_totals_reconcile(parsed):
    assert parsed.lines_sum() == parsed.total_amount
    critical = [p for p in parsed.pending_fields
                if p.field_path in ("total_amount", "purchase_date")]
    assert critical == []
    assert parsed.overall_confidence >= 0.9
