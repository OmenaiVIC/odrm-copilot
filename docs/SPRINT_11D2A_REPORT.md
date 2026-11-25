# Sprint 11 D2a — Cryptographic Provenance Workbook: Phase 5 Report

| | |
|---|---|
| Status | **Complete** |
| Date | 2026-11-25 |
| Plan | `1dbb6a5` |
| Implementation | `ccc912f` |
| Scope | CSV/Excel evidence export, four-page regulatory workbook, integration tests, operator documentation |

## 1. What was built

- **Export script:** `scripts/export_evidence_for_excel.py` generates both the CSV export and the four-page Excel workbook from the evidence chain.
- **Integration tests:** `backend/tests/integration/test_evidence_export_script.py` contains five tests covering script output, date filtering, column schema, valid integrity, and tampered integrity.
- **Documentation:** `docs/REGULATORY_WORKBOOK.md` documents the workbook purpose, page contents, integrity rules, and usage.
- **Four-page Excel workbook:**
  - `Operator Screening`
  - `Portfolio Summary`
  - `Scenario Comparison`
  - `Evidence Trail`

## 2. Test coverage and pass rates

- **Targeted integration tests:** 5 passed.
- **Full backend suite:** 604 passed (599 prior + 5 new).
- **Ruff:** Clean.
- **Mypy:** Clean (65 source files).

## 3. Deviations from the plan

- The test loader had to register `sys.modules[spec.name]` before `exec_module` to fix a `dataclass` annotation resolution failure. This is a legitimate fix for the `importlib.util` + `dataclasses` interaction and does not change the test semantics.
- The manual export against the default empty SQLite DB produced a header-only workbook. The tests exercise the full data path via a seeded temp DB, so the code is verified.

## 4. Known issues / technical debt

- `openpyxl` has no `py.typed` marker, so mypy uses `ignore_missing_imports` for `openpyxl.*`. This is documented in the pyproject override and matches the existing treatment for `reportlab`.
- Native Excel slicers are not generated; the workbook uses Table auto-filters. This is documented in `docs/REGULATORY_WORKBOOK.md`.
- `anchor_tx` is blank until D5 (Stellar anchoring).
- The workbook does not contain financial data (ROI, payback, CO2). This is intentional per the Option A scope decision. Financial portfolio reporting is deferred to Sprint 12.

## 5. Commit references

- **Implementation:** `ccc912f`
- **Plan:** `1dbb6a5`

## 6. Next deliverable

D3 (Open Benchmark Publication) — the `v1.0-benchmark` tag and `docs/BENCHMARK_REPRODUCTION.md`.
