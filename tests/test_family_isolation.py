"""Independent synthetic challenges for normalization and price privacy."""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.application.receipt_ingestion import ReceiptIngestionService, price_comparison
from app.domain.normalization.pipeline import AIProductProposer
from app.domain.receipts.models import FieldConfidence, ParsedLine, ParsedReceipt
from app.infrastructure.db.orm import (
    Base, Family, NormalizationReview, Product, ProductAlias,
    ProductPriceHistory, Receipt, ReceiptLine, Supermarket,
)
from app.infrastructure.normalization.matchers import ExactMatcher, FuzzyMatcher


@pytest.fixture
def data():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        a, b = Family(name="Synthetic A"), Family(name="Synthetic B")
        market = Supermarket(name="Synthetic market", parser_key="synthetic")
        other = Supermarket(name="Other market", parser_key="other")
        session.add_all([a, b, market, other]); session.flush()
        private = Product(family_id=a.id, canonical_name="Private A", default_unit="unit")
        shared = Product(canonical_name="Shared product", default_unit="unit")
        session.add_all([private, shared]); session.flush()
        yield session, a, b, market, other, private, shared


def add_alias(session, product, text, market=None, owner=None):
    alias = ProductAlias(product_id=product.id, family_id=owner.id if owner else None,
                         alias_text=text, supermarket_id=market.id if market else None,
                         match_type="manual")
    session.add(alias); session.flush()
    return alias


def parsed(text="Unknown purchase", amount="2.35", pending=False):
    receipt = ParsedReceipt(
        supermarket_key="synthetic", purchase_date=date(2026, 11, 7),
        total_amount=Decimal(amount),
        lines=[ParsedLine(line_number=1, raw_text="raw:" + text,
                          description=text, quantity=Decimal("1"),
                          line_total=Decimal(amount), unit_price=Decimal(amount))],
    )
    if pending:
        receipt.pending_fields = [FieldConfidence(field_path="total_amount", confidence=0)]
    return receipt


def test_exact_requires_both_product_and_alias_visibility(data):
    session, a, b, market, _, private, shared = data
    # Even an alias marked global cannot expose its privately owned product.
    add_alias(session, private, "PRIVATE ALIAS", market)
    add_alias(session, shared, "OWN ALIAS ON SHARED PRODUCT", market, a)
    add_alias(session, shared, "SHARED ALIAS", market)
    matcher = ExactMatcher(session)
    assert matcher.match("PRIVATE ALIAS", market.id, b.id) is None
    assert matcher.match("PRIVATE ALIAS", market.id) is None
    assert matcher.match("PRIVATE ALIAS", market.id, a.id).product_id == private.id
    assert matcher.match("OWN ALIAS ON SHARED PRODUCT", market.id, b.id) is None
    assert matcher.match("OWN ALIAS ON SHARED PRODUCT", market.id) is None
    assert matcher.match("SHARED ALIAS", market.id).product_id == shared.id


def test_fuzzy_cannot_use_other_families_or_other_markets(data):
    session, a, b, market, other, private, shared = data
    add_alias(session, private, "PRIVATE SPECIAL APPLES", market)
    add_alias(session, shared, "SECOND MARKET PEARS", other)
    add_alias(session, shared, "OWN SPECIAL BANANAS", market, a)
    matcher = FuzzyMatcher(session)
    assert matcher.match("PRIVATE SPECIAL APPLE", market.id, b.id) is None
    assert matcher.match("PRIVATE SPECIAL APPLE", market.id, a.id).product_id == private.id
    assert matcher.match("SECOND MARKET PEAR", market.id, b.id) is None
    assert matcher.match("OWN SPECIAL BANANA", market.id, b.id) is None


def test_specific_market_then_own_family_precedence(data):
    session, a, b, market, _, private, shared = data
    own = Product(family_id=b.id, canonical_name="Own B", default_unit="unit")
    session.add(own); session.flush()
    add_alias(session, own, "PRIORITY", None, b)
    add_alias(session, shared, "PRIORITY", market)
    matcher = ExactMatcher(session)
    assert matcher.match("PRIORITY", market.id, b.id).product_id == shared.id
    add_alias(session, own, "PRIORITY", market, b)
    assert matcher.match("PRIORITY", market.id, b.id).product_id == own.id
    assert matcher.match("PRIORITY", market.id, a.id).product_id == shared.id


class Proposal(AIProductProposer):
    def __init__(self, payload):
        self.payload = payload
        self.contexts = []

    def propose(self, alias_text, context):
        self.contexts.append(context)
        return self.payload


@pytest.mark.parametrize("invalid_id", ["private", "malformed"])
def test_ai_private_or_invalid_product_is_rejected_without_review_leak(data, invalid_id):
    session, a, b, market, _, private, _ = data
    proposed_id = str(private.id) if invalid_id == "private" else "not-a-uuid"
    ai = Proposal({"existing_product_id": proposed_id, "confidence": 0.99,
                   "private_note": "provider response must not enter family B review"})
    result = ReceiptIngestionService(session, ai).ingest(parsed(), b.id)
    line = session.execute(select(ReceiptLine).where(ReceiptLine.receipt_id == result.receipt_id)).scalar_one()
    review = session.execute(select(NormalizationReview).where(NormalizationReview.receipt_line_id == line.id)).scalar_one()
    assert line.product_id is None and result.matched_ai == 0
    assert review.ai_proposal is None
    assert ai.contexts == [{"supermarket_id": str(market.id), "family_id": str(b.id)}]
    assert session.execute(select(ProductAlias)).scalars().all() == []


def test_learned_alias_is_private_even_for_a_shared_product(data):
    session, a, b, market, _, _, shared = data
    ai = Proposal({"existing_product_id": str(shared.id), "confidence": 0.95})
    one = ReceiptIngestionService(session, ai).ingest(parsed("FAMILY CUSTOM ALIAS"), a.id)
    assert one.aliases_learned == 1
    alias = session.execute(select(ProductAlias)).scalar_one()
    assert alias.family_id == a.id and alias.product_id == shared.id
    assert ExactMatcher(session).match("FAMILY CUSTOM ALIAS", market.id, b.id) is None
    assert FuzzyMatcher(session).match("FAMILY CUSTOM ALIA", market.id, b.id) is None
    again = ReceiptIngestionService(session).ingest(parsed("FAMILY CUSTOM ALIAS"), a.id)
    assert again.matched_exact == 1 and again.aliases_learned == 0
    other = ReceiptIngestionService(session, ai).ingest(parsed("FAMILY CUSTOM ALIAS"), b.id)
    assert other.matched_ai == 1 and other.aliases_learned == 1
    assert len(session.execute(select(ProductAlias)).scalars().all()) == 2


def test_history_requires_explicit_family_and_visible_product(data):
    session, a, b, market, _, private, shared = data
    for family, value in [(a, "1.23"), (b, "9.87")]:
        session.add(ProductPriceHistory(product_id=shared.id, supermarket_id=market.id,
                    family_id=family.id, date=date(2026, 11, 7),
                    unit_price=Decimal(value), unit="unit", had_promotion=False))
    # An inconsistent foreign-product row must not bypass product visibility.
    session.add(ProductPriceHistory(product_id=private.id, supermarket_id=market.id,
                family_id=b.id, date=date(2026, 11, 7), unit_price=Decimal("100"),
                unit="unit", had_promotion=False))
    session.flush()
    assert price_comparison(session, shared.id) == []
    assert price_comparison(session, private.id, b.id) == []
    assert price_comparison(session, shared.id, a.id)[0]["avg_unit_price"] == Decimal("1.2300")
    assert price_comparison(session, shared.id, b.id)[0]["avg_unit_price"] == Decimal("9.8700")
    assert price_comparison(session, shared.id, b.id)[0]["samples"] == 1


def test_unknown_lines_retain_exact_description_amount_and_review_links(data):
    session, _, b, _, _, _, _ = data
    receipt = parsed("Unknown one", "2.35")
    receipt.lines.append(ParsedLine(line_number=2, raw_text="second raw 17.89",
                         description="Unknown unrelated two", quantity=Decimal("3"),
                         line_total=Decimal("17.89")))
    receipt.total_amount = Decimal("20.24")
    result = ReceiptIngestionService(session).ingest(receipt, b.id)
    lines = session.execute(select(ReceiptLine).where(ReceiptLine.receipt_id == result.receipt_id)
                            .order_by(ReceiptLine.line_number)).scalars().all()
    assert [(l.raw_text, l.description, l.quantity, l.line_total) for l in lines] == [
        ("raw:Unknown one", "Unknown one", Decimal("1"), Decimal("2.35")),
        ("second raw 17.89", "Unknown unrelated two", Decimal("3"), Decimal("17.89")),
    ]
    reviews = session.execute(select(NormalizationReview)).scalars().all()
    assert {r.receipt_line_id for r in reviews} == {l.id for l in lines}
    assert {r.alias_text for r in reviews} == {l.description for l in lines}
    assert all(l.product_id is None for l in lines)


def test_pending_update_preserves_receipt_id_and_removes_stale_reviews(data):
    session, a, b, market, _, _, shared = data
    add_alias(session, shared, "KNOWN", market)
    pending = parsed("KNOWN", pending=True)
    pending.lines.append(ParsedLine(line_number=2, raw_text="old unknown", description="old unknown", line_total=Decimal("7.77")))
    service = ReceiptIngestionService(session)
    first = service.ingest(pending, b.id)
    receipt = session.get(Receipt, first.receipt_id)
    old_ids = {l.id for l in receipt.lines}
    assert first.price_points_created == 0
    assert session.execute(select(ProductPriceHistory)).scalars().all() == []
    with pytest.raises(ValueError):
        service.update_pending(receipt, parsed("KNOWN"), a.id)
    updated = service.update_pending(receipt, parsed("KNOWN", "4.56"), b.id)
    assert updated.receipt_id == first.receipt_id and receipt.status == "confirmed"
    assert updated.price_points_created == 1
    lines = session.execute(select(ReceiptLine).where(ReceiptLine.receipt_id == receipt.id)).scalars().all()
    assert len(lines) == 1 and lines[0].line_total == Decimal("4.56")
    assert lines[0].id not in old_ids
    assert session.execute(select(NormalizationReview)).scalars().all() == []
    with pytest.raises(ValueError):
        service.update_pending(receipt, parsed("KNOWN"), b.id)
