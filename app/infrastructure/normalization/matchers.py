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
from app.infrastructure.db.orm import ProductAlias

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


class ExactMatcher(ProductMatcher):
    def __init__(self, session: Session):
        self.session = session

    def match(self, alias_text: str, supermarket_id: uuid.UUID | None):
        stmt = select(ProductAlias).where(
            func.lower(ProductAlias.alias_text) == alias_text.lower().strip(),
            or_(
                ProductAlias.supermarket_id == supermarket_id,
                ProductAlias.supermarket_id.is_(None),
            ),
        )
        # prioridad: alias específico de la cadena sobre alias global
        rows = self.session.execute(stmt).scalars().all()
        if not rows:
            return None
        best = sorted(rows, key=lambda a: a.supermarket_id is None)[0]
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

    def match(self, alias_text: str, supermarket_id: uuid.UUID | None):
        needle = normalize_text(alias_text)
        if not needle:
            return None
        best: tuple[float, ProductAlias] | None = None
        for alias in self.session.execute(select(ProductAlias)).scalars():
            score = SequenceMatcher(
                None, needle, normalize_text(alias.alias_text)
            ).ratio()
            if best is None or score > best[0]:
                best = (score, alias)
        if best and best[0] >= self.threshold:
            return MatchResult(
                product_id=best[1].product_id,
                match_type="fuzzy",
                confidence=round(best[0], 3),
                matched_alias=best[1].alias_text,
            )
        return None


class NullAIProposer(AIProductProposer):
    """Stub para tests/entornos sin IA. En producción: ClaudeProposer
    (llamada a Claude API con la línea + categorías + productos similares)."""

    def propose(self, alias_text: str, context: dict) -> dict | None:
        return None
