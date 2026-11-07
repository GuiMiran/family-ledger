# Remediation candidate 0.2.0

The original GUIDO diagnosis and its failing receipt remain immutable in
`../2026-11-07/`. This directory records later corrective work; it does not
replace the original evaluation with a retrospective PASS.

## Corrected behavior

| Original finding | Corrective evidence | Scope |
|---|---|---|
| Cross-family normalization/history | `tests/test_family_isolation.py`, original isolation probe rerun | Exact/fuzzy/AI, alias privacy and family history |
| Unknown-line retention not challenged | Explicit description/amount assertions in `tests/test_ingestion.py` | Existing implementation, not reconstruction |
| Editable install/driver failure | Clean editable install, `tests/test_db_session.py`, pip check | Sync SQLAlchemy/psycopg, package discovery |
| Parsing API disconnected from persistence | `tests/test_receipt_api.py` | Authenticated commands and reads, stable pending confirmation |
| No atomic inventory/event projection | API retry and injected-failure tests | Durable internal event and purchase projection in one transaction |
| Migration path absent | `tests/test_migrations.py` | Explicit recognized-schema migration and rollback; no production operation |
| Storage precision/VAT input gaps | `tests/test_receipt_validation_limits.py` | Reject rounding-away values, impossible VAT, out-of-range storage |
| No PostgreSQL concurrency qualification | `tests/test_postgres.py`, dedicated CI service | Only qualified when that job actually runs |

Independent implementation work: reviewer A implemented normalization and
independently challenged the root API with tests; reviewer B implemented the
packaging/session/migration slice and reviewed the root validation logic. That
review found numeric-precision and VAT blockers, which were corrected and
rechecked. These are code-review/test activities, not two fresh blinded
organizational assessments or a reconstruction trial.

## Receipts and provenance

`local-receipts.json` identifies the source base plus candidate snapshot digest
in `docs/brownfield/remediation-baseline.json`. `local-tests.log` reports real
local execution, including PostgreSQL skips. `family-isolation-after.log`
records the same synthetic challenge that previously failed. The historical
baseline JSON and all original report/log hashes are retained.

The candidate is subject to owner review. Local SQLite success is not a claim
about a deployed server. Remote CI runs are the separate source-commit-bound
evidence for PostgreSQL. No household receipt has been imported into a remote
database, and the 363 EUR record's sale date remains unknown.

## Remaining product work

Real image OCR, connected UI, consumption/reservation ledger, AI menus and
package-to-unit price conversion remain separately specified roadmap work.
Legacy alias provenance needs an operator decision; quarantine prevents it
becoming shared by default. Deployment, backup rehearsal on retained user data
and isolated reconstruction have not been performed. No G1–G5 rating is issued.
