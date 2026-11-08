# Shopping candidate 0.3.0 · verification

Source base b6084dcbfde7122cc51c85e96683207ddb4c08e0. Candidate source snapshot
is bound by shopping-baseline.json and local-receipts.json. Local suite: 232 pass,
4 PostgreSQL tests skipped; actual PostgreSQL qualification belongs to remote CI.
TypeScript and production build pass. Browser binary download failed; visual and
physical-mobile checks have not run. No deployment or household DB changes.

Synthetic tests qualify arithmetic, eligibility, adapters, privacy, bounded agent,
explicit migration and API behavior; not six live chains. The final live smoke
queried Mercadona public storefront with explicit environment proxy opt-in:
61 observations, 6 of 8 basket groups with eligible options for echoed CP08038.
Milk UHT is credited only to the three individually checked legal-name details.
Egg size remains pending; beef cut unknown is excluded. No price is a stock or
future-price guarantee. Other five chains require configured sources.

Earlier direct/proxy smoke failures and the intermediate injected-client success
are retained separately. These do not replace the final receipt. Logs contain
no invitation, customer account, private feed token or proxy address.

Existing C/D diagnosis reports archived in ../../sdd-assessment/remediation-v0.2
refer only to b6084dc's eight selected obligations. No GUIDO level or reconstruction
claim is issued for this new feature. Spectra trace percentages are static links.

Initial CI 42456699074 ran all 236 Python tests with PostgreSQL successfully,
but failed the frontend typecheck on a duplicated coverage-label key.
`github-ci-initial.json` preserves that failure; the duplicate is removed and
the fresh local web-build.log confirms corrected compilation. Overall CI success
requires the subsequent complete run; Python success alone is not pipeline success.
