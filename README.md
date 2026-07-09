# Family Ledger

> **"Cada euro tiene un propósito."**

El sistema operativo financiero de una familia. Fase 1 (MVP): reducir el
desperdicio alimentario, optimizar las compras y medir el ahorro real —
a partir de una sola foto del ticket.

## Estado actual — Sprint 2 completado

| Sprint | Entregable | Estado |
|---|---|---|
| Specs | Arquitectura + modelo de datos + 4 contratos OpenAPI (`/specs`) | ✅ |
| 1 | Parsers Makro + Mercadona, ParserRegistry, API de parsing | ✅ |
| 2 | Persistencia PostgreSQL (SQLAlchemy 2.0) + normalización de productos + parser Lidl | ✅ |
| — | Prototipo UI navegable (`/prototype`) | ✅ |

**34 tests en verde**, validados contra **dos tickets reales del 04/07/2026**:
Makro Barcelona (17 líneas, 211,87 €) y Lidl El Prat (48 líneas, 151,46 €).

## Lo esencial del diseño

**Normalización de productos** (`product_aliases`): "MACARRONS RATLLATS"
(Lidl, catalán) y "MACARRON PLUMA 3 ARO 5KG" (Makro) acaban en el mismo
producto canónico. Pipeline en cascada: exact → fuzzy → IA → cola de
revisión. Cada resolución se aprende como alias: **la segunda vez es
gratis** (test `test_lidl_ai_normalization_then_free_second_time`).

**Historial de precios propio** (`product_price_history`): la comparativa
€/kg entre supermercados sale de los tickets de la propia familia — sin
depender de APIs de terceros que no existen oficialmente.

**Reconciliación al céntimo**: cada parser valida que las líneas cuadren
con el total (Makro contra base imponible, Lidl/Mercadona contra PVP).
Si no cuadra → `pending_fields` con sugerencia. Nunca se pide
reintroducir el ticket completo.

**El raw nunca se pierde**: `raw_text` por línea y `raw_ocr` completo se
conservan; si mañana mejora un parser, se reprocesan tickets antiguos.

## Ejecutar

```bash
pip install -e ".[dev]"
pytest -q                        # 34 tests
uvicorn app.main:app --reload    # docs: http://localhost:8000/docs
```

Con Docker: `docker compose up` (API + PostgreSQL 16).

## Estructura

```
specs/                    arquitectura, modelo de datos, contratos OpenAPI
app/
  domain/                 modelos + puertos (sin frameworks)
    receipts/             ParsedReceipt, puerto ReceiptParser
    normalization/        MatchResult, puertos ProductMatcher / AIProductProposer
  application/            receipt_ingestion: persistir + normalizar + precios
  infrastructure/
    parsers/              makro.py, lidl.py, mercadona.py, registry.py
    normalization/        ExactMatcher, FuzzyMatcher (difflib→pg_trgm), stub IA
    db/                   ORM SQLAlchemy 2.0 (PostgreSQL / SQLite en tests)
prototype/                FamilyLedgerApp.jsx — UI navegable (5 pantallas)
tests/
  fixtures/               tickets reales: makro, lidl, mercadona
```

## Roadmap

- **Sprint 3**: OCRProvider real (foto → texto) + endpoints completos del
  contrato Receipt Service + evento `ReceiptConfirmed`
- **Sprint 4**: Inventory Service (despensa, congelador, ledger de movimientos)
- **Sprint 5**: Menu/AI Service (Claude) + Analytics (vistas materializadas)
- **Fase 2+**: comparador multi-super, predicción de hábitos, Flutter

---
Guido Miranda · GUIDO SDD Engineering Stack · CC BY-NC-ND 4.0
