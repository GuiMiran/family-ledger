# @spectra US-001
# @spectra OP-001
# @spectra WF-001
"""Family Ledger — API (Fase 1, vertical slice: parsing de tickets).

Este scaffold implementa el slice OCR-text → ParsedReceipt.
El endpoint /api/v1/receipts/parse recibe texto OCR (en producción vendrá
del OCRProvider tras subir la imagen) y devuelve el ticket estructurado
con pending_fields, listo para el flujo de confirmación del contrato OpenAPI.
"""
from fastapi import FastAPI
from pydantic import BaseModel

from app.domain.receipts.models import ParsedReceipt
from app.infrastructure.parsers.registry import registry

app = FastAPI(
    title="Family Ledger API",
    version="0.1.0",
    description="Cada euro tiene un propósito.",
)


class ParseRequest(BaseModel):
    ocr_text: str


@app.post("/api/v1/receipts/parse", response_model=ParsedReceipt)
def parse_receipt(body: ParseRequest) -> ParsedReceipt:
    """Parsea el texto OCR de un ticket. Detecta el supermercado
    automáticamente (Makro, Mercadona) y devuelve la estructura completa
    con confianza por campo."""
    return registry.parse(body.ocr_text)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
