"""Utilidades comunes a todos los parsers de tickets españoles."""
from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

ES_NUMBER = re.compile(r"^-?\d{1,3}(?:\.\d{3})*(?:,\d+)?-?$")


def es_decimal(raw: str) -> Decimal | None:
    """Convierte número en formato español ('1.234,56', '2,692', '1,29-')
    a Decimal. Sufijo '-' (habitual en tickets Makro) = negativo."""
    raw = raw.strip()
    if not raw:
        return None
    negative = raw.endswith("-") or raw.startswith("-")
    cleaned = raw.strip("-").replace(".", "").replace(",", ".")
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        return None
    return -value if negative else value


def es_date(raw: str) -> date | None:
    """Fechas habituales en tickets: DD/MM/YYYY o DD/MM/YY."""
    raw = raw.strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y", "%d-%m-%y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def yymmdd_date(raw: str) -> date | None:
    """Formato compacto YYMMDD usado en 'Fecha consumo preferente'
    de Makro (ej. '270117' → 2027-01-17)."""
    raw = raw.strip()
    if not re.fullmatch(r"\d{6}", raw):
        return None
    try:
        return datetime.strptime(raw, "%y%m%d").date()
    except ValueError:
        return None


def normalize_ocr_text(text: str) -> list[str]:
    """Normaliza el texto OCR en líneas limpias: colapsa espacios
    múltiples conservando la separación de columnas (2+ espacios)."""
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if line.strip():
            lines.append(line)
    return lines
