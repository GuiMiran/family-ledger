"""Adaptadores de normalización.

FuzzyMatcher usa difflib (portable, funciona en SQLite/tests). En producción
PostgreSQL se sustituye por PgTrigramMatcher (similarity() de pg_trgm con
índice GIN) manteniendo el mismo puerto ProductMatcher.
"""
from __future__ import annotations

import re
import unicodedata
import uuid
from difflib import SequenceMatcher

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.domain.normalization.pipeline import (
    AIProductProposer,
    MatchResult,
    ProductMatcher,
)
from app.infrastructure.db.orm import Product, ProductAlias

# ruido habitual en descripciones de ticket que no aporta identidad
_NOISE = re.compile(
    r"\b(\d+[.,]?\d*\s?(kg|g|l|ml|cl|ud|uds|x\d+)|mc|aro|bj|vc|bl|pq|rlr|prof|peça|pack)\b",
    re.IGNORECASE,
)


def normalize_text(raw: str) -> str:
    """Normaliza para comparar: sin acentos, minúsculas, sin ruido de formato.
    'MACARRÓN PLUMA 3 ARO 5KG' → 'macarron pluma 3'."""
    text = unicodedata.normalize("NFKD", raw)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = _NOISE.sub(" ", text)
    text = re.sub(r"[^a-z0-9ñç ]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _visible_aliases(supermarket_id, family_id):
    """Both an alias and its product must be shared or owned by this family.

    Omitting the family deliberately grants only shared-catalog visibility.
    An alias from another market is not a candidate for either matcher.
    """
    return (
        select(ProductAlias, Product)
        .join(Product, Product.id == ProductAlias.product_id)
        .where(
            or_(ProductAlias.supermarket_id == supermarket_id,
                ProductAlias.supermarket_id.is_(None)),
            or_(Product.family_id.is_(None), Product.family_id == family_id),
            or_(ProductAlias.family_id.is_(None), ProductAlias.family_id == family_id),
        )
    )


def _precedence(alias, product):
    # Specific market, then own alias/product, then deterministic tie-breaking.
    return (alias.supermarket_id is None, alias.family_id is None,
            product.family_id is None, str(alias.id))


class ExactMatcher(ProductMatcher):
    def __init__(self, session: Session):
        self.session = session

    def match(self, alias_text: str, supermarket_id: uuid.UUID | None,
              family_id: uuid.UUID | None = None):
        stmt = _visible_aliases(supermarket_id, family_id).where(
            func.lower(ProductAlias.alias_text) == alias_text.lower().strip(),
        )
        rows = self.session.execute(stmt).all()
        if not rows:
            return None
        best, _ = min(rows, key=lambda row: _precedence(*row))
        return MatchResult(
            product_id=best.product_id,
            match_type="exact",
            confidence=1.0,
            matched_alias=best.alias_text,
        )


class FuzzyMatcher(ProductMatcher):
    """Similitud difflib sobre el texto normalizado de todos los aliases.
    En producción: PgTrigramMatcher con el mismo umbral."""

    def __init__(self, session: Session, threshold: float = 0.72):
        self.session = session
        self.threshold = threshold

    def match(self, alias_text: str, supermarket_id: uuid.UUID | None,
              family_id: uuid.UUID | None = None):
        needle = normalize_text(alias_text)
        if not needle:
            return None
        candidates = []
        for alias, product in self.session.execute(
            _visible_aliases(supermarket_id, family_id)
        ).all():
            score = SequenceMatcher(
                None, needle, normalize_text(alias.alias_text)
            ).ratio()
            if score >= self.threshold:
                # Honor market/ownership precedence among accepted candidates;
                # similarity then resolves candidates within the same scope.
                scope = _precedence(alias, product)
                candidates.append(((*scope[:3], -score, scope[3]), score, alias))
        if candidates:
            _, score, alias = min(candidates, key=lambda candidate: candidate[0])
            return MatchResult(
                product_id=alias.product_id,
                match_type="fuzzy",
                confidence=round(score, 3),
                matched_alias=alias.alias_text,
            )
        return None


class NullAIProposer(AIProductProposer):
    """Stub para tests/entornos sin IA. En producción: ClaudeProposer
    (llamada a Claude API con la línea + categorías + productos similares)."""

    def propose(self, alias_text: str, context: dict) -> dict | None:
        return None
