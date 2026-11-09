# Contributing

Read AGENTS.md and the relevant .spectra domain layers before proposing a change.
Describe behavior, obligations, negative cases and recovery in a change record.
Keep diagnostic receipts tied to their original revision; new evidence belongs
to a new revision rather than replacing history.

Use a branch and reviewable PR. Install `python -m pip install -e ".[dev]"`, run
`python -m pytest -q`, validate Spectra layers and run the adoption verifier.
PostgreSQL qualification uses only an explicitly disposable test database.
Never commit credentials or private household receipts.

The owner reviews authorization, ownership, migration, agent instructions and
evidence controls. CODEOWNERS identifies that owner; branch protection remains
an administrator setting.
