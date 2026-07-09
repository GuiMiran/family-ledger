"""Puerto de dominio: interfaz de parser de tickets.

Cada supermercado tiene su formato de ticket. Los parsers viven en
infrastructure/parsers y se registran en el ParserRegistry. El dominio
solo conoce esta interfaz — OCR y formatos concretos quedan desacoplados.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.receipts.models import ParsedReceipt


class ReceiptParser(ABC):
    """Un parser recibe el texto plano producido por el OCR y devuelve
    un ParsedReceipt. Nunca lanza excepción por ticket malformado:
    degrada la confianza y añade pending_fields."""

    #: clave del parser, coincide con supermarkets.parser_key en BD
    key: str

    @abstractmethod
    def can_parse(self, ocr_text: str) -> float:
        """Devuelve 0.0-1.0: probabilidad de que este texto sea un ticket
        de este supermercado. El registry elige el parser con mayor score."""

    @abstractmethod
    def parse(self, ocr_text: str) -> ParsedReceipt:
        """Parsea el texto OCR completo."""
