# Prompt for Codex — Iteration 001

You are working on FAMILY LEDGER, an AI-powered household economy system developed using Spec Driven Development.

Before coding, read:
- README.md
- CODEX.md
- backlog/BACKLOG.md
- codex/ITERATION_001.md
- domains/purchase-intelligence/receipt.spec.md
- testplans/receipt.testplan.md

Task: Implement Iteration 001.

Build a Python FastAPI backend with:
1. `/health` endpoint.
2. Domain models: Receipt, ReceiptItem, Store, TaxSummary, Discount, PaymentSummary.
3. Parser abstraction: ReceiptParser interface and ParserResult with confidence and ambiguous fields.
4. MakroReceiptParser MVP that accepts OCR text and returns structured receipt data.
5. Price-per-unit calculator.
6. Basic persistence using SQLite.
7. Tests with pytest.
8. README update with local run instructions.

Constraints:
- Keep OCR provider separate from parsing.
- Do not hardcode the whole app into one file.
- Use clean architecture folders.
- Implement the smallest useful slice.
- Add tests before considering the task complete.

Expected result:
A developer can run the backend locally, submit OCR text from a Makro receipt, and receive structured JSON with items, totals, confidence and warnings.
