# Regulatory Provenance Workbook

## Purpose

The ODRM regulatory workbook is a reproducible audit artifact for screening
evidence. It lets an operator or regulator inspect stored screening hashes,
confirm Merkle-tree integrity, and trace each screening back to its evidence
batch.

The workbook is a **cryptographic provenance audit tool**, not a financial
dashboard. Financial portfolio reporting, operator metadata, site metadata,
ROI, payback, and CO2 analysis are deferred to Sprint 12 and are not part of
D2a.

## Scope and limitations

The current evidence schema does not store operator identity or contact data,
site metadata, capital or operating costs, production volumes, revenue, ROI,
payback period, NPV, IRR, or CO2 accounting. Those fields cannot be exported or
reported from the existing database.

The exact data-source limitation shown in the workbook is:

> Financial data (ROI, payback, CO2) and operator metadata are not stored in the
> current evidence schema. This workbook is a cryptographic provenance audit tool.

The workbook therefore reports only what the evidence ledger can prove:
screening hashes, batch membership, Merkle roots, leaf counts, integrity status,
and current anchoring status.

## Quick start

Install the project dependencies from the repository root:

```bash
python -m pip install -r requirements.txt
```

For an editable development install:

```bash
python -m pip install -e ".[dev]"
```

Generate both outputs with the default database setting:

```bash
python scripts/export_evidence_for_excel.py
```

The default database URL is `ODRM_DATABASE_URL` via project settings, falling
back to `sqlite:///./odrm.db`. Override it when needed:

```bash
python scripts/export_evidence_for_excel.py \
  --database-url sqlite:///./odrm.db \
  --output-dir exports
```

Filter by screening date using inclusive UTC dates:

```bash
python scripts/export_evidence_for_excel.py \
  --start 2026-01-01 \
  --end 2026-01-31
```

`--start` is the inclusive lower bound. `--end` is the inclusive upper bound;
the script converts it internally to an exclusive next-day boundary. If both are
provided, `--start` must be on or before `--end`.

## Outputs

| Output | Default path | Purpose |
| --- | --- | --- |
| CSV export | `exports/evidence_export.csv` | Exact row-level evidence contract |
| Excel workbook | `exports/regulatory_workbook.xlsx` | Four-page regulator-facing audit view |

Both files are generated runtime artifacts and must remain untracked. The
repository ignores CSV files with `*.csv` and the workbook with `exports/*.xlsx`.

The script writes the CSV first and then builds the workbook by reading that CSV
back with `csv.DictReader`. The workbook therefore has no direct database
dependency and no hidden data source.

## Workbook pages

### Operator Screening

This is the row-level evidence view. It has the columns `Date`,
`Screening Hash`, `Batch ID`, `Integrity Status`, and `Leaf Index`.

`Date` is written as an Excel datetime in UTC with the number format
`yyyy-mm-dd hh:mm:ss`. `Integrity Status` displays `✓ Verified` in green or
`✗ Failed` in red. The sheet is frozen at `A2`, includes the `OperatorScreening`
Excel table with striped rows and auto-filter, and shows the exact data-source
limitation below the table.

If the filter matches no rows, the page shows the headers, a no-results note, and
the limitation text. No empty Excel table is created.

### Portfolio Summary

This page contains only two evidence-derived summaries:

- Screenings per week, grouped by ISO week and labelled with the Monday of that
  week, in the `WeeklyScreenings` table and a line chart.
- Batch sizes, deduplicated by batch ID, in the `BatchSizes` table and a bar
  chart. Charts use short batch labels; full batch IDs remain in the CSV and the
  `Evidence Trail` page.

There are no ROI, payback, CO2, operator, site, or other financial metrics on
this page. The chart note states that charts are generated from
`evidence_export.csv` and that rerunning the export refreshes them.

### Scenario Comparison

This page is a formula-driven lookup, not a financial scenario model. Rows 2 and
3 are two screening-hash inputs. The first two distinct screening hashes in the
CSV are prefilled when available. The dropdown list is sourced from the
`Screening Hash` column on `Operator Screening`.

For each input, VLOOKUP formulas return the batch ID, integrity status, and leaf
index from `Operator Screening`. A COUNTIF formula confirms whether the hash is a
member of the batch. Missing hashes resolve to `Not found`. If no screening rows
exist, the page shows the headers and `No screening hashes available.` without
formulas or validation.

### Evidence Trail

This page has one row per batch, in first-appearance order: `Batch ID`,
`Leaf Count`, `Merkle Root`, `Anchor Status`, and `Anchor Tx`.

The Merkle root is displayed in shortened form as the first 16 characters, an
ellipsis, and the last 8 characters. The full 64-character root is attached as a
cell comment. The page uses the `EvidenceTrail` Excel table, whose `Anchor Status`
auto-filter provides status filtering.

`Anchor Tx` is always blank until Stellar anchoring is implemented in D5. If no
batches match, the page shows the headers and a no-results note without an empty
table.

## Integrity Status

`✓ Verified` means all of the following are true:

- The screening hash is present at the reported zero-based `leaf_index` in the
  full batch.
- The Merkle proof for that leaf recomputes to the stored batch Merkle root.
- The stored batch leaf count equals the full number of leaves in the batch.
- Every leaf in the batch belongs to that batch.

`✗ Failed` means tampering or inconsistency was detected. A single altered
screening hash, Merkle root, or leaf count invalidates the whole batch, so every
exported row from that batch reports `failed`. This is intentional.

Date filtering changes only which rows are written to the CSV. It does not
rebuild the Merkle tree from the filtered subset. A date-filtered row can
therefore report `failed` because of tampering in another, unexported row of the
same batch.

## CSV data dictionary

| Column | Type | Description |
| --- | --- | --- |
| `date` | string | Screening creation time, ISO-8601 UTC with `Z` suffix |
| `screening_hash` | string | Lowercase 64-hex screening hash |
| `batch_id` | string | Evidence batch identifier |
| `leaf_index` | integer | Zero-based position in the full batch ordered by `(created_at ASC, id ASC)` |
| `integrity_status` | string | `verified` or `failed` |
| `merkle_root` | string | Stored full 64-hex batch Merkle root |
| `leaf_count` | integer | Stored batch leaf count |
| `anchor_status` | string | Stored anchoring status (`pending`, `anchored_on_soroban`, or `verified`) |
| `anchor_tx` | string | Empty until D5 Stellar anchoring supplies a transaction reference |

The CSV is UTF-8 with a header row and `\n` line endings. If no rows match, the
file contains the header only.

## Refresh process

Rerun the export script to refresh both outputs:

```bash
python scripts/export_evidence_for_excel.py
```

There is no Power Query, external data connection, or live Excel link to the
database. The workbook is rebuilt from the CSV on every run. Manual edits to
either generated file are overwritten by the next refresh. The workbook requests
a full calculation on open so the `Scenario Comparison` formulas resolve.

## Anchoring status (D5)

The evidence schema currently records `anchor_status` and does not record a
Stellar transaction reference. The `anchor_status` values are `pending`,
`anchored_on_soroban`, and `verified`, as stored in the evidence batch.

`anchor_tx` is intentionally blank in this phase. A blank value does not prove
that anchoring failed; it means the reference field is not implemented until D5.
Do not infer an on-chain transaction from this workbook alone.

## Independent verification

The D2 Merkle behavior can be reproduced independently from the full ordered
leaf list:

```python
from odrm.evidence.service import merkle_proof, merkle_root, verify_merkle_proof

# Use every leaf in the batch, not only the date-filtered CSV rows.
hashes = [leaf.screening_hash for leaf in full_batch_leaves]
leaf_index = ...
proof = merkle_proof(hashes, leaf_index)
root = merkle_root(hashes)

assert verify_merkle_proof(
    hashes[leaf_index],
    proof,
    root,
    leaf_index,
    len(hashes),
)

# Compare root and len(hashes) to evidence_batches.merkle_root and
# evidence_batches.leaf_count for the batch.
```

`EvidenceService.verify()` recomputes the root from the current leaves and does
not compare it to the stored batch row. The export does that comparison, which is
what makes tamper detection meaningful. Auditors should compare the independently
recomputed root and leaf count with the stored batch values as well.

## Security and privacy

The CSV and workbook contain screening hashes, batch identifiers, Merkle roots,
leaf counts, integrity status, and anchoring status. They contain no operator
identity, site metadata, PII, financial values, or CO2 data.

Treat exports as sensitive audit artifacts even though they contain hashes rather
than raw inputs. Keep `exports/` untracked, restrict access to the files, and do
not attach them to public issues without review.

## Excel filtering limitation

`openpyxl` does not create native Excel slicer objects. The generated workbook
uses Excel Table auto-filters, including the `Anchor Status` filter on
`Evidence Trail`. If native slicers are required, they are a manual
post-generation enhancement and are not generated by this script.

## License

The contents of this document, `scripts/export_evidence_for_excel.py`, and the
generated workbook output are made available under the MIT License
(SPDX-License-Identifier: MIT).

This does not change the license of the ODRM application. The application retains
its existing project licensing; refer to the repository `LICENSE` file and the
`license` field in `pyproject.toml`. This document does not relicense application
source code.
