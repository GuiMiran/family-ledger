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
    assert parsed.purchase_date == date(2026, 7, 4)
    assert parsed.purchase_time == time(18, 23)
    assert parsed.total_amount == Decimal("22.12")
    assert parsed.total_vat == Decimal("1.40")
    assert parsed.payment_method == "card"
    assert parsed.invoice_number == "2308-013-141414"


def test_lines_count(parsed):
    assert len(parsed.lines) == 6


def test_unit_line_without_price(parsed):
    """Cantidad 1 → columna P.Unit vacia → unit_price = total."""
    leche = next(l for l in parsed.lines if "LECHE" in l.description)
    assert leche.quantity == Decimal("1")
    assert leche.line_total == Decimal("5.10")
    assert leche.unit_price == Decimal("5.10")


def test_unit_line_with_price(parsed):
    galleta = next(l for l in parsed.lines if "GALLETA" in l.description)
    assert galleta.quantity == Decimal("2")
    assert galleta.unit_price == Decimal("1.22")
    assert galleta.line_total == Decimal("2.44")


def test_weight_split_two_lines(parsed):
    """'0,536 kg' en renglon propio + 'PLATANO 2,29 1,23' debajo."""
    platano = next(l for l in parsed.lines if "PLATANO" in l.description)
    assert platano.unit == Unit.KG
    assert platano.quantity == Decimal("0.536")
    assert platano.unit_price == Decimal("2.29")
    assert platano.line_total == Decimal("1.23")


def test_weight_single_line(parsed):
    pollo = next(l for l in parsed.lines if "POLLO" in l.description)
    assert pollo.unit == Unit.KG
    assert pollo.quantity == Decimal("1.240")
    assert pollo.unit_price == Decimal("3.95")
    assert pollo.line_total == Decimal("4.90")


def test_totals_reconcile(parsed):
    assert parsed.lines_sum() == parsed.total_amount
    critical = [p for p in parsed.pending_fields
                if p.field_path in ("total_amount", "purchase_date")]
    assert critical == []
    assert parsed.overall_confidence >= 0.9
