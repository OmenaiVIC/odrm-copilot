# Sprint 11 D2a Phase 2 Plan — Cryptographic Provenance Workbook

**Status:** Draft for CTO approval  
**Phase:** D2a Phase 2 — plan only  
**Scope decision:** Option A — cryptographic provenance audit tool, not a financial dashboard

## 1. Goal

Add a reproducible CSV export and a programmatically generated, four-page `.xlsx` workbook that lets a regulator inspect screening evidence, confirm Merkle-tree integrity, and trace batch-level provenance.

The workbook is a cryptographic provenance audit tool. Financial portfolio reporting, operator metadata, site metadata, ROI, payback, and CO2 analysis are deferred to Sprint 12 and are not part of D2a.

## 2. Deliverables

1. `scripts/export_evidence_for_excel.py` — reads `screening_evidence` and `evidence_batches`, writes `exports/evidence_export.csv`, then builds `exports/regulatory_workbook.xlsx` from that CSV with `openpyxl`.
2. `docs/REGULATORY_WORKBOOK.md` — operator/regulator documentation covering purpose, scope, refresh process, workbook pages, Integrity Status meaning, limitations, and MIT licensing.
3. `backend/tests/integration/test_evidence_export_script.py` — focused integration tests for the CSV contract, date filtering, and integrity-status behavior.
4. Dependency and ignore updates for `openpyxl` and generated workbooks.

## 3. Acceptance Criteria

- AC-D2a-1: Running `python scripts/export_evidence_for_excel.py` from the repo root exits `0`, creates `exports/`, writes `exports/evidence_export.csv`, and writes `exports/regulatory_workbook.xlsx`.
- AC-D2a-2: The CSV has exactly these columns, in this order: `date`, `screening_hash`, `batch_id`, `leaf_index`, `integrity_status`, `merkle_root`, `leaf_count`, `anchor_status`, `anchor_tx`.
- AC-D2a-3: `integrity_status` is `verified` only when the row's screening hash verifies against the **stored** `evidence_batches.merkle_root`; otherwise it is `failed`.
- AC-D2a-4: `leaf_index` is the row's batch-local, zero-based position ordered by `(created_at ASC, id ASC)` and is computed from the full batch, even when the output is date-filtered.
- AC-D2a-5: The workbook contains exactly four visible pages: `Operator Screening`, `Portfolio Summary`, `Scenario Comparison`, and `Evidence Trail`.
- AC-D2a-6: `Operator Screening` uses the header `Integrity Status` and displays `✓ Verified` or `✗ Failed`; it includes the exact data-source limitation text required below.
- AC-D2a-7: `Portfolio Summary` contains only a screenings-per-week series and a batch-size chart; it contains no ROI, payback, CO2, operator, or site data.
- AC-D2a-8: `Scenario Comparison` is a formula-driven lookup for two screening hashes and confirms batch membership; it contains no financial metrics.
- AC-D2a-9: `Evidence Trail` has one row per batch with `batch_id`, `leaf_count`, truncated `merkle_root`, `anchor_status`, and blank `anchor_tx`.
- AC-D2a-10: The workbook is generated from the CSV with no live Power Query connection; documentation says rerunning the script refreshes it.
- AC-D2a-11: `openpyxl` is declared in both `pyproject.toml` and `requirements.txt`; `exports/*.xlsx` is ignored and generated artifacts are not tracked.
- AC-D2a-12: Focused tests, the full backend test suite, Ruff, and mypy pass; CTO manual review confirms the workbook contents.

## 4. Files to Create

- `scripts/export_evidence_for_excel.py`
- `docs/REGULATORY_WORKBOOK.md`
- `backend/tests/integration/test_evidence_export_script.py`

`exports/` is a runtime output directory only. `exports/evidence_export.csv` and `exports/regulatory_workbook.xlsx` must remain untracked.

## 5. Files to Modify

- `pyproject.toml` — add `openpyxl` to project dependencies.
- `requirements.txt` — add the pinned `openpyxl` version.
- `.gitignore` — add `exports/*.xlsx` (CSV is already covered by `*.csv`).

No changes are authorized for backend models, migrations, repositories, services, API routes, frontend code, or existing D2 behavior.

## 6. Technical Design

### 6.1 Script structure and CLI

`scripts/export_evidence_for_excel.py` should be a thin CLI with a testable `main(argv: Sequence[str] | None = None) -> int`.

Constants:

```python
CSV_COLUMNS = (
    "date",
    "screening_hash",
    "batch_id",
    "leaf_index",
    "integrity_status",
    "merkle_root",
    "leaf_count",
    "anchor_status",
    "anchor_tx",
)
CSV_NAME = "evidence_export.csv"
WORKBOOK_NAME = "regulatory_workbook.xlsx"
```

CLI arguments:

- `--database-url`: optional override; otherwise use `get_settings().database_url`.
- `--output-dir`: default `REPO_ROOT / "exports"`.
- `--start YYYY-MM-DD`: inclusive UTC date lower bound.
- `--end YYYY-MM-DD`: inclusive UTC date upper bound; convert internally to an exclusive next-day boundary.

Validate `start <= end`, create the output directory, write the CSV first, then build the workbook from that CSV. Print a JSON summary containing output paths, row count, and batch count.

Use `odrm.db.create_session_factory`, `odrm.evidence.models.EvidenceBatch`, `odrm.evidence.models.ScreeningEvidence`, and `odrm.evidence.repository.SqlAlchemyEvidenceRepository` with `root_builder=merkle_root`.

### 6.2 Exact SQLAlchemy query for output rows

The output query filters on `screening_evidence.created_at`. It must return each selected screening row joined to its batch, in deterministic order:

```python
def load_export_rows(
    session_factory: sessionmaker[Session],
    start: datetime | None,
    end_exclusive: datetime | None,
) -> list[ExportRow]:
    stmt = (
        select(ScreeningEvidence, EvidenceBatch)
        .join(EvidenceBatch, ScreeningEvidence.batch_id == EvidenceBatch.id)
        .order_by(
            EvidenceBatch.created_at.asc(),
            EvidenceBatch.id.asc(),
            ScreeningEvidence.created_at.asc(),
            ScreeningEvidence.id.asc(),
        )
    )
    if start is not None:
        stmt = stmt.where(ScreeningEvidence.created_at >= start)
    if end_exclusive is not None:
        stmt = stmt.where(ScreeningEvidence.created_at < end_exclusive)

    with session_factory() as session:
        return [
            ExportRow(
                leaf_id=leaf.id,
                screening_hash=leaf.screening_hash,
                batch_id=leaf.batch_id,
                created_at=as_utc(leaf.created_at),
                stored_merkle_root=batch.merkle_root,
                stored_leaf_count=batch.leaf_count,
                anchor_status=batch.anchor_status,
            )
            for leaf, batch in session.execute(stmt)
        ]
```

`ExportRow` is a frozen dataclass populated before the session closes. `as_utc()` normalizes naive SQLite datetimes to UTC and converts aware datetimes to UTC.

Date filtering applies only to the rows written to the CSV. It must **not** be used to build the Merkle tree. A date-filtered export still loads every leaf in each included batch so that proofs and batch roots remain valid.

### 6.3 Full-batch integrity evaluation

For each unique batch represented in the filtered output, load the full batch with:

```python
leaves = repository.list_leaves(batch_id)
hashes = [leaf.screening_hash for leaf in leaves]
computed_root = merkle_root(hashes) if hashes else None
```

The repository already orders leaves by `(created_at ASC, id ASC)`, which is the D2 Merkle leaf order. Cache one `BatchState` per batch:

```python
@dataclass(frozen=True)
class BatchState:
    leaves: list[EvidenceLeafRecord]
    hashes: list[str]
    stored_root: str
    stored_leaf_count: int
    index_by_leaf_id: dict[str, int]
    batch_ok: bool
```

`batch_ok` must be true only when all of the following hold:

- The batch has at least one leaf.
- `stored_leaf_count == len(hashes)`.
- `computed_root == stored_root`.
- `leaf.batch_id == batch_id` for every leaf.

For each output row:

```python
index = state.index_by_leaf_id.get(row.leaf_id)
if index is None or not state.batch_ok:
    status = "failed"
else:
    proof = merkle_proof(state.hashes, index)
    status = "verified" if verify_merkle_proof(
        row.screening_hash,
        proof,
        state.stored_root,
        index,
        state.stored_leaf_count,
    ) else "failed"
```

**Tamper-detection requirement:** `EvidenceService.verify()` recomputes the root from current leaves and does not compare it to the stored batch row. The export must not rely on `EvidenceProof.verified` alone. It must compare the recomputed root and leaf count to `EvidenceBatch.merkle_root` / `EvidenceBatch.leaf_count`. This is what makes `test_integrity_status_is_failed_for_tampered_row` meaningful.

Consequences to document:

- Tampering with one leaf invalidates the whole batch; every exported row from that batch reports `failed`.
- Tampering with a stored batch root or leaf count also marks the whole batch `failed`.
- A date-filtered row can be `failed` because of tampering in another, unexported row of the same batch. This is intentional.

### 6.4 CSV schema and formatting

Write with `csv.DictWriter`, UTF-8, `lineterminator="\n"`, and the exact `CSV_COLUMNS` order.

Row mapping:

| Column | Source | Format |
| --- | --- | --- |
| `date` | `screening_evidence.created_at` | ISO-8601 UTC with `Z` suffix |
| `screening_hash` | `screening_evidence.screening_hash` | lowercase 64-hex string |
| `batch_id` | `screening_evidence.batch_id` | string |
| `leaf_index` | full-batch leaf position by leaf id | zero-based integer |
| `integrity_status` | computed batch/proof result | `verified` or `failed` |
| `merkle_root` | stored `evidence_batches.merkle_root` | full 64-hex string |
| `leaf_count` | stored `evidence_batches.leaf_count` | integer |
| `anchor_status` | stored `evidence_batches.anchor_status` | string |
| `anchor_tx` | not present until D5 | empty string |

If no rows match, write the header only. The workbook must still open and explain that no evidence records matched the filter.

### 6.5 Workbook generation with openpyxl

Use `openpyxl.Workbook`, standard styles, and Excel `Table` objects. Read the generated CSV back with `csv.DictReader`; do not read the database directly from the workbook builder. This preserves the “CSV is the workbook data source” contract.

Workbook properties:

- Title: `ODRM Cryptographic Provenance Workbook`
- Subject: `Merkle-tree screening evidence audit`
- Creator: `ODRM Copilot`
- Description: `Cryptographic provenance audit workbook. Not a financial model.`
- Keywords: `ODRM, provenance, Merkle, screening, audit`

Set `wb.calculation.fullCalcOnLoad = True` so Scenario Comparison formulas calculate when opened.

#### Page 1 — `Operator Screening`

- Header row: `Date`, `Screening Hash`, `Batch ID`, `Integrity Status`, `Leaf Index`.
- One row per CSV row, in CSV order.
- Write `Date` as an Excel datetime with number format `yyyy-mm-dd hh:mm:ss`.
- Map `verified` to `✓ Verified` and `failed` to `✗ Failed`. Use green fill/font for verified and red fill/font for failed.
- Create Excel Table `OperatorScreening` over the full data range with auto-filter and striped rows.
- Freeze `A2`, set sensible column widths, and enable header wrapping.
- Put the exact limitation text in a merged cell below the table, wrapped and italicized:

  `Financial data (ROI, payback, CO2) and operator metadata are not stored in the current evidence schema. This workbook is a cryptographic provenance audit tool.`

- If there are no rows, write the headers, a “No evidence records matched the export filter.” note, and the limitation text; do not create an empty table.

#### Page 2 — `Portfolio Summary`

- Derive all data from the CSV.
- Weekly screenings: parse `date`, group by ISO year/week, use the Monday of the ISO week as the label, and count rows. Write a `WeeklyScreenings` table with `Week` and `Screenings`.
- Batch sizes: deduplicate by `batch_id`, preserving first appearance order (the CSV is already ordered by batch creation), and use `leaf_count`. Write a `BatchSizes` table with `Batch` and `Leaves`.
- Add a `LineChart` titled `Screenings per Week` using the weekly table, with axis titles `Week` and `Screenings`.
- Add a `BarChart` titled `Batch Sizes` using the batch table, with axis titles `Batch` and `Leaves`.
- Use short batch labels such as `batch_id[:8] + "…"`; full IDs remain in the CSV and Evidence Trail.
- Add a note: `Charts are generated from evidence_export.csv. Rerun the export script to refresh.`
- No financial, ROI, payback, CO2, operator, or site metrics.

#### Page 3 — `Scenario Comparison`

- Header row: `Screening Hash`, `Batch ID`, `Integrity Status`, `Leaf Index`, `Batch Membership`.
- Rows 2 and 3 are the two comparison inputs. Prefill them with the first two distinct screening hashes from the CSV, if available; otherwise leave blank.
- Add a data-validation list on `A2:A3` sourced from `'Operator Screening'!$B$2:$B$<last_row>`.
- Add exact-match formulas for rows 2 and 3:
  - Batch ID: `=IFERROR(VLOOKUP($A2,'Operator Screening'!$B$2:$E$<last_row>,2,FALSE),"Not found")`
  - Integrity Status: `=IFERROR(VLOOKUP($A2,'Operator Screening'!$B$2:$E$<last_row>,3,FALSE),"Not found")`
  - Leaf Index: `=IFERROR(VLOOKUP($A2,'Operator Screening'!$B$2:$E$<last_row>,4,FALSE),"Not found")`
  - Batch Membership: `=IF(COUNTIF('Operator Screening'!$B$2:$B$<last_row>,$A2)>0,"Member","Not found")`
- Add a note explaining that users select two screening hashes from the dropdowns; the sheet is a lookup, not a financial scenario model.
- If no screening rows exist, write the headers and a “No screening hashes available.” note and skip formulas/data validation.

#### Page 4 — `Evidence Trail`

- Deduplicate batches from the CSV, preserving first appearance order.
- Header row: `Batch ID`, `Leaf Count`, `Merkle Root`, `Anchor Status`, `Anchor Tx`.
- `Merkle Root` display value: first 16 hex characters, an ellipsis, and the last 8 characters when the root is longer; attach the full root as an Excel cell comment.
- `Anchor Tx` is always blank until D5 Stellar anchoring.
- Create Excel Table `EvidenceTrail` with auto-filter and striped rows. The `Anchor Status` column filter provides the required status filtering.
- Add a note: `anchor_tx is blank until Stellar anchoring is implemented in D5.`
- If no batches exist, write headers and a “No evidence batches matched the export filter.” note; do not create an empty table.

#### openpyxl filtering limitation

`openpyxl` does not create native Excel slicer objects. The generated workbook uses Excel Table auto-filters for `date` and `anchor_status`. If native slicers are required, they are a manual post-generation enhancement and must not be represented as generated automation. This limitation should be stated in `docs/REGULATORY_WORKBOOK.md`.

### 6.6 Documentation requirements

`docs/REGULATORY_WORKBOOK.md` must cover:

- Purpose and narrowed scope: cryptographic provenance audit, not a financial dashboard.
- Exact limitation text and what data is absent from the current schema.
- Quick start: install dependencies, run `python scripts/export_evidence_for_excel.py`, optional `--database-url`, `--output-dir`, `--start`, `--end`.
- Outputs: CSV path, workbook path, and that generated files are untracked.
- Page-by-page guide for all four pages.
- Definition of `Integrity Status`: `✓ Verified` means the screening hash verifies against the stored batch Merkle root and the batch's stored leaf count matches; `✗ Failed` means tampering or inconsistency was detected. A single tampered leaf invalidates its whole batch.
- CSV data dictionary with all nine columns.
- Refresh process: rerun the script; there is no Power Query or live Excel connection. Manual workbook edits are overwritten on refresh.
- D5 anchoring status: `anchor_status` and blank `anchor_tx`.
- Independent verification guidance using the D2 Merkle proof/verify behavior.
- Security/privacy: exports contain hashes and no operator/PII/financial fields; keep generated files untracked.
- MIT licensing statement for the workbook, export script, and documentation; clarify that the ODRM application retains its existing project license.

## 7. TDD Test Plan

Test file: `backend/tests/integration/test_evidence_export_script.py`  
Marker: `pytest.mark.integration`

Test setup:

- Create a temporary SQLite database with `create_db_engine` and `Base.metadata.create_all`.
- Use `SqlAlchemyEvidenceRepository(session_factory, root_builder=merkle_root)`.
- Record five evidence rows through the repository using deterministic 32-byte input/output hashes and computed `screening_hash` values; no model inference or network calls.
- Batch 1: three rows at `2026-01-01T12:00:00Z`, `+1s`, `+2s`.
- Batch 2: two rows at `2026-01-02T12:00:00Z`, `+1s`.
- Import the script with `importlib.util` using the existing dataset-test pattern.
- Invoke `main(["--database-url", ..., "--output-dir", ..., ...])`.

Tests:

1. `test_export_script_produces_csv`
   - Exit code `0`.
   - `evidence_export.csv` exists with five data rows and two distinct batch IDs.
   - `regulatory_workbook.xlsx` exists and is a valid `.xlsx` file.
2. `test_export_respects_date_range`
   - With `--start 2026-01-02 --end 2026-01-02`, CSV has exactly the two batch-2 rows.
   - With no range, CSV has all five rows.
   - Date filtering does not change `leaf_index` for the selected rows.
3. `test_export_includes_all_required_columns`
   - CSV header equals `CSV_COLUMNS` exactly.
   - `anchor_tx` is present and empty.
   - No financial/operator/site columns are present.
4. `test_integrity_status_is_verified_for_valid_row`
   - All five rows report `verified`.
   - Every `leaf_index` is an integer within the stored batch `leaf_count`.
5. `test_integrity_status_is_failed_for_tampered_row`
   - Update one `screening_evidence.screening_hash` directly in SQLite without updating the batch root.
   - Rerun the export.
   - The tampered row reports `failed`; all rows in its batch report `failed`; the other batch remains `verified`.
6. Manual workbook review (CTO):
   - Open `exports/regulatory_workbook.xlsx`.
   - Confirm exactly four pages and the expected headers.
   - Confirm `Integrity Status` renders `✓ Verified` / `✗ Failed`.
   - Confirm the exact limitation text is present on page 1.
   - Confirm weekly and batch-size charts exist and contain no financial data.
   - Confirm Scenario Comparison formulas resolve for the prefilled hashes.
   - Confirm Evidence Trail has one row per batch and blank `anchor_tx`.
   - Confirm no live connections or external data prompts.

## 8. Commit Message

```text
feat(reporting): add cryptographic provenance workbook and export script
```

## 9. Audit Protocol

### Phase 3 — implementation audit

- Write the named tests first and confirm they fail for the expected reason.
- Implement the script, workbook builder, and documentation.
- Run focused tests: `python -m pytest tests/integration/test_evidence_export_script.py -q`.
- Run the full backend suite: `python -m pytest -q`.
- Run Ruff and mypy using the project-standard commands; fix all findings.
- Generate a temporary export and perform the manual workbook review.
- Report file diffs, test counts, dependency changes, and the manual review result to the CTO.
- Do not commit until Phase 3 is approved.

### Phase 4 — CTO delivery audit

- Confirm only authorized files changed: script, documentation, test, `pyproject.toml`, `requirements.txt`, `.gitignore`.
- Confirm no backend/API/schema/migration/frontend changes.
- Inspect the CSV header and sample rows against the exact schema.
- Verify `integrity_status` is computed against stored batch roots, including the tamper test result.
- Confirm the workbook has four pages, the exact limitation text, no financial/operator/site data, and no live Power Query connection.
- Confirm generated CSV/XLSX files are untracked and ignored where required.
- Confirm `openpyxl` is in both dependency files and the lock/requirements state is reproducible.
- Confirm documentation covers MIT licensing, refresh-by-rerun, Integrity Status semantics, and D5 anchoring status.
- Commit with the exact message above and push only after CTO approval.

## 10. Out of Scope

- ROI, payback, CO2, NPV, IRR, or any financial modeling.
- Operator, site, state, or other metadata absent from the current evidence schema.
- Stellar anchoring implementation or real `anchor_tx` values (D5).
- Live Power Query, external data connections, or automatic Excel refresh.
- Next.js portfolio dashboard or Sprint 12 financial reporting.
- Power BI, Tableau, or other BI integrations.
- Backend model, migration, repository, service, API, or frontend behavior changes.
- Native Excel slicer automation; table auto-filters are the generated mechanism.
- Committing generated CSV or XLSX artifacts.
