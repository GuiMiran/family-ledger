"""Integración: persistencia + normalización con los DOS tickets reales
(Makro 211,87 € y Lidl 151,46 €, ambos del 04/07/2026).

Historia que valida este test:
  1. Ingesta Makro con aliases previos → exact para conocidos,
     fuzzy para variantes ('POLLO PECHUGA VC MC' ≈ 'POLLO PECHUGA'),
     resto a cola de revisión (nunca se pierde el raw_text).
  2. Ingesta Lidl con IA → 'MACARRONS RATLLATS' (catalán) se mapea al
     canónico 'Macarrones' vía AIProposer y el alias queda APRENDIDO.
  3. Re-ingesta Lidl SIN IA → ahora es match exact: la segunda vez es gratis.
  4. price_comparison responde '¿dónde compro más barato?' con datos propios.
"""
import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.application.receipt_ingestion import (
    ReceiptIngestionService,
    price_comparison,
)
from app.domain.normalization.pipeline import AIProductProposer
from app.infrastructure.db.orm import (
    Base, Family, NormalizationReview, Product, ProductAlias,
    ProductPriceHistory, Receipt, ReceiptLine, Supermarket,
)
from app.infrastructure.parsers.lidl import LidlParser
from app.infrastructure.parsers.makro import MakroParser

FIXTURES = Path(__file__).parent / "fixtures"
MAKRO = (FIXTURES / "makro_ticket.txt").read_text(encoding="utf-8")
LIDL = (FIXTURES / "lidl_ticket.txt").read_text(encoding="utf-8")


class FakeAIProposer(AIProductProposer):
    """Simula a Claude resolviendo el cruce catalán/castellano entre cadenas."""

    def __init__(self, mapping: dict[str, uuid.UUID]):
        self.mapping = mapping
        self.calls = 0

    def propose(self, alias_text: str, context: dict):
        self.calls += 1
        if alias_text in self.mapping:
            return {
                "existing_product_id": str(self.mapping[alias_text]),
                "confidence": 0.92,
            }
        return None


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


@pytest.fixture
def seed(session):
    family = Family(name="Familia Miranda", members_count=5)
    makro = Supermarket(name="Makro", parser_key="makro")
    lidl = Supermarket(name="Lidl", parser_key="lidl")
    mercadona = Supermarket(name="Mercadona", parser_key="mercadona")

    macarrones = Product(canonical_name="Macarrones", default_unit="unit")
    espaguetis = Product(canonical_name="Espaguetis", default_unit="unit")
    pechuga = Product(
        canonical_name="Pechuga de pollo", default_unit="kg",
        typical_shelf_life_days=3, is_freezable=True,
    )
    session.add_all([family, makro, lidl, mercadona, macarrones, espaguetis, pechuga])
    session.flush()

    # aliases "aprendidos" en compras anteriores
    session.add_all([
        ProductAlias(product_id=macarrones.id, supermarket_id=makro.id,
                     alias_text="MACARRON PLUMA 3 ARO 5KG", match_type="manual"),
        ProductAlias(product_id=espaguetis.id, supermarket_id=makro.id,
                     alias_text="SPAGHETTI ARO 5KG", match_type="manual"),
        ProductAlias(product_id=pechuga.id, supermarket_id=None,  # global
                     alias_text="POLLO PECHUGA", match_type="manual"),
    ])
    session.flush()
    return {
        "family": family, "makro": makro, "lidl": lidl,
        "macarrones": macarrones, "espaguetis": espaguetis, "pechuga": pechuga,
    }


def test_makro_ingestion_exact_fuzzy_and_review(session, seed):
    parsed = MakroParser().parse(MAKRO)
    svc = ReceiptIngestionService(session)
    res = svc.ingest(parsed, seed["family"].id)

    assert res.lines_total == 17
    # macarrones + espaguetis (alias previo) = 2 exact.
    # 1ª línea de pollo → fuzzy (≈'POLLO PECHUGA') y APRENDE el alias;
    # las líneas 2 y 3 del mismo ticket ya entran como exact → 4 exact, 1 fuzzy.
    assert res.matched_exact == 4
    assert res.matched_fuzzy == 1
    assert res.sent_to_review == 12    # el resto, con raw_text conservado
    # el alias fuzzy se aprende UNA sola vez (dedupe)
    assert res.aliases_learned == 1

    receipt = session.get(Receipt, res.receipt_id)
    assert receipt.status == "confirmed"          # cuadró al céntimo
    assert receipt.total_amount == Decimal("211.87")

    # la caducidad impresa del jamón llega a la BD
    jamon = session.execute(
        select(ReceiptLine).where(ReceiptLine.description.like("%JAMON%"))
    ).scalar_one()
    assert jamon.expiry_date == date(2027, 1, 17)

    # 5 puntos de precio: 2 exact + 3 fuzzy con unit_price
    assert res.price_points_created == 5
    pechuga_prices = session.execute(
        select(ProductPriceHistory).where(
            ProductPriceHistory.product_id == seed["pechuga"].id
        )
    ).scalars().all()
    assert len(pechuga_prices) == 3
    assert all(p.unit_price == Decimal("5.3900") for p in pechuga_prices)
    assert all(p.unit == "kg" for p in pechuga_prices)


def test_lidl_ai_normalization_then_free_second_time(session, seed):
    # 1ª ingesta Lidl: la IA resuelve el cruce catalán → castellano
    ai = FakeAIProposer({
        "MACARRONS RATLLATS": seed["macarrones"].id,
        "SPAGHETTI INTEGRAL": seed["espaguetis"].id,
    })
    parsed = LidlParser().parse(LIDL)
    res1 = ReceiptIngestionService(session, ai_proposer=ai).ingest(
        parsed, seed["family"].id
    )
    assert res1.matched_ai == 2
    assert res1.aliases_learned == 2
    assert ai.calls > 0

    # 2ª ingesta (misma compra recurrente): SIN IA → ahora es exact.
    res2 = ReceiptIngestionService(session).ingest(parsed, seed["family"].id)
    matched_before_review = res2.matched_exact
    assert matched_before_review >= 2  # macarrons + spaghetti ya aprendidos
    mac_line = session.execute(
        select(ReceiptLine)
        .where(ReceiptLine.description == "MACARRONS RATLLATS")
        .order_by(ReceiptLine.created_at.desc())
    ).scalars().first()
    assert mac_line.match_type == "exact"


def test_price_comparison_own_data(session, seed):
    """'¿Dónde compro más barato los macarrones?' — con datos propios,
    sin APIs de terceros. (Nota: unidades distintas se agrupan aparte;
    el paquete Makro de 5 kg y el de Lidl son formatos diferentes.)"""
    ReceiptIngestionService(session).ingest(
        MakroParser().parse(MAKRO), seed["family"].id
    )
    ai = FakeAIProposer({"MACARRONS RATLLATS": seed["macarrones"].id})
    ReceiptIngestionService(session, ai_proposer=ai).ingest(
        LidlParser().parse(LIDL), seed["family"].id
    )
    comp = price_comparison(session, seed["macarrones"].id, seed["family"].id)
    markets = {c["supermarket"]: c for c in comp}
    assert "Makro" in markets and "Lidl" in markets
    assert markets["Makro"]["avg_unit_price"] == Decimal("5.3900")  # pack 5 kg
    assert markets["Lidl"]["avg_unit_price"] == Decimal("1.0900")   # pack 500 g
    # ordenado de más barato a más caro
    assert comp[0]["supermarket"] == "Lidl"


def test_review_queue_preserves_everything(session, seed):
    ReceiptIngestionService(session).ingest(
        MakroParser().parse(MAKRO), seed["family"].id
    )
    reviews = session.execute(select(NormalizationReview)).scalars().all()
    assert len(reviews) == 12
    assert all(r.status == "pending" for r in reviews)
    assert any("HEINZ" in r.alias_text for r in reviews)
