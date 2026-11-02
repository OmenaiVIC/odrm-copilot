# Sprint 1 Plan — Data Engineering (The Foundation)

**Project:** ODRM-Copilot (Syngas Shovel)
**Sprint:** 1 — Data Engineering
**Owner:** CTO / Systems Architect
**Status:** 🟡 Awaiting review — execution blocked until approval
**Date:** 2026-11-02
**Approval phrase:** `AUTHORIZED: Sprint 1 implementation phase`

---

## 0. Sprint Charter

Sprint 1 creates the trustworthy data foundation for Sprint 2's surrogate model: a
deterministic 10,000-row synthetic ODRM dataset, a strict Pandas validator that
enforces the `odrm_v1` contract and physics bounds, and the provenance needed to
reproduce both.

The dataset is **synthetic**. It is not experimental data, not HYSYS output, and not
COMSOL output. It must never be presented as equivalent to those tools.

### In scope

- `backend/src/odrm/data/schema.py`: contract constants, typed exceptions, and
  `validate_odrm_frame()`.
- `backend/src/odrm/data/synthetic.py`: pure, testable synthetic-data generation
  helpers.
- `scripts/generate_odrm_data.py`: thin CLI wrapper that generates, validates, and
  writes the dataset.
- A 10,000-row Parquet dataset with a content hash and manifest.
- `jsonschema`-based validation of `data/schemas/odrm_v1.json` itself (S0-F2).
- Unit and integration tests for contract drift, bounds, derived columns, determinism,
  physics trends, and artifact provenance.
- `docs/SPRINT_1_REPORT.md` at Phase 5, plus the minimum README command updates.

### Explicitly out of scope (deferred)

- XGBoost training, `/api/predict`, model artifacts, R² gates.
- LangChain agent, tool calling, prompt design.
- Frontend/UI changes.
- Optimization engine, techno-economic model, plant deployment.
- Real experimental data, HYSYS exports, COMSOL exports, or any claim of simulator
  equivalence.
- Changing `data/schemas/odrm_v1.json` or its `v1` contract.
- Database ingestion, cloud storage, auth, billing, CI secrets.
- Dropping `quality_flag == "rejected"` rows for training. That filter belongs to the
  Sprint 2 training pipeline.

### Deliverables checklist (exit criteria)

| # | Deliverable | Verification |
|---|---|---|
| 1 | `backend/src/odrm/data/schema.py` with `REQUIRED`, `BOUNDS`, `RISK_THRESHOLDS`, typed exceptions, `validate_odrm_frame()` | Validator tests pass; no silent clamping |
| 2 | `backend/src/odrm/data/synthetic.py` with deterministic, element-conserving generation | Generator unit tests pass |
| 3 | `scripts/generate_odrm_data.py` CLI | `--n 10000 --seed 7` produces a valid dataset and manifest |
| 4 | 10,000-row dataset, all rows valid, 29 columns | Validator passes; row count / uniqueness checks pass |
| 5 | `_manifest.json` with row count, SHA-256, schema version, generator, seed | Manifest hashes match files |
| 6 | `data/schemas/odrm_v1.json` validated with `jsonschema` | S0-F2 contract test passes |
| 7 | Test suite for schema, validator, generator, and artifacts | `pytest backend/tests -q` green |
| 8 | `docs/SPRINT_1_REPORT.md` | Reviewed at Phase 5 |

### Traceability

| Source | Deliverable |
|---|---|
| `MASTER_ROADMAP.md` Sprint 1.1 | Generator script |
| `MASTER_ROADMAP.md` Sprint 1.2 | 10,000-record dataset |
| `MASTER_ROADMAP.md` Sprint 1.3 | Strict validator |
| `ARCHITECTURE.md` §5.1–5.4 | Contract, storage, manifest, quality gates |
| `SPRINT_0_REPORT.md` S0-F2 | `jsonschema` validation of the schema file |
| `SPRINT_WORKFLOW.md` | Plan-first, TDD, review gate, report |

### Definition of Done (global)

Code review approved · lint clean (`ruff`) · type check clean (`mypy`) · tests green ·
docs updated · no secrets committed · reproducible from a clean venv.

### CTO-approved scope additions

- `backend/src/odrm/data/synthetic.py` — pure generation module, approved to improve testability and separate pure logic from the CLI wrapper.
- `pyproject.toml` mypy target change to include `scripts/` — approved so the generator CLI is type-checked rather than excluded.

---

## 1. Source of Truth and Modelling Stance

### 1.1 Contract

`data/schemas/odrm_v1.json` is authoritative.

- JSON Schema 2020-12.
- **29 properties: 23 required, 6 optional.**
- `additionalProperties: false`.
- `schema_version` is the constant `"v1"`.
- `temperature_c` has a hard maximum of `1000`; the schema is authoritative, so
  exactly `1000` is accepted and anything above is rejected.
- Derived columns are recomputed, never trusted:
  `h2_co_ratio`, `syngas_yield_mol_per_mol_ch4`, `ch4_slip_pct`,
  `carbon_risk_class`.

The Python constants in `schema.py` must mirror the JSON Schema. A contract test
parses the JSON file and fails if the two drift.

### 1.2 Thesis basis

The thesis supplies the reaction network, reaction enthalpies, operating window, and
qualitative equilibrium trends. It does **not** provide a complete kinetic parameter
set or a numerical Gibbs-minimization solver.

| Thesis basis | Use in Sprint 1 |
|---|---|
| ODRM definition and feed-ratio effects (§2.4, §2.5.7) | Input sampling ranges and syngas trade-offs |
| DRM `CH4 + CO2 ⇌ 2CO + 2H2`, ΔH ≈ +247 kJ/mol | Primary endothermic syngas route |
| POM `CH4 + 0.5O2 → CO + 2H2`, ΔH ≈ −36 kJ/mol | Internal heat supply and O2 response |
| Methane cracking `CH4 → C + 2H2`, ΔH ≈ +75 kJ/mol | Carbon precursor; favoured at high temperature |
| Boudouard `2CO ⇌ CO2 + C`, ΔH ≈ −172 kJ/mol | Carbon precursor; favoured at low temperature |
| RWGS `CO2 + H2 ⇌ CO + H2O`, ΔH ≈ +41 kJ/mol | H2/CO tuning; excess CO2 lowers H2 |
| Complete oxidation `CH4 + 2O2 → CO2 + 2H2O`, ΔH ≈ −802 kJ/mol | Excess-O2 syngas penalty |
| Temperature window (§2.5.5) | Low conversion below ~700 °C; optimum ~800–900 °C |
| Pressure effect (§2.5.6) | Higher pressure suppresses DRM |
| Carbon tendency (§2.5.8) | Low T, high CH4, low CO2/O2 increase carbon |
| Simulation gap (§2.12.3) | HYSYS/HSC/COMSOL validation remains future work |

### 1.3 Modelling stance

Sprint 1 will use a **reduced-order thermodynamic surrogate**, not a full equilibrium
solver:

- Reaction extents for DRM, POM, steam reforming, RWGS, cracking, Boudouard, and
  complete oxidation.
- Extents are bounded functions of temperature, pressure, feed ratios, GHSV, and
  catalyst activity.
- Species are computed algebraically from extents, so elemental C/H/O closure is
  exact by construction.
- The model reproduces the thesis's qualitative directions and trade-offs, not
  quantitative equilibrium values.
- No proprietary simulator data is used or implied.

If the CTO requires a true Gibbs-minimization generator, that is a scope change and
must be approved explicitly (OQ-5).

### 1.4 Non-negotiables

- Invalid rows are rejected, never clamped or repaired.
- Required fields never contain nulls.
- Duplicate `run_id` values are rejected.
- The generator is deterministic for a given seed.
- The generator performs no network access.
- Tests use the existing network-blocking `conftest.py`.
- Generated artifacts are reproducible from generator, seed, and contract hash.

---

## 2. Data Contract and Physics Envelope

### 2.1 Column groups

| Group | Fields |
|---|---|
| Required provenance | `run_id`, `created_at`, `source`, `schema_version` |
| Required inputs | `catalyst`, `temperature_c`, `pressure_bar`, `ch4_o2_ratio`, `co2_ch4_ratio`, `h2o_ch4_ratio`, `ghsv_per_h` |
| Required outputs | `ch4_conversion`, `co2_conversion`, `o2_conversion`, `h2_yield_mol_per_mol_ch4`, `co_yield_mol_per_mol_ch4` |
| Required derived / quality | `h2_co_ratio`, `syngas_yield_mol_per_mol_ch4`, `ch4_slip_pct`, `carbon_deposition_mg_per_gcat`, `carbon_risk_class`, `balance_error_pct`, `quality_flag` |
| Optional | `reactor_id`, `catalyst_loading_wt_pct`, `n2_dilution_mol_pct`, `contact_time_ms`, `energy_input_kw`, `notes` |

### 2.2 Bounds

All bounds are inclusive unless stated otherwise.

| Field | Min | Max | Notes |
|---|---:|---:|---|
| `temperature_c` | 500 | 1000 | Hard cap; reject >1000 |
| `pressure_bar` | 1 | 30 | Near-atmospheric to moderate pressure |
| `ch4_o2_ratio` | 1.4 | 2.5 | Lower ratio means more O2 |
| `co2_ch4_ratio` | 0 | 1.5 | Generator samples 0.05–1.5 for ODRM relevance (OQ-3) |
| `h2o_ch4_ratio` | 0 | 1.5 | Steam is a secondary feed |
| `ghsv_per_h` | 1000 | 100000 | Log-uniform sampling |
| `catalyst_loading_wt_pct` | 0 | 20 | Optional/nullable |
| `n2_dilution_mol_pct` | 0 | 50 | Optional/nullable |
| `contact_time_ms` | >0 exclusive | — | Optional/nullable; no reactor volume exists (OQ-2) |
| `ch4_conversion` | 0 | 1 | Fraction |
| `co2_conversion` | 0 | 1 | Fraction |
| `o2_conversion` | 0 | 1 | Fraction |
| `h2_yield_mol_per_mol_ch4` | 0 | 4 | mol H2 / mol CH4 fed |
| `co_yield_mol_per_mol_ch4` | 0 | 4 | mol CO / mol CH4 fed |
| `h2_co_ratio` | 0 | — | Requires `co_yield > 0` |
| `syngas_yield_mol_per_mol_ch4` | 0 | 8 | `h2_yield + co_yield` |
| `ch4_slip_pct` | 0 | 100 | `(1 - ch4_conversion) * 100` |
| `carbon_deposition_mg_per_gcat` | 0 | 100 | Safety-critical |
| `energy_input_kw` | 0 | 100000 | Optional/nullable |
| `balance_error_pct` | −2 | 2 | Elemental closure tolerance |

### 2.3 Enums and constants

- `source`: `experimental`, `aspen_hysys`, `comsol`, `synthetic`, `plant`.
- `catalyst`: `Ni/Al2O3`, `Ni-MgO`, `Rh`, `Pt`, `none`, `other`.
- `quality_flag`: `valid`, `suspect`, `rejected`.
- `schema_version`: constant `"v1"`.
- `created_at`: ISO 8601 UTC; validator normalizes to a UTC timestamp.
- `run_id`: valid UUID string; duplicate values rejected.

### 2.4 Derived columns

The validator recomputes these values from source columns and rejects mismatches:

```text
h2_co_ratio                 = h2_yield_mol_per_mol_ch4 / co_yield_mol_per_mol_ch4
syngas_yield_mol_per_mol_ch4 = h2_yield_mol_per_mol_ch4 + co_yield_mol_per_mol_ch4
ch4_slip_pct                = (1 - ch4_conversion) * 100
carbon_risk_class           = classify(carbon_deposition_mg_per_gcat)
```

Guard: `co_yield_mol_per_mol_ch4 > 0` is required for a finite H2/CO ratio. Rows with
zero CO need a contract decision (OQ-3); the Sprint 1 generator will avoid them.

Comparison tolerance: `rtol=1e-9`, `atol=1e-9` for numeric derived values. Carbon risk
classification is exact.

### 2.5 Carbon risk thresholds

The JSON Schema lists overlapping ranges. Sprint 1 resolves them as left-closed,
right-open intervals; a value exactly on a boundary belongs to the higher-risk class.

| Class | Interval (mg C / gcat) |
|---|---|
| `none` | `0 ≤ x < 1` |
| `low` | `1 ≤ x < 5` |
| `moderate` | `5 ≤ x < 20` |
| `high` | `x ≥ 20` |

This is a safety-conservative interpretation and needs CTO confirmation (OQ-4).

### 2.6 Contact-time caveat

`contact_time_ms` is described as "derived from GHSV", but GHSV alone does not
determine contact time without catalyst-bed volume, void fraction, or reactor
dimensions. No such field exists in `odrm_v1`.

Sprint 1 therefore emits `null` for `contact_time_ms` and only enforces
`contact_time_ms > 0` when a value is present. It does not claim to recompute it.
Resolving this properly requires a reactor-volume field or a removed derivation claim
(OQ-2).

### 2.7 Schema self-validation and dependency

S0-F2 is closed in Sprint 1 by adding `jsonschema` to the **dev** extra and testing:

- `Draft202012Validator.check_schema(schema)`.
- Required/property counts and optional/derived lists.
- Python constants match the JSON Schema.
- A representative record validates against the schema.

No runtime dependency is added unless the CTO asks for JSON-Schema validation at
request time (OQ-6). The Pandas validator remains the runtime gate.

---

## 3. Validator Design

### 3.1 Public API

`backend/src/odrm/data/schema.py` exposes:

```python
REQUIRED: dict[str, str]
BOUNDS: dict[str, tuple[float, float]]
RISK_THRESHOLDS: dict[str, tuple[float, float | None]]

class SchemaError(ValueError): ...
class BoundsError(ValueError): ...
class BalanceError(ValueError): ...

def validate_odrm_frame(df: pd.DataFrame) -> pd.DataFrame: ...
```

Supporting constants may include `OPTIONAL`, `ENUMS`, `DERIVED_COLUMNS`, and
`CARBON_RISK_CLASSES`.

### 3.2 Check order

1. Argument is a non-empty `pandas.DataFrame`; otherwise `SchemaError`.
2. Required columns present; optional columns allowed; unexpected columns rejected.
3. Required fields contain no nulls.
4. Numeric fields are finite and coerced to canonical floating dtypes; strings and
   enums are validated.
5. `run_id` values are valid UUIDs and unique.
6. `created_at` values parse as timezone-aware ISO 8601 timestamps.
7. Enums and `schema_version` constants match.
8. Numeric values are inside `BOUNDS`; violations raise `BoundsError`.
9. `balance_error_pct` is within ±2; violations raise `BalanceError`.
10. Derived columns are recomputed and compared; mismatches raise `SchemaError`.
11. Return a validated copy with canonical dtypes.

### 3.3 Return and mutation policy

- Never mutate the input frame.
- Never sort rows, change the index, drop rows, or rewrite values to fit bounds.
- Dtype coercion is allowed only on the returned copy.
- `quality_flag` is preserved. The validator does not drop `rejected` rows; that is a
  training-time filter (OQ-7).
- No file I/O and no network I/O.

### 3.4 Exception taxonomy

| Condition | Exception |
|---|---|
| Missing/extra column, bad null, bad dtype, bad enum, bad UUID/timestamp, duplicate ID, derived mismatch | `SchemaError` |
| Numeric value outside `BOUNDS` | `BoundsError` |
| `balance_error_pct` outside ±2 | `BalanceError` |

### 3.5 Not in the validator

- No train/test split.
- No outlier removal beyond contract bounds.
- No imputation.
- No `quality_flag` filtering.
- No Parquet writing.
- No schema migration.

---

## 4. Generator Design

### 4.1 CLI

`scripts/generate_odrm_data.py` is a thin wrapper around
`backend/src/odrm/data/synthetic.py`.

Proposed flags:

| Flag | Default | Purpose |
|---|---|---|
| `--n` | `10000` | Row count |
| `--seed` | `7` | Deterministic RNG seed |
| `--out-dir` | `data/processed/odrm/v1` | Canonical batch directory |
| `--compat-path` | `data/odrm_dataset.parquet` | Roadmap-compatible copy |
| `--created-at-base` | `2026-01-01T00:00:00Z` | Deterministic row timestamps |

Exit codes: `0` success or idempotent reuse; `2` validation failure; `3` artifact
conflict; `4` I/O failure. A JSON summary is printed to stdout; errors go to stderr.

### 4.2 Sampling

Use `numpy.random.Generator` with a local PCG64 generator; never touch global RNG
state. Use stratified Latin-hypercube-style sampling so the full operating envelope is
covered, not clustered by chance.

- `temperature_c`: uniform 500–1000 °C.
- `pressure_bar`: log-uniform 1–30 bar.
- `ch4_o2_ratio`: uniform 1.4–2.5.
- `co2_ch4_ratio`: uniform 0.05–1.5 (zero-CO2 edge deferred, OQ-3).
- `h2o_ch4_ratio`: uniform 0–1.0 (contract allows 1.5).
- `ghsv_per_h`: log-uniform 1,000–100,000 h⁻¹.
- `catalyst`: weighted `Ni/Al2O3`, `Ni-MgO`, `Rh`, `Pt`, `none`, `other`.
- `catalyst_loading_wt_pct`: 2–15 for active catalysts; null for `none`.
- `n2_dilution_mol_pct`: null for ~40% of rows; otherwise 0–30.
- `reactor_id`: synthetic identifiers such as `SYN-R-001`.
- `energy_input_kw`: optional heat-duty proxy, bounded 0–100,000.
- `notes`: null.
- `quality_flag`: `valid` for every production row.
- `source`: `synthetic`.
- `schema_version`: `v1`.

`run_id` is a deterministic UUIDv5 derived from generator version, seed, and row index.
`created_at` is `created_at_base + index seconds`, not wall-clock time, so the dataset
bytes are reproducible.

### 4.3 Physics surrogate

For a 1 mol CH4 feed basis:

1. Compute reaction extents for DRM, POM, steam reforming, RWGS, cracking, Boudouard,
   and complete oxidation.
2. Each extent is the product of:
   - catalyst activity factor,
   - GHSV/contact-efficiency factor,
   - a bounded saturation of the thermodynamic driving force,
   - a limiting-reactant cap.
3. Compute outlet CH4, CO2, O2, H2, CO, H2O, and solid C algebraically from the
   extents.
4. Derive conversions and yields from the outlet species.
5. Recompute all derived columns from the generated source columns.

Required qualitative behavior:

- Temperature increases DRM/POM/cracking and suppresses Boudouard carbon.
- Pressure suppresses DRM because the reaction increases gas moles.
- Excess CO2 promotes DRM/RWGS, lowers H2/CO, and gasifies carbon.
- Excess O2 first promotes POM, then complete oxidation and a syngas penalty.
- Steam promotes steam reforming/WGS and raises H2.
- Higher GHSV reduces approach to equilibrium and conversion.
- Catalyst activity orders `Rh`/`Pt` above `Ni/Al2O3`; `none` is lowest.
- `Ni-MgO` is more carbon-resistant than `Ni/Al2O3` at comparable conditions.

### 4.4 Carbon and balance

- Carbon is a proxy from cracking + Boudouard − reverse-Boudouard gasification,
  scaled to `mg C / gcat` with a documented nominal catalyst-mass basis.
- Carbon is bounded 0–100 and classified by `RISK_THRESHOLDS`.
- The absolute carbon magnitude is synthetic; only relative trends and risk classes
  are tested.
- `balance_error_pct` is computed from C/H/O atom closure on the 1 mol CH4 basis.
  Default target is `< 1e-6` (floating-point noise only). If a future noise model is
  added, rows above ±2% must be regenerated, never clamped.

### 4.5 Provenance

- `source` is always `synthetic`.
- `run_id` is deterministic and unique.
- `created_at` is deterministic for a given seed and base timestamp.
- The generator version is recorded in the manifest.
- The contract path and SHA-256 are recorded in the manifest.

### 4.6 Artifact layout and manifest

Canonical output:

```text
data/processed/odrm/v1/
  <batch_id>.parquet
  _manifest.json
```

`batch_id` is `synthetic-v1-<sha256[:16]>`, derived from the Parquet bytes. The batch
file is immutable: if the same content already exists, reuse it; if the path exists
with a different hash, abort.

Proposed `_manifest.json` is a batch index with one entry per generated batch:

```json
{
  "schema_version": "v1",
  "contract": {
    "path": "data/schemas/odrm_v1.json",
    "sha256": "<contract-sha256>"
  },
  "batches": [
    {
      "batch_id": "synthetic-v1-<sha16>",
      "file": "synthetic-v1-<sha16>.parquet",
      "sha256": "<parquet-sha256>",
      "row_count": 10000,
      "column_count": 29,
      "source": "synthetic",
      "generator": "scripts/generate_odrm_data.py",
      "generator_version": "1.0.0",
      "seed": 7,
      "created_at_base": "2026-01-01T00:00:00Z",
      "generated_at": "<first-generation UTC timestamp>",
      "compat_path": "data/odrm_dataset.parquet",
      "compat_sha256": "<parquet-sha256>"
    }
  ]
}
```

Writes are atomic (temp file + replace). The manifest index may be rewritten to add a
new batch; batch Parquet files are never overwritten.

### 4.7 Storage resolution

The roadmap names `data/odrm_dataset.parquet`; the architecture names immutable
batches under `data/processed/odrm/v1/`.

Proposed resolution:

- The canonical scientific artifact is the immutable batch under `data/processed/`.
- `data/odrm_dataset.parquet` is a byte-identical compatibility copy for the roadmap
  path and Sprint 2 convenience.
- The manifest records both hashes; the compatibility copy is not a second scientific
  artifact.
- Generated artifacts are **not committed by default**; they are reproducible from the
  generator, seed, and contract. If the CTO requires a versioned binary, OQ-1 must be
  approved and `.gitignore` changed narrowly.

Sprint 1 implementation will add these narrow `.gitignore` entries only:
`data/processed/odrm/` and `data/odrm_dataset.parquet`. No other `data/` paths are
ignored. `data/schemas/odrm_v1.json` and committed reference data remain tracked.

### 4.8 Failure behavior

- Generation is all-or-nothing: validate before writing.
- A validation failure writes no dataset and no manifest.
- Existing canonical batches are never silently overwritten.
- The compatibility copy is replaced atomically only after a new canonical batch
  validates.
- The CLI is safe to run from the repository root under Windows PowerShell.

---

## 5. TDD and Test Matrix

Tests are written first, observed to fail for the expected reason, then implemented.
The existing `backend/tests/conftest.py` fixtures and network block are reused.

### 5.1 Test files

| File | Purpose |
|---|---|
| `backend/tests/unit/test_schema_contract.py` | JSON Schema self-validation and constant drift |
| `backend/tests/unit/test_schema_validation.py` | Validator happy path and every failure class |
| `backend/tests/unit/test_synthetic_generator.py` | Determinism, sampling, physics trends, balance |
| `backend/tests/integration/test_dataset_artifacts.py` | CLI, Parquet, manifest, hashes, idempotence |

### 5.2 Contract tests

- `odrm_v1.json` passes `Draft202012Validator.check_schema`.
- Property count is 29; required count is 23.
- Optional list matches the six nullable columns.
- Derived list matches the four derived columns.
- `additionalProperties` is false and `schema_version` is const `"v1"`.
- `REQUIRED`, `BOUNDS`, and `RISK_THRESHOLDS` in `schema.py` match the JSON file.
- Every schema property appears in exactly one of required/optional.
- A representative valid record validates against the JSON Schema.
- No network access is attempted.

### 5.3 Validator tests

- Valid fixture passes and returns a copy.
- Input frame is byte-for-byte unchanged after validation.
- Missing required column, extra column, null required value, bad dtype, bad enum,
  bad UUID, naive timestamp, and duplicate `run_id` raise `SchemaError`.
- Optional nulls are accepted.
- Every numeric bound has a below-minimum and above-maximum rejection, plus an
  inclusive boundary acceptance where applicable.
- `temperature_c = 1000` passes; `1000.0001` raises `BoundsError`.
- `balance_error_pct = ±2` passes; `±2.0001` raises `BalanceError`.
- Derived-value mismatches raise `SchemaError`.
- Carbon-risk boundaries at 1, 5, and 20 map to the higher-risk class.
- `co_yield = 0` is rejected pending OQ-3.
- `NaN` and `inf` are rejected.
- A `quality_flag = "rejected"` row is not silently dropped.

### 5.4 Generator tests

- Same seed produces identical frames and identical Parquet hashes.
- Different seed produces different data.
- Row and column counts are correct; required fields are never null.
- Every generated row passes `validate_odrm_frame`.
- No duplicate `run_id` values.
- All four carbon-risk classes are represented in the 10,000-row acceptance dataset.
- Temperature sweep: CH4 conversion and syngas yield increase; carbon tendency falls.
- Pressure sweep: CH4 conversion is non-increasing.
- CO2/CH4 sweep: CH4 conversion rises; H2/CO falls; carbon falls.
- O2 sweep: syngas yield has an interior optimum, with a penalty at excess O2.
- GHSV sweep: conversions fall as GHSV rises.
- Catalyst activity ordering and Ni-MgO carbon resistance hold on controlled cases.
- Elemental balance is within `1e-6` for every row.
- No constant feature columns; all four risk classes and the full temperature range
  are covered.

Tests assert directions and constraints, not exact calibrated numbers.

### 5.5 Artifact tests

- CLI writes the canonical Parquet, `_manifest.json`, and compatibility copy.
- Parquet shape is `(n, 29)`; columns and dtypes match the contract.
- Manifest row count, column count, seed, generator, and schema version are correct.
- Manifest SHA-256 matches the actual Parquet bytes.
- Contract SHA-256 matches `data/schemas/odrm_v1.json`.
- Compatibility copy is byte-identical to the canonical batch.
- Rerunning with the same seed reuses the same batch and does not duplicate files.
- A different seed creates a new batch entry and updates the compatibility copy
  atomically.
- Validation failure writes no artifact.
- Tests use `tmp_path`; they never write into the repository's real `data/` tree.

### 5.6 Quality targets

- All tests green with `pytest backend/tests -q`.
- `odrm/data/schema.py` line coverage ≥90%.
- Generator CLI exercised end-to-end.
- No `DeprecationWarning` from `odrm.*` (existing pytest filter).
- 10,000-row dataset accepted with zero invalid rows.

---

## 6. Implementation Sequence and Commits

Only after approval. Each step is test-first and committed only if the CTO authorizes
commits under the workflow.

| Step | Work | Commit message (proposed) |
|---|---|---|
| 1 | Add `jsonschema` dev dependency; contract tests | `test(data): lock ODRM v1 contract` |
| 2 | Add schema constants and exceptions | `feat(data): add ODRM schema constants` |
| 3 | Implement structural/null/dtype/enum validation | `feat(data): validate ODRM structure` |
| 4 | Implement bounds, balance, duplicates | `feat(data): enforce ODRM bounds` |
| 5 | Implement derived-column and risk checks | `feat(data): validate derived ODRM fields` |
| 6 | Add deterministic sampler and reaction-extent surrogate | `feat(data): add synthetic ODRM generator` |
| 7 | Add Parquet batch, manifest, compatibility copy | `feat(data): write ODRM batches with manifests` |
| 8 | Generate and verify the 10,000-row dataset | `data: generate ODRM v1 synthetic dataset` |
| 9 | Update README and write Sprint 1 report | `docs: add Sprint 1 report` |

If generated data is not committed (default), step 8 produces local artifacts and
commits the generator/tests only; the report records the hashes.

### 6.1 Documentation

- README: add generation, validation, and test commands.
- `docs/SPRINT_1_REPORT.md`: built items, coverage/pass rates, deviations, known
  issues, artifact hashes, and open debt.
- `docs/ARCHITECTURE.md`: only if OQ-1 or OQ-2 changes the agreed storage/contact-time
  policy.

### 6.2 Local commands

PowerShell from the repository root, using the project venv:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_schema_contract.py -q
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_schema_validation.py -q
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_synthetic_generator.py -q
.\.venv\Scripts\python.exe -m pytest backend/tests/integration/test_dataset_artifacts.py -q
```

---

## 7. Acceptance and Audit Evidence

The sprint is accepted only with raw terminal evidence, not a summary.

### 7.1 Full gate

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
.\.venv\Scripts\python.exe -m ruff check backend scripts
.\.venv\Scripts\python.exe -m ruff format --check backend scripts
.\.venv\Scripts\python.exe -m mypy backend/src scripts
```

Mypy target will be adjusted from `packages = ["odrm"]` to include the CLI script, so
the generator is type-checked rather than excluded.

### 7.2 Dataset acceptance

```powershell
.\.venv\Scripts\python.exe scripts\generate_odrm_data.py --n 10000 --seed 7 `
  --out-dir data\processed\odrm\v1 --compat-path data\odrm_dataset.parquet
```

Then verify:

```powershell
.\.venv\Scripts\python.exe -c "import pandas as pd; df=pd.read_parquet('data/odrm_dataset.parquet'); print(df.shape); print(df['run_id'].nunique()); print(df.isna().sum()); print(df['carbon_risk_class'].value_counts(dropna=False))"
.\.venv\Scripts\python.exe -c "import json,pathlib; print(json.dumps(json.loads(pathlib.Path('data/processed/odrm/v1/_manifest.json').read_text()), indent=2))"
.\.venv\Scripts\python.exe -c "import hashlib,pathlib; p=pathlib.Path('data/odrm_dataset.parquet'); print(hashlib.sha256(p.read_bytes()).hexdigest())"
```

Required evidence:

- 10,000 rows; 29 columns; 10,000 unique `run_id`; zero nulls in required fields.
- All four carbon-risk classes present.
- Manifest SHA-256 equals the recomputed Parquet hash.
- Contract SHA-256 equals the recomputed schema-file hash.
- Same seed rerun produces the same batch hash.
- No network access during tests or generation.
- `git status --short` shows only expected files.

### 7.3 Phase 5 report

`docs/SPRINT_1_REPORT.md` must include:

- What was built.
- Test counts, pass rate, and coverage for `odrm/data/schema.py`.
- Dataset row count, column count, risk-class distribution, and SHA-256.
- Commands run and their raw outcomes.
- Deviations from this plan.
- Known issues, limitations, and follow-ups.
- Confirmation that no schema or architecture contract was silently changed.

---

## 8. Risks and Mitigations

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Synthetic data mistaken for validated physics | High | High | Label `source=synthetic`; document limits; no simulator-equivalence claims; future HYSYS/COMSOL validation |
| R2 | Reduced-order surrogate produces implausible trends | Medium | High | Reaction extents; monotonic/trend tests; thesis review; explicit OQ-5 |
| R3 | Python constants drift from JSON Schema | Medium | Medium | Contract test parses schema and compares counts, bounds, enums, thresholds |
| R4 | Roadmap and architecture storage paths diverge | Medium | Low | Canonical batch + byte-identical compatibility copy; manifest records both |
| R5 | `jsonschema` missing from dependencies | Low | Low | Add to dev extra; install in the acceptance venv |
| R6 | Zero CO makes H2/CO undefined | Medium | Medium | Generator avoids zero CO; validator rejects; OQ-3 for contract decision |
| R7 | Contact time cannot be derived without reactor volume | Medium | Low | Emit null; validate only if present; OQ-2 |
| R8 | Generated data accidentally committed | Medium | Low | Default: do not commit artifacts; OQ-1 if CTO wants a versioned binary |
| R9 | Windows paths or encoding break writes | Low | Low | `pathlib`, UTF-8, atomic writes, PowerShell-safe commands |
| R10 | Test suite writes into repository data | Medium | Medium | All artifact tests use `tmp_path` |
| R11 | Synthetic model overfits Sprint 2 to unrealistic distribution | High | Medium | Broad stratified coverage; report limitation; future real/simulator data |
| R12 | Silent clamping hides bad data | Low | High | Validator rejects; tests assert no mutation and no clamping |

---

## 9. Assumptions

- Sprint 0 is accepted and `odrm_v1.json` is frozen at `v1`.
- The thesis reaction network and qualitative trends are an acceptable basis for a
  synthetic training set.
- 10,000 rows are sufficient for Sprint 2's initial surrogate; no train/test split is
  produced in Sprint 1.
- No real plant, experimental, HYSYS, or COMSOL data is available or required.
- `jsonschema` is approved as a dev-only dependency.
- Python 3.11.9 in `.venv` is the execution environment.
- Generated Parquet artifacts are reproducible and are not committed by default.
- `quality_flag` filtering is a Sprint 2 training concern, not a validator concern.
- No schema migration is performed in Sprint 1.

---

## 10. Open Questions (CTO Decisions)

| ID | Question | Recommendation | Impact if unresolved | CTO decision |
|---|---|---|---|---|
| OQ-1 | Should the 10,000-row dataset be committed, or generated and ignored? Should `_manifest.json` be an index or one manifest per batch? | Generate, do not commit; canonical batch + compatibility copy; manifest index with one entry per batch | Release packaging and Sprint 2 data availability | Approved as proposed (generate + ignore; canonical batch + compat copy; manifest index; `.gitignore` per §4.7). |
| OQ-2 | How should `contact_time_ms` be handled when no reactor-volume field exists? | Emit null; validate >0 only if present; revisit schema if reactor volume is added | Schema description remains internally inconsistent | Approved as proposed. |
| OQ-3 | What is the contract for `co_yield = 0` and `co2_ch4_ratio = 0`, where H2/CO and CO2 conversion are undefined? | Generator samples `co2_ch4_ratio ≥ 0.05` and guarantees `co_yield > 0`; validator rejects zero-CO rows; revisit `v1` if zero-CO records are required | Dataset does not cover the exact zero edges | Approved with change — sample `co2_ch4_ratio` from 0.05, not 0.2. |
| OQ-4 | Do carbon-risk boundaries at 1, 5, and 20 belong to the lower or higher class? | Left-closed/right-open; boundary belongs to the higher-risk class | Label ambiguity in tests and downstream risk display | Approved as proposed. |
| OQ-5 | Is a reduced-order reaction-extent surrogate acceptable, or is a true Gibbs-minimization generator required now? | Reduced-order for Sprint 1; label limitations; full Gibbs/HYSYS later | Scope and scientific fidelity of the dataset | Approved as proposed — reduced-order surrogate; label prominently in `docs/SPRINT_1_REPORT.md`. |
| OQ-6 | Should `jsonschema` be dev-only or a runtime dependency? | Dev-only for contract tests; Pandas validator remains runtime | Packaging surface | Approved as proposed. |
| OQ-7 | Should `validate_odrm_frame()` drop `quality_flag == "rejected"` rows? | No; preserve rows; Sprint 2 training filters them | Validator/training boundary | Approved as proposed. |
| OQ-8 | Should the compatibility copy overwrite an existing `data/odrm_dataset.parquet` atomically? | Yes, after the canonical batch validates; old batches remain immutable | Rerun behavior | Approved as proposed. |

---

## 11. Approval Gate

This plan is the only Sprint 1 artifact created before authorization.

- No implementation code, tests, Parquet files, schema edits, or commits are made until
  the CTO replies with the exact phrase:

  `AUTHORIZED: Sprint 1 implementation phase`

- If the CTO requests changes, revise this plan first and stop again.
- If an open question changes the contract, update the plan and obtain a new approval
  before coding.
- On approval, implementation proceeds in the TDD order in §6 and reports through
  `docs/SPRINT_1_REPORT.md`.
