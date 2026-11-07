# Security reporting and data boundaries

Report a minimal synthetic reproducer and affected revision. Do not put secrets,
tokens or personal receipts in public issues. Arrange a private channel with
the owner before sharing sensitive details; no unverified reporting address is
published here.

Version 0.2.0 scopes receipt data, aliases and price history to the authenticated
family and explicitly shared catalogue entries. Tokens are issued offline by an
operator; there is no public registration or token-minting endpoint. Use TLS at
the hosting boundary, independent deployment secrets and short-lived tokens.

Schema changes require explicit initialization/migration and a backup of an
existing database. Legacy aliases attached to shared products are quarantined during migration
until owner review, because older rows did not record who learned them. A
migration cannot recover that missing provenance by guessing.

The UI prototype, OCR provider and AI menu generation are not a deployed product.
Passing the suite does not establish comprehensive production security.
