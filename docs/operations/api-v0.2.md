# Receipt API 0.2.0

This API accepts OCR text for parsing and structured `ParsedReceipt` objects for
persistence. It does not supply a real image-OCR provider or deploy the UI
prototype. The generated `/openapi.json` and `/docs` describe implemented routes;
the original `specs/03` photo/OCR contract remains a future target where different.

## Explicit local setup

Install `python -m pip install -e ".[dev]"`. Configure `DATABASE_URL` and a random
`JWT_SECRET` of at least 32 characters in an untracked operator environment.
For retained databases, read [database migration](database.md) before proceeding.

```sh
python -m app.admin init-db
python -m app.admin create-family --name "My household"
python -m app.admin token --family FAMILY_UUID --hours 8
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Replace FAMILY_UUID with the provisioned UUID. The token command deliberately
prints an access token for the operator; do not paste it into a public issue,
commit or diagnostic log. There is no public family-registration/token endpoint.
Use TLS when serving beyond localhost. Production secrets and databases are not
created by these repository changes.

For a new Compose database, start PostgreSQL, run the explicit initializer using
the API image, provision the family and issue a token, then start the API. No
implicit migration occurs during import or application startup.

```sh
docker compose up -d db
docker compose run --rm api python -m app.admin init-db
docker compose run --rm api python -m app.admin create-family --name "My household"
docker compose run --rm api python -m app.admin token --family FAMILY_UUID --hours 8
docker compose up -d api
```

## Implemented contract

| Route | Inputs | Result |
|---|---|---|
| `POST /api/v1/receipts/parse` | `{ "ocr_text": "..." }` | Parsed receipt; does not save |
| `POST /api/v1/receipts` | Bearer token, `Idempotency-Key`, ParsedReceipt | Stores pending or confirmed receipt; 201 |
| `POST /api/v1/receipts/{id}/confirm` | Bearer, a new command key, corrected ParsedReceipt | Confirms an owned pending receipt with stable ID |
| `GET /api/v1/receipts` | Bearer, limit/offset | Owned receipts only |
| `GET /api/v1/receipts/{id}` | Bearer | Owned receipt, otherwise 404 |
| `GET /api/v1/inventory` | Bearer, limit/offset | Once-only confirmed purchase projection |
| `GET /api/v1/analytics` | Bearer, optional start/end dates | Confirmed totals and pending count within scope |

Family identity comes from the signed, expiring token, never from a request body.
The operator controls signing authority. Missing/invalid/expired credentials are
rejected. Unknown families cannot self-provision through the API.

The same key/body retry returns the existing receipt. A changed request using
that key returns 409. Keys are scoped by family. Receipt, lines, normalization,
idempotency record, internal ReceiptConfirmed fact and inventory projection are
one transaction. The durable event is consumed inline once; this is not an
external broker or a claim of exactly-once delivery across arbitrary consumers.

The server validates quantities, values, required fields and totals itself;
client-supplied confidence/pending fields cannot certify a mismatching total.
Missing date or other review fields retains pending status and creates no
confirmed event/inventory. Confirmation requires a corrected valid receipt.
Malformed requests return 422. Pending receipts do not create price history.

Amounts and quantities must fit their database precision without rounding away
value. VAT cannot exceed the paid total. A reconciliation difference of up to
0.05 EUR remains pending for correction; a larger difference is rejected. No
nonzero difference is silently promoted to a confirmed purchase.

Inventory lists quantities purchased, in the parser's declared units. It does
not subtract consumption or infer package-content conversions. Analytics excludes
undated pending purchases from date periods. Product price history preserves
original units; there is no claim of comparable €/kg across package formats.

## Current Makro record

`data/purchases/makro-36300-captured-20261107.json` contains a `parsed_receipt`
member ready for review/import. Its sale date remains unknown. Importing that
member would store a pending purchase, without inventory, until the user confirms
the actual date. This release has not imported it into a deployed/private BD.

## Verification

Run `python -m pytest -q`. SQLite checks cover isolation, persistence/restarts,
idempotency, confirmation and failure rollback. The PostgreSQL job uses an
ephemeral database ending in `_test` and exercises concurrent same-key commands;
those checks skip locally if TEST_DATABASE_URL is not supplied. A skip does not
qualify PostgreSQL. Migration and deployment have separate runbooks and evidence.
