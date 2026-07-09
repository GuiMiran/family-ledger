"""Registro de parsers: dado un texto OCR, elige el parser adecuado."""
from __future__ import annotations

from app.domain.receipts.models import ParsedReceipt
from app.domain.receipts.parser import ReceiptParser
from app.infrastructure.parsers.lidl import LidlParser
from app.infrastructure.parsers.makro import MakroParser
from app.infrastructure.parsers.mercadona import MercadonaParser

_MIN_SCORE = 0.5


class ParserRegistry:
    def __init__(self, parsers: list[ReceiptParser] | None = None):
        self._parsers = parsers or [MakroParser(), MercadonaParser(), LidlParser()]

    def detect(self, ocr_text: str) -> ReceiptParser | None:
        scored = sorted(
            ((p.can_parse(ocr_text), p) for p in self._parsers),
            key=lambda t: t[0],
            reverse=True,
        )
        best_score, best = scored[0]
        return best if best_score >= _MIN_SCORE else None

    def parse(self, ocr_text: str) -> ParsedReceipt:
        parser = self.detect(ocr_text)
        if parser is None:
            # Fallback: ticket no reconocido → todo a revisión.
            # (parser genérico previsto para Fase 1.1)
            from app.domain.receipts.models import FieldConfidence

            return ParsedReceipt(
                supermarket_key="unknown",
                overall_confidence=0.0,
                pending_fields=[
                    FieldConfidence(field_path="supermarket_id", confidence=0.0)
                ],
            )
        return parser.parse(ocr_text)


registry = ParserRegistry()
