"""Tests del parser Makro contra el ticket real de referencia
(Makro Barcelona, 04/07/2026, 211,87 EUR)."""
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
    assert parsed.purchase_date == date(2026, 7, 4)
    assert parsed.total_amount == Decimal("211.87")
    assert parsed.total_vat == Decimal("16.98")
    assert parsed.payment_method == "card"
    assert parsed.invoice_number == "1/0(002)0205/(2026)000125"


def test_all_lines_detected(parsed):
    # 17 lineas de articulo en el ticket real
    assert len(parsed.lines) == 17


def test_weight_line_pollo(parsed):
    """Tres lotes de pechuga con pesos distintos → tres lineas kg."""
    pollos = [l for l in parsed.lines if "POLLO PECHUGA" in l.description]
    assert len(pollos) == 3
    assert all(l.unit == Unit.KG for l in pollos)
    assert all(l.unit_price == Decimal("5.390") for l in pollos)
    assert sorted(l.quantity for l in pollos) == [
        Decimal("2.188"),
        Decimal("2.308"),
        Decimal("2.370"),
    ]


def test_expiry_date_from_ticket(parsed):
    """Makro imprime la caducidad → va directa al inventario."""
    jamon = next(l for l in parsed.lines if "JAMON" in l.description)
    assert jamon.expiry_date == date(2027, 1, 17)
    assert jamon.gtin == "08414892328944"
    assert jamon.lot_code == "261660625"


def test_multi_quantity_line(parsed):
    """ARROZ LARGO MC 5KG: 2 bultos de 1 → cantidad 2, importe 12,10."""
    arroz = next(l for l in parsed.lines if "ARROZ" in l.description)
    assert arroz.quantity == Decimal("2")
    assert arroz.line_total == Decimal("12.10")


def test_vat_groups_resolved(parsed):
    """Grupo 1 = 10%, grupo 5 = 4%."""
    jamon = next(l for l in parsed.lines if "JAMON" in l.description)
    huevos = next(l for l in parsed.lines if "HVO" in l.description)
    assert jamon.vat_rate == Decimal("10.00")
    assert huevos.vat_rate == Decimal("4.00")


def test_promotion_detected(parsed):
    picadas = [l for l in parsed.lines if "PICADA" in l.description]
    assert len(picadas) == 2
    assert all(l.promotion_text and "84240" in l.promotion_text for l in picadas)


def test_global_discount(parsed):
    assert parsed.discount_lines_total == Decimal("1.29")
    assert parsed.total_discounts == Decimal("1.42")


def test_totals_reconcile_no_pending(parsed):
    """base imponible (211,87-16,98) == suma lineas (196,18) - dto (1,29)."""
    assert parsed.lines_sum() == Decimal("196.18")
    critical = [p for p in parsed.pending_fields
                if p.field_path in ("total_amount", "purchase_date")]
    assert critical == []
    assert parsed.overall_confidence >= 0.9
