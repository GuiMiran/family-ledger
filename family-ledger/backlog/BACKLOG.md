# FAMILY LEDGER — Product Backlog

## MVP
Upload ticket photo/OCR text → structured receipt → user review → saved purchase → saving summary.

## Epic 1 — Receipt Intake
### FL-001 — Backend skeleton
Status: Ready | Priority: P0
Create FastAPI backend with `/health`, config and pytest.

### FL-002 — Receipt data model
Status: Ready | Priority: P0
Models: Receipt, ReceiptItem, Store, TaxSummary, Discount, PaymentSummary.

### FL-003 — Receipt parser interface
Status: Ready | Priority: P0
Parser accepts OCR text and returns structured receipt, confidence and ambiguous fields.

### FL-004 — Makro receipt parser MVP
Status: Ready | Priority: P0
Detect Makro, total, IVA, discounts and clear line items.

### FL-005 — Manual correction workflow
Status: Next | Priority: P1
Allow user to correct product, category, quantity, price and total before saving.

## Epic 2 — Inventory
### FL-006 — Inventory model
Status: Next | Priority: P1
Pantry, fridge and freezer inventory with quantity, unit, date and optional expiry.

### FL-007 — Auto inventory update
Status: Later | Priority: P2
After saving receipt, update inventory.

## Epic 3 — Conservation & Waste
### FL-008 — Conservation recommendation
Status: Next | Priority: P1
Suggest fridge/freezer/pantry and portioning rules.

### FL-009 — Food Waste Index
Status: Later | Priority: P2
Track discarded food value.

## Epic 4 — Savings Engine
### FL-010 — Price per unit calculator
Status: Ready | Priority: P0
Calculate €/kg, €/L or €/unit.

### FL-011 — Savings report
Status: Next | Priority: P1
Show best buys, expensive products and estimated savings.

### FL-012 — Investment ROI
Status: Next | Priority: P1
Track cortafiambres, film, zip bags and vacuum sealer amortization.

## Epic 5 — Family AI
### FL-013 — Family saving summary
Status: Next | Priority: P1
Generate a plain-language family summary after each purchase.

### FL-014 — Meal ideas from inventory
Status: Later | Priority: P2
Suggest meals using current inventory and near-expiry items first.
