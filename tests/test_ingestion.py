"""Synthetic ingestion: exact/fuzzy matching, review, learned aliases and prices.

Fixtures are wholly fictional; no family purchase history is public test data.
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
    """Deterministic synthetic proposer; no external AI calls."""

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
    family = Family(name="Synthetic Test Household", members_count=2)
    makro = Supermarket(name="Makro", parser_key="makro")
    lidl = Supermarket(name="Lidl", parser_key="lidl")
    mercadona = Supermarket(name="Mercadona", parser_key="mercadona")

    alpha = Product(canonical_name="Synthetic Alpha", default_unit="unit")
    beta = Product(canonical_name="Synthetic Beta", default_unit="unit")
    delta = Product(
        canonical_name="Synthetic Delta", default_unit="kg",
        typical_shelf_life_days=3, is_freezable=True,
    )
    session.add_all([family, makro, lidl, mercadona, alpha, beta, delta])
    session.flush()

    # aliases "aprendidos" en compras anteriores
    session.add_all([
        ProductAlias(product_id=alpha.id, supermarket_id=makro.id,
                     alias_text="ORBITA QX ALFA", match_type="manual"),
        ProductAlias(product_id=beta.id, supermarket_id=makro.id,
                     alias_text="VECTOR ZY BETA", match_type="manual"),
        ProductAlias(product_id=delta.id, supermarket_id=None,  # global
                     alias_text="SINTETICO DELTA", match_type="manual"),
    ])
    session.flush()
    return {
        "family": family, "makro": makro, "lidl": lidl,
        "alpha": alpha, "beta": beta, "delta": delta,
    }


def test_makro_ingestion_exact_fuzzy_and_review(session, seed):
    parsed = MakroParser().parse(MAKRO)
    svc = ReceiptIngestionService(session)
    res = svc.ingest(parsed, seed["family"].id)

    assert res.lines_total == 8
    # Two known aliases, then one fuzzy delta alias learned for its next two rows.
    assert res.matched_exact == 4
    assert res.matched_fuzzy == 1
    assert res.sent_to_review == 3    # el resto, con raw_text conservado
    # el alias fuzzy se aprende UNA sola vez (dedupe)
    assert res.aliases_learned == 1

    receipt = session.get(Receipt, res.receipt_id)
    assert receipt.status == "confirmed"          # cuadró al céntimo
    assert receipt.total_amount == Decimal("36.12")

    # Synthetic printed expiry metadata survives persistence
    gamma = session.execute(
        select(ReceiptLine).where(ReceiptLine.description.like("%GAMMA%"))
    ).scalar_one()
    assert gamma.expiry_date == date(2030, 2, 15)

    # Five price points: two known aliases and three weighted delta rows
    assert res.price_points_created == 5
    delta_prices = session.execute(
        select(ProductPriceHistory).where(
            ProductPriceHistory.product_id == seed["delta"].id
        )
    ).scalars().all()
    assert len(delta_prices) == 3
    assert all(p.unit_price == Decimal("8.0000") for p in delta_prices)
    assert all(p.unit == "kg" for p in delta_prices)


def test_lidl_ai_normalization_then_free_second_time(session, seed):
    # First ingestion resolves fictional cross-store aliases with a deterministic stub
    ai = FakeAIProposer({
        "ALFA CATALITIC QX": seed["alpha"].id,
        "BETA HELICOIDAL ZY": seed["beta"].id,
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
    assert matched_before_review >= 2  # both synthetic aliases have been learned
    alpha_line = session.execute(
        select(ReceiptLine)
        .where(ReceiptLine.description == "ALFA CATALITIC QX")
        .order_by(ReceiptLine.created_at.desc())
    ).scalars().first()
    assert alpha_line.match_type == "exact"


def test_price_comparison_own_data(session, seed):
    """Compare only synthetic historical unit prices within the family."""
    ReceiptIngestionService(session).ingest(
        MakroParser().parse(MAKRO), seed["family"].id
    )
    ai = FakeAIProposer({"ALFA CATALITIC QX": seed["alpha"].id})
    ReceiptIngestionService(session, ai_proposer=ai).ingest(
        LidlParser().parse(LIDL), seed["family"].id
    )
    comp = price_comparison(session, seed["alpha"].id, seed["family"].id)
    markets = {c["supermarket"]: c for c in comp}
    assert "Makro" in markets and "Lidl" in markets
    assert markets["Makro"]["avg_unit_price"] == Decimal("1.8000")
    assert markets["Lidl"]["avg_unit_price"] == Decimal("2.7500")
    # ordenado de más barato a más caro
    assert comp[0]["supermarket"] == "Makro"


def test_review_queue_preserves_everything(session, seed):
    ReceiptIngestionService(session).ingest(
        MakroParser().parse(MAKRO), seed["family"].id
    )
    reviews = session.execute(select(NormalizationReview)).scalars().all()
    assert len(reviews) == 3
    assert all(r.status == "pending" for r in reviews)
    assert any("ZETA" in r.alias_text for r in reviews)
