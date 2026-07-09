"""Dominio de normalización de productos.

Pipeline en cascada (spec §3 del modelo de datos):
  1. ExactMatcher   — alias_text idéntico (case-insensitive) en product_aliases
  2. FuzzyMatcher   — similitud sobre aliases existentes (pg_trgm en prod,
                      difflib como fallback portable)
  3. AIMatcher      — propone canónico vía LLM (puerto; stub en tests)
  4. Sin resolución — a cola de revisión; el usuario confirma UNA vez y el
                      alias queda aprendido para siempre.

Con ~150-300 productos recurrentes por familia, los pasos 3-4 tienden a
desaparecer en semanas de uso.
"""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class MatchResult:
    product_id: uuid.UUID
    match_type: str  # 'exact' | 'fuzzy' | 'ai'
    confidence: float
    matched_alias: str | None = None


class ProductMatcher(ABC):
    """Puerto: cada etapa del pipeline implementa esta interfaz."""

    @abstractmethod
    def match(
        self, alias_text: str, supermarket_id: uuid.UUID | None
    ) -> MatchResult | None: ...


class AIProductProposer(ABC):
    """Puerto para el proveedor de IA (Claude en prod). Recibe la línea
    y el catálogo de categorías; propone producto existente o nuevo."""

    @abstractmethod
    def propose(self, alias_text: str, context: dict) -> dict | None: ...
