# Iteration 001 — Receipt Intake MVP

## Objective
Create the first usable technical slice of FAMILY LEDGER.

## Scope
- Backend skeleton.
- Receipt models.
- Manual OCR text input.
- Makro receipt parser MVP.
- Price-per-unit calculation.
- Basic purchase summary.

## Out of scope
- Full mobile app.
- Real OCR provider.
- Bank integration.
- Full inventory automation.
- Complex AI orchestration.

## Deliverables
1. FastAPI app.
2. SQLite schema.
3. Receipt parser interface.
4. Makro parser MVP.
5. Tests for parser and calculations.
6. API documentation.

## Definition of Done
- `pytest` passes.
- `/health` works.
- A Makro receipt text sample produces structured JSON.
- Receipt total and line totals are validated.
- README explains how to run locally.
