"""Caso de uso: ingesta de un ticket parseado.

ParsedReceipt (dominio parsing) →
  1. Persistir Receipt + ReceiptLines
  2. Normalizar cada línea (exact → fuzzy → ai → cola de revisión)
  3. Aprender aliases nuevos de los matches fuzzy/ai confiables
  4. Insertar ProductPriceHistory por línea normalizada
     (base de la comparativa €/kg entre supermercados)
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.normalization.pipeline import AIProductProposer
from app.domain.receipts.models import ParsedReceipt
from app.infrastructure.db.orm import (
    NormalizationReview,
    Product,
    ProductAlias,
    ProductPriceHistory,
    Receipt,
    ReceiptLine,
    Supermarket,
)
from app.infrastructure.normalization.matchers import (
    ExactMatcher,
    FuzzyMatcher,
    NullAIProposer,
)

_LEARN_THRESHOLD = 0.80  # fuzzy/ai por encima → alias aprendido
_AI_ACCEPT_THRESHOLD = 0.85


@dataclass
class IngestionResult:
    receipt_id: uuid.UUID
    lines_total: int = 0
    matched_exact: int = 0
    matched_fuzzy: int = 0
    matched_ai: int = 0
    sent_to_review: int = 0
    aliases_learned: int = 0
    price_points_created: int = 0
    review_items: list[str] = field(default_factory=list)


class ReceiptIngestionService:
    def __init__(
        self,
        session: Session,
        ai_proposer: AIProductProposer | None = None,
    ):
        self.session = session
        self.exact = ExactMatcher(session)
        self.fuzzy = FuzzyMatcher(session)
        self.ai = ai_proposer or NullAIProposer()

    # ──────────────────────────────────────────────
    def ingest(self, parsed: ParsedReceipt, family_id: uuid.UUID) -> IngestionResult:
        supermarket = self._resolve_supermarket(parsed.supermarket_key)

        receipt = Receipt(
            family_id=family_id,
            supermarket_id=supermarket.id if supermarket else None,
            purchase_date=parsed.purchase_date,
            total_amount=parsed.total_amount,
            total_vat=parsed.total_vat,
            total_discounts=parsed.total_discounts,
            payment_method=parsed.payment_method.value
            if parsed.payment_method
            else None,
            invoice_number=parsed.invoice_number,
            ocr_confidence=Decimal(str(parsed.overall_confidence)),
            status="confirmed" if not parsed.pending_fields else "pending_review",
        )
        self.session.add(receipt)
        self.session.flush()

        result = IngestionResult(receipt_id=receipt.id, lines_total=len(parsed.lines))

        for pl in parsed.lines:
            line = ReceiptLine(
                receipt_id=receipt.id,
                line_number=pl.line_number,
                raw_text=pl.raw_text,
                description=pl.description,
                quantity=pl.quantity,
                unit=pl.unit.value,
                unit_price=pl.unit_price,
                line_total=pl.line_total,
                discount_amount=pl.discount_amount,
                promotion_text=pl.promotion_text,
                vat_rate=pl.vat_rate,
                expiry_date=pl.expiry_date,
            )
            self.session.add(line)
            self.session.flush()
            self._normalize_line(
                line, supermarket.id if supermarket else None, family_id, result
            )

        self.session.flush()
        return result

    # ──────────────────────────────────────────────
    def _normalize_line(
        self,
        line: ReceiptLine,
        supermarket_id: uuid.UUID | None,
        family_id: uuid.UUID,
        result: IngestionResult,
    ) -> None:
        # 1. exact
        if m := self.exact.match(line.description, supermarket_id):
            result.matched_exact += 1
            self._apply_match(line, m, supermarket_id, family_id, result, learn=False)
            return

        # 2. fuzzy
        if m := self.fuzzy.match(line.description, supermarket_id):
            result.matched_fuzzy += 1
            self._apply_match(
                line, m, supermarket_id, family_id, result,
                learn=m.confidence >= _LEARN_THRESHOLD,
            )
            return

        # 3. IA
        proposal = self.ai.propose(
            line.description,
            {"supermarket_id": str(supermarket_id) if supermarket_id else None},
        )
        if proposal and proposal.get("confidence", 0) >= _AI_ACCEPT_THRESHOLD:
            product_id = self._resolve_ai_proposal(proposal, family_id)
            if product_id:
                from app.domain.normalization.pipeline import MatchResult

                m = MatchResult(
                    product_id=product_id,
                    match_type="ai",
                    confidence=proposal["confidence"],
                )
                result.matched_ai += 1
                self._apply_match(
                    line, m, supermarket_id, family_id, result, learn=True
                )
                return

        # 4. cola de revisión (raw_text nunca se pierde: reprocesable)
        self.session.add(
            NormalizationReview(
                receipt_line_id=line.id,
                alias_text=line.description,
                supermarket_id=supermarket_id,
                ai_proposal=proposal,
            )
        )
        result.sent_to_review += 1
        result.review_items.append(line.description)

    def _apply_match(
        self,
        line: ReceiptLine,
        m,
        supermarket_id: uuid.UUID | None,
        family_id: uuid.UUID,
        result: IngestionResult,
        learn: bool,
    ) -> None:
        line.product_id = m.product_id
        line.match_type = m.match_type
        line.match_confidence = Decimal(str(m.confidence))

        if learn:
            exists = self.session.execute(
                select(ProductAlias).where(
                    ProductAlias.supermarket_id == supermarket_id,
                    ProductAlias.alias_text == line.description,
                )
            ).scalar_one_or_none()
            if not exists:
                self.session.add(
                    ProductAlias(
                        product_id=m.product_id,
                        supermarket_id=supermarket_id,
                        alias_text=line.description,
                        match_type=m.match_type,
                        confidence=Decimal(str(m.confidence)),
                    )
                )
                result.aliases_learned += 1

        # precio unitario normalizado → historial de precios
        if line.unit_price is not None and line.receipt.purchase_date:
            self.session.add(
                ProductPriceHistory(
                    product_id=m.product_id,
                    supermarket_id=supermarket_id,
                    family_id=family_id,
                    date=line.receipt.purchase_date,
                    unit_price=line.unit_price,
                    unit=line.unit,
                    had_promotion=bool(line.promotion_text)
                    or line.discount_amount > 0,
                )
            )
            result.price_points_created += 1

    # ──────────────────────────────────────────────
    def _resolve_supermarket(self, parser_key: str) -> Supermarket | None:
        return self.session.execute(
            select(Supermarket).where(Supermarket.parser_key == parser_key)
        ).scalar_one_or_none()

    def _resolve_ai_proposal(
        self, proposal: dict, family_id: uuid.UUID
    ) -> uuid.UUID | None:
        if pid := proposal.get("existing_product_id"):
            return uuid.UUID(pid)
        if new := proposal.get("new_product"):
            product = Product(
                family_id=family_id,
                canonical_name=new["canonical_name"],
                default_unit=new.get("default_unit", "unit"),
            )
            self.session.add(product)
            self.session.flush()
            return product.id
        return None


# ────────────────────── Consulta: comparativa €/kg ──────────────────────
def price_comparison(session: Session, product_id: uuid.UUID) -> list[dict]:
    """¿Dónde suele salir más barato este producto? Con los datos propios
    de la familia — sin depender de APIs de terceros."""
    from sqlalchemy import func as f

    rows = session.execute(
        select(
            Supermarket.name,
            f.avg(ProductPriceHistory.unit_price),
            f.min(ProductPriceHistory.unit_price),
            f.count(ProductPriceHistory.id),
            ProductPriceHistory.unit,
        )
        .join(Supermarket, Supermarket.id == ProductPriceHistory.supermarket_id)
        .where(ProductPriceHistory.product_id == product_id)
        .group_by(Supermarket.name, ProductPriceHistory.unit)
        .order_by(f.avg(ProductPriceHistory.unit_price))
    ).all()
    return [
        {
            "supermarket": name,
            "avg_unit_price": round(Decimal(avg), 4),
            "min_unit_price": min_,
            "samples": count,
            "unit": unit,
        }
        for name, avg, min_, count, unit in rows
    ]
