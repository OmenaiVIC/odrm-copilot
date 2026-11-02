# Sprint 1 — Data Validation & Synthetic Dataset: Review Note

| | |
|---|---|
| Status | **Complete** |
| Date | 2026-11-02 |
| Scope | ODRM v1 validator, deterministic synthetic generator, 10k-row dataset + manifest |
| Plan | [`SPRINT_1_PLAN.md`](SPRINT_1_PLAN.md) (CTO approved, `a769657`) |
| Workflow | [`SPRINT_WORKFLOW.md`](SPRINT_WORKFLOW.md) |
| Architecture | [`ARCHITECTURE.md`](ARCHITECTURE.md) |

No model training, API prediction endpoint, agent work, frontend change, or cloud
deployment was introduced. No real experimental, HYSYS, or COMSOL data was used.

---

## 1. Objectives vs. outcome

| Plan §6 step | Outcome |
|---|---|
| 1. `jsonschema` dev dependency + contract tests | Done — `569ea36`, closes S0-F2 |
| 2. Schema constants and exceptions | Done — `efc837a` |
| 3. Structural/null/dtype/enum validation | Done — `8ec2447` |
| 4. Bounds, balance, duplicate `run_id` | Done — `ac376c2` |
| 5. Derived columns and carbon-risk checks | Done — `605c566` |
| 6. Deterministic sampler + reaction-extent surrogate | Done — `8286524` |
| 7. Parquet batch, manifest, compatibility copy | Done — `c52c598` |
| 8. Generate and verify 10,000-row dataset | Done — local artifacts, hashes in §4 |
| 9. README + Sprint 1 report | Done — this note |

---

## 2. Environment

| Item | Value |
|---|---|
| OS / shell | Windows, PowerShell 5.1 |
| Python | 3.11.9 (`.venv`) |
| pandas / PyArrow / NumPy | 3.1.0 / 26.0.0 / 2.4.6 |
| scikit-learn / XGBoost | 1.9.1 / 3.2.0 (unused this sprint) |
| FastAPI / Pydantic | 0.162.0 / 2.14.2 |
| pytest / jsonschema | 9.2.0 / 4.26.0 |

---

## 3. Deliverables

### Validation (`backend/src/odrm/data/schema.py`)

- Contract constants mirroring `data/schemas/odrm_v1.json`: `REQUIRED` (23),
  `OPTIONAL` (6), `DERIVED_COLUMNS`, `ENUMS`, `BOUNDS`, `RISK_THRESHOLDS`,
  `SCHEMA_VERSION`.
- Typed failure classes (`SchemaError` and subclasses) for structure, nulls, dtypes,
  enums, bounds, balance, derived fields, duplicates, and risk labels.
- `validate_odrm_frame()` is non-mutating for values, rejects bad rows instead of
  clamping, and returns a canonicalized frame (categoricals, UTC timestamps).

### Generator (`backend/src/odrm/data/synthetic.py`)

- `generate_odrm_frame(n, seed, created_at_base)` and `simulate_point(...)`;
  `GENERATOR_VERSION = "1.0.0"`.
- Local `PCG64` generator with Latin-hypercube coverage of the v1 envelope; global
  RNG state is never touched.
- Reduced-order reaction-extent surrogate with CH₄/O₂ budgets and mass-balance
  closure; derived fields (`h2_co_ratio`, `syngas_yield_mol_per_mol_ch4`,
  `ch4_slip_pct`, `carbon_risk_class`) are computed consistently and validated.
- Every emitted row is `source=synthetic`, `schema_version=v1`; risk boundaries are
  left-closed/right-open per OQ-4.

### Artifact CLI (`scripts/generate_odrm_data.py`)

- Thin CLI (`--n`, `--seed`, `--out-dir`, `--compat-path`, `--created-at-base`).
- Generates → validates → writes an immutable
  `data/processed/odrm/v1/synthetic-v1-<sha256[:16]>.parquet`, atomically rewrites
  `_manifest.json`, and writes a byte-identical `data/odrm_dataset.parquet`.
- Reuses a batch when content matches; aborts with exit `3` if a batch or the
  recorded contract hash differs; exit `2` for validation failure and `4` for I/O.
- Manifest records schema version, contract path/hash, and per-batch row/column
  counts, generator + version, seed, timestamp base, and both hashes.

### Tests

- `backend/tests/unit/test_schema_contract.py` — Draft 2020-12 self-validation,
  counts, constant/bound/enum/risk drift (S0-F2).
- `backend/tests/unit/test_schema_validation.py` — happy path plus every failure
  class, no-clamping and no-mutation checks.
- `backend/tests/unit/test_synthetic_generator.py` — determinism, seed sensitivity,
  bounds/enums, balance, derived-field and physics-trend checks.
- `backend/tests/integration/test_dataset_artifacts.py` — CLI end-to-end, Parquet
  shape/dtypes, manifest metadata/hashes, byte-identical copy, idempotent reuse,
  seed append, validation-failure atomicity, tamper conflict, I/O failure. All
  artifact writes use `tmp_path`.

### Docs

- `README.md` — install, test, lint, type-check, and generation commands; synthetic
  data disclaimer.
- This report.

---

## 4. Dataset evidence

Command:

```powershell
.\.venv\Scripts\python.exe scripts\generate_odrm_data.py --n 10000 --seed 7
```

```json
{"batch_id": "synthetic-v1-65f9ab45c3641747", "column_count": 29,
 "compat_path": "data/odrm_dataset.parquet",
 "file": "synthetic-v1-65f9ab45c3641747.parquet",
 "out_dir": "data/processed/odrm/v1", "reused": false, "row_count": 10000,
 "seed": 7,
 "sha256": "65f9ab45c3641747d980f9641145a2a6665a6e73e432c628f24bb038586b69c5"}
```

| Item | Value |
|---|---|
| Rows × columns | `10000 × 29` |
| Unique `run_id` | `10000` |
| Required-field nulls | `0` |
| `source` | `synthetic` × 10000 |
| Parquet SHA-256 | `65f9ab45c3641747d980f9641145a2a6665a6e73e432c628f24bb038586b69c5` |
| Schema SHA-256 | `1ae139340befa4da32c1a7bd5955d8697f0a262e61313ed4964b9a9bf21f0224` |
| Compat copy | byte-identical to canonical batch |

Carbon-risk distribution:

| Class | Rows |
|---|---|
| `none` | 1,263 |
| `low` | 3,662 |
| `moderate` | 4,719 |
| `high` | 356 |

Intentional nulls (optional columns): `contact_time_ms` 10,000 (OQ-2, no reactor
volume), `notes` 10,000, `n2_dilution_mol_pct` 4,011, `catalyst_loading_wt_pct`
1,407. Coverage includes 12 reactor IDs, all catalyst classes, temperatures
500–1000 °C, pressures 1–30 bar, GHSV 1,000–100,000 h⁻¹.

Reproducibility: a fresh run into a temporary directory produced the same
`batch_id` and SHA-256 (`65f9ab45c3641747…`). `generated_at` is wall-clock on first
write and preserved on reuse; dataset bytes do not depend on it.

`_manifest.json`:

```json
{
  "batches": [
    {
      "batch_id": "synthetic-v1-65f9ab45c3641747",
      "column_count": 29,
      "compat_path": "data/odrm_dataset.parquet",
      "compat_sha256": "65f9ab45c3641747d980f9641145a2a6665a6e73e432c628f24bb038586b69c5",
      "created_at_base": "2026-01-01T00:00:00Z",
      "file": "synthetic-v1-65f9ab45c3641747.parquet",
      "generated_at": "2026-11-02T19:08:53.701438Z",
      "generator": "scripts/generate_odrm_data.py",
      "generator_version": "1.0.0",
      "row_count": 10000,
      "seed": 7,
      "sha256": "65f9ab45c3641747d980f9641145a2a6665a6e73e432c628f24bb038586b69c5",
      "source": "synthetic"
    }
  ],
  "contract": {
    "path": "data/schemas/odrm_v1.json",
    "sha256": "1ae139340befa4da32c1a7bd5955d8697f0a262e61313ed4964b9a9bf21f0224"
  },
  "schema_version": "v1"
}
```

---

## 5. Gate evidence

```
> .\.venv\Scripts\python.exe -m pytest backend/tests -q
114 passed in 4.40s

> .\.venv\Scripts\python.exe -m ruff check backend scripts
All checks passed!

> .\.venv\Scripts\python.exe -m ruff format --check backend scripts
24 files already formatted

> .\.venv\Scripts\python.exe -m mypy backend/src scripts
Success: no issues found in 13 source files
```

Coverage (`--cov=odrm.data.schema --cov=odrm.data.synthetic`, 114 tests):

```
schema.py     151 stmts   66 branch   97%   (missing 137-139)
synthetic.py  127 stmts    8 branch   97%   (missing 230, 234)
TOTAL         278 stmts   74 branch   97%
```

`odrm.data.schema` exceeds the plan's ≥90% target. No `odrm.*`
`DeprecationWarning` was observed. Tests and generation make no outbound network
calls (the suite's autouse blocker would fail otherwise). `git status --short`
shows only the README and this report before the docs commit; generated artifacts
are ignored by design.

---

## 6. Commit history

| Commit | Message |
|---|---|
| `569ea36` | `test(data): lock ODRM v1 contract` |
| `efc837a` | `feat(data): add ODRM schema constants` |
| `8ec2447` | `feat(data): validate ODRM structure` |
| `ac376c2` | `feat(data): enforce ODRM bounds` |
| `605c566` | `feat(data): validate derived ODRM fields` |
| `8286524` | `feat(data): add synthetic ODRM generator` |
| `c52c598` | `feat(data): write ODRM batches with manifests` |
| _this_ | `docs: add Sprint 1 report` |

Step 8 produced local artifacts only, per the approved no-commit decision (OQ-1);
its hashes are recorded above.

---

## 7. Deviations and decisions

1. **Integration tests load the CLI in-process.** `importlib` loads
   `scripts/generate_odrm_data.py` and calls `main(argv)` rather than spawning a
   subprocess. This exercises the full CLI path while keeping writes inside
   `tmp_path` and the runtime fast; exit codes, stdout JSON, and stderr messages are
   asserted.
2. **Contract path is repo-relative, with no `--contract` flag.** The CLI resolves
   `data/schemas/odrm_v1.json` from its own location so it works from any working
   directory, as required for a reproducible manifest hash.
3. **Extra safeguard: contract-drift refusal.** If an existing manifest records a
   different contract hash, the writer aborts with exit `3` instead of appending to
   a manifest that no longer describes the current `v1` contract.
4. **`quality_flag` is `valid` for all generated rows.** The generator does not
   synthesize rejected/suspect rows (OQ-7 keeps filtering out of the validator).
   Sprint 2's filter is therefore a no-op on this batch.
5. **`contact_time_ms` is entirely null** in this batch because no reactor-volume
   field exists (OQ-2); the validator accepts null and only checks positivity when
   present.
6. **No schema or architecture edits.** `git diff a769657..HEAD -- data/schemas
   docs/ARCHITECTURE.md` is empty; the `v1` contract and storage policy are
   unchanged.

---

## 8. Known issues, limitations, and follow-ups

**Scientific fidelity (prominent, per OQ-5).** The dataset is generated by a
reduced-order reaction-extent surrogate derived from the thesis reaction network,
not by Gibbs minimization, Aspen HYSYS, COMSOL, a pilot plant, or experiments. It is
fit for exercising the Sprint 2 pipeline and for qualitative trend tests, not for
validating reactor design or publishing kinetic claims. `source=synthetic` marks
every row. Future real/simulator data must be added as separate sources and the
surrogate re-validated against it.

- **Class imbalance.** `high` carbon risk is 3.6% of rows; Sprint 2 must stratify or
  weight rather than assume balance.
- **No degenerate-edge coverage.** `co2_ch4_ratio` starts at 0.05 and `co_yield > 0`
  is guaranteed (OQ-3), so exact zero-CO behavior is untested by this dataset.
- **Optional sparsity.** `contact_time_ms` and `notes` carry no information yet;
  `n2_dilution_mol_pct` and `catalyst_loading_wt_pct` are partially null. Sprint 2
  feature handling must tolerate nulls.
- **Single seed artifact.** Only seed `7` is materialized; other seeds are covered by
  tests but not stored.
- **No train/test split** was produced (by design); Sprint 2 owns splitting and
  leakage controls.
- **Follow-up S1-F1:** wire dataset generation into CI once artifact caching policy
  is decided (Sprint 3 dependency review is the natural place).
- **Follow-up S1-F2:** add a reactor-volume field (schema `v2`) so `contact_time_ms`
  can be derived rather than left null (OQ-2).

---

## 9. Ready for Sprint 2

The v1 contract, validator, generator, and artifact provenance are in place and
green. Sprint 2 can train the initial XGBoost surrogate on
`data/odrm_dataset.parquet`, using `quality_flag` filtering (currently all `valid`)
and stratified splits for the imbalanced `high` risk class.

**Recommendation:** accept Sprint 1 and authorize Sprint 2 (surrogate training +
prediction endpoint) under the same workflow.
