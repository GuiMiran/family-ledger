# Family Ledger

> **"Cada euro tiene un propósito."**

El sistema operativo financiero de una familia. Fase 1 (MVP): reducir el
desperdicio alimentario, optimizar las compras y medir el ahorro real —
a partir de una sola foto del ticket.

## Versión 0.2.0 — correcciones y flujo persistente

- Normalización, alias aprendidos e historial de precios limitados a catálogo global autorizado o familia propia.
- API autenticada para guardar/consultar tickets, confirmar pendientes y proyectar compras a inventario y analítica básica.
- Claves idempotentes por familia y transacciones con rollback; sin duplicar eventos ni inventario en reintentos.
- Instalación editable corregida, SQLAlchemy/psycopg/PyJWT declarados y administración offline para esquema, familias y tokens.

[Operación y contrato de API](docs/operations/api-v0.2.md) · [Base de datos/migración](docs/operations/database.md) · [Contrato de corrección](docs/changes/2026-11-07-remediation-contract.md).

Entrada para agentes: [AGENTS.md](AGENTS.md). Dominio: [13 capas Spectra](.spectra/00-vision.md). Protocolo: [registro de adopción](.spectra/adoption/record.json).

El [diagnóstico GUIDO histórico](docs/sdd-assessment/2026-11-07/README.md) conserva el defecto original reproducido al commit 0616d2b; las correcciones posteriores requieren su propia evidencia. No asigna nivel organizativo ni acredita reconstrucción.

La [compra Makro de 363 EUR](data/purchases/makro-36300-captured-20261107.json) sigue pendiente de fecha. No se ha desplegado ni importado a una base de datos privada. OCR de imagen, menús IA, consumo real de inventario y conversión de paquetes a €/kg siguen siendo capacidades futuras explícitas.

Gobernanza: [Spectra](https://github.com/GuiMiran/spectra), [ecosistema GUIDO](https://github.com/GuiMiran/spectra/tree/main/docs/ecosystem).

## Estado histórico declarado — Sprint 2

| Sprint | Entregable | Estado |
|---|---|---|
| Specs | Arquitectura + modelo de datos + 4 contratos OpenAPI (`/specs`) | ✅ |
| 1 | Parsers Makro + Mercadona, ParserRegistry, API de parsing | ✅ |
| 2 | Persistencia PostgreSQL (SQLAlchemy 2.0) + normalización de productos + parser Lidl | ✅ |
| — | Prototipo UI navegable (`/prototype`) | ✅ |

**34 tests declarados en el README histórico**; la ejecución actual se registra en [verificación brownfield](docs/brownfield/verification.md). Las fixtures originales corresponden a **dos tickets reales del 04/07/2026**:
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

**El raw nunca se pierde**: `raw_text` por línea y los campos estructurados se conservan. El texto OCR completo no se almacena por la API estructurada actual; su retención requiere un contrato específico de captura y privacidad.

## Ejecutar la versión actual

```bash
pip install -e ".[dev]"
pytest -q                        # suite actual
uvicorn app.main:app --reload    # docs: http://localhost:8000/docs
```

Con Docker, seguir el [procedimiento explícito de inicialización](docs/operations/api-v0.2.md) antes de arrancar API + PostgreSQL 16.

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
