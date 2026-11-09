> PRIVACY-REDACTED HISTORICAL MATERIAL (2026-11-09). Private case details have been removed. This public copy is not byte-original evidence, its former file digests are withdrawn, and it does not re-certify historical outcomes. See docs/data-privacy.md.

# SDD repository evidence audit

Repository: `/workspace/scratch/1778e4e08e2b/family-ledger-conformance`
Commit: `0616d2b86c2930a8c96a2c65e4cae0cd5ff1ddbd`

Observed: 6/8; no evidence: 2/8.

| Dimension | Check | Status | Evidence |
|---|---|---|---|
| documentation | Project README | observed | `README.md` |
| documentation | Versioned specifications | observed | `.spectra/00-vision.md`, `.spectra/01-glossary.md`, `.spectra/02-stories.md` |
| governance | Contribution guidance | no_evidence | — |
| governance | Security policy | no_evidence | — |
| automation | CI workflow | observed | `.github/workflows/spectra-brownfield.yml` |
| quality | Versioned tests | observed | `tests/test_api.py`, `tests/test_ingestion.py`, `tests/test_lidl_parser.py` |
| agents | Agent instructions or contract | observed | `AGENTS.md` |
| traceability | Explicit trace mapping | observed | `.spectra/12-trace.md`, `docs/brownfield/traceability.md` |

## Next steps

- Document the contribution and review process in CONTRIBUTING.md.
- Document security reporting in SECURITY.md.

## Interpretation

Repository file presence only; observed does not imply quality or enforcement.
Absence means the check found no matching file, not that the practice does not exist.
No organizational GUIDO level or migration effort is assigned by this scan.
