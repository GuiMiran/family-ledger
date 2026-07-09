# FAMILY LEDGER — Codex Project Brief

## Mission
Build FAMILY LEDGER as an AI-powered household economy system using Spec Driven Development.

The first practical version must transform receipt photos into structured purchase data, then use that data to feed inventory, conservation, savings, and food-waste decisions.

## Working Method: Spec Driven Development
For every feature:
1. Read the domain spec.
2. Update or create acceptance criteria.
3. Create or update the test plan.
4. Implement the smallest useful slice.
5. Add tests.
6. Update documentation and backlog status.

## MVP Goal
Upload a receipt photo, extract purchase data, review it, save it, and generate a useful family-saving summary.

## First Vertical Slice
Receipt photo → OCR text → parsed receipt → product lines → purchase summary → manual correction → saved purchase.

## Tech Proposal
- Backend: Python + FastAPI
- Database: SQLite first, PostgreSQL later
- OCR: pluggable adapter, first version can use manual OCR text input or mocked OCR
- Frontend: simple web UI first, Flutter later
- Tests: pytest
- API docs: OpenAPI
- Project style: clean architecture

## Non-negotiables
- Keep OCR, AI and business logic decoupled.
- Store original receipt image metadata.
- Track confidence and ambiguous fields.
- Never overwrite user-corrected values without confirmation.
- Every module must have a spec and test plan.

## First Codex Task
Create the backend skeleton with FastAPI, domain models, receipt parser interface, SQLite persistence, and endpoint `POST /receipts/parse`.
