# Sprint 2 Plan — Surrogate Training & Prediction API

**Project:** ODRM-Copilot (Syngas Shovel)
**Sprint:** 2 — Surrogate Training & Prediction API
**Owner:** CTO / Systems Architect
**Status:** 🟡 Awaiting review — execution blocked until approval
**Date:** 2026-11-02
**Approval phrase:** `AUTHORIZED: Sprint 2 implementation phase`

---

## 0. Sprint Charter

Sprint 2 turns the Sprint 1 synthetic dataset into a served surrogate: a deterministic
training pipeline that fits XGBoost regressors for two targets, enforces quality gates
(R² > 0.95 and explicit RMSE ceilings), writes versioned model artifacts with full
provenance, and exposes them through a validated `POST /api/v1/predict` endpoint.

The model learns the **reduced-order synthetic generator**, not the real reactor. It is
not experimental data, not HYSYS output, and not COMSOL output, and it must never be
presented as equivalent to those tools. Sprint 2 proves the serving path and the
measurement discipline; scientific fidelity remains bounded by Sprint 1's generator.

### In scope

- `backend/src/odrm/ml/features.py`: feature matrix, target extraction, catalyst
  encoding, leakage guard.
- `backend/src/odrm/ml/dataset.py`: Parquet loading, `quality_flag` filtering,
  stratified train/test split and CV folds.
- `backend/src/odrm/ml/train.py`: CLI that tunes, fits, evaluates, gates, and saves.
- `backend/src/odrm/ml/registry.py`: `.joblib` + `metadata.json` save/load, version
  resolution, corruption handling.
- `backend/src/odrm/ml/predict.py`: load pinned models, build prediction responses.
- `backend/src/odrm/api/schemas.py`: `PredictRequest`, `PredictResponse`,
  `ErrorEnvelope` Pydantic models.
- `backend/src/odrm/api/routes.py`: `POST /api/v1/predict` router.
- `backend/src/odrm/main.py`: router wiring and model-loading lifecycle.
- `.gitignore`: narrow change so `models/**/*.joblib` is ignored while
  `metadata.json` stays tracked.
- Unit and `ml`-marked tests for features, dataset, registry, training, gates, and the
  API contract.
- `docs/SPRINT_2_REPORT.md` at Phase 5.

### Explicitly out of scope (deferred)

- Carbon deposition regression and the `carbon_risk_class` classifier (Sprint 3).
- LangChain agent, tool calling, prompt design.
- Frontend/UI changes, charts, evidence-chain UI.
- Optimization engine, techno-economic model, plant deployment.
- Real experimental data, HYSYS exports, COMSOL exports, or simulator-equivalence
  claims.
- Changing `data/schemas/odrm_v1.json` or its `v1` contract.
- Changing the Sprint 1 generator, validator, or dataset bytes.
- Database ingestion, cloud storage, auth, billing, CI secrets.
- Batch prediction, streaming, async queues, model monitoring/retraining jobs.
- Committing binary `.joblib` artifacts.

### Deliverables checklist (exit criteria)

| # | Deliverable | Verification |
|---|---|---|
| 1 | `ml/features.py` with explicit feature list, catalyst encoding, and leakage guard | Feature tests pass; leakage guard fails on injected target column |
| 2 | `ml/dataset.py` filtering `quality_flag == "rejected"` and stratified split | Split tests pass; rejected rows absent |
| 3 | `ml/train.py` CLI with bounded tuning and metric reporting | `--seed 7` trains both targets and writes artifacts |
| 4 | `ml/registry.py` with versioned `.joblib` + `metadata.json` | Roundtrip and corruption tests pass |
| 5 | Trained artifacts for both targets meeting R² and RMSE gates | Gate test prints raw metrics; both pass |
| 6 | `POST /api/v1/predict` with Pydantic request/response and error envelope | API tests: 200 / 422 / 503 |
| 7 | Warm p95 latency < 50 ms | Latency test reports measured p95 |
| 8 | `models/odrm/<target>/<version>/metadata.json` committed; `.joblib` ignored | `git status` shows metadata only |
| 9 | `docs/SPRINT_2_REPORT.md` | Reviewed at Phase 5 |

### Traceability

| Source | Deliverable |
|---|---|
| `MASTER_ROADMAP.md` Sprint 2 | XGBoost model, R² > 0.95 gate, `/api/predict` route, <50 ms inference |
| `ARCHITECTURE.md` §5.2 | `models/odrm/<target>/<version>/` artifact layout |
| `ARCHITECTURE.md` §5.3 | Model records trained schema version; inference rejects mismatch |
| `ARCHITECTURE.md` §5.4 | Data-quality gates and no silent fallback |
| `ARCHITECTURE.md` §6.1 | Target and feature mapping |
| `ARCHITECTURE.md` §8 | Error envelope, `/api/v1` URL versioning, 422/503 semantics |
| `SPRINT_1_REPORT.md` §8 | 3.6% `high` class, optional-null sparsity, no split produced |
| `SPRINT_1_REPORT.md` §9 | Ready for Sprint 2; `quality_flag` filtering is Sprint 2's job |
| `SPRINT_WORKFLOW.md` | Plan-first, TDD, review gate, report |
| CTO decisions 2026-11-02 | Endpoint path, 2-target scope, RMSE gates, optional features, artifact policy, latency target |

### Definition of Done (global)

Code review approved · lint clean (`ruff`) · type check clean (`mypy`) · tests green ·
docs updated · no secrets committed · no binary artifacts committed · reproducible from
a clean venv with `--seed 7`.

### CTO-approved scope decisions

Recorded verbatim from the 2026-11-02 review:

1. **Endpoint path:** `POST /api/v1/predict`. `ARCHITECTURE.md` will be reconciled in a
   later sprint.
2. **Scope:** two regression targets only — `ch4_conversion` and
   `syngas_yield_mol_per_mol_ch4`. Carbon deposition and the risk classifier move to
   Sprint 3.
3. **RMSE gates:** accepted — ≤ 0.03 for `ch4_conversion`, ≤ 0.15 for
   `syngas_yield_mol_per_mol_ch4`.
4. **Optional features:** include `n2_dilution_mol_pct` and
   `catalyst_loading_wt_pct` (native XGBoost NaN handling). Drop `contact_time_ms` and
   `notes` entirely.
5. **Artifacts:** commit `metadata.json`; gitignore `.joblib`.
6. **Latency:** enforce 50 ms warm p95.

---

## 1. Source of Truth and Modelling Stance

### 1.1 Dataset contract

Sprint 2 consumes the Sprint 1 artifact unchanged.

| Property | Value |
|---|---|
| Path | `data/odrm_dataset.parquet` (compat copy of canonical batch) |
| Shape | `10000 × 29` |
| Unique `run_id` | `10000` |
| Required-field nulls | `0` |
| Parquet SHA-256 | `65f9ab45c3641747d980f9641145a2a6665a6e73e432c628f24bb038586b69c5` |
| Schema SHA-256 | `1ae139340befa4da32c1a7bd5955d8697f0a262e61313ed4964b9a9bf21f0224` |
| Generator seed | `7` |

Carbon-risk distribution (stratification basis):

| Class | Rows | Share |
|---|---:|---:|
| `none` | 1,263 | 12.63% |
| `low` | 3,662 | 36.62% |
| `moderate` | 4,719 | 47.19% |
| `high` | 356 | 3.56% |

Intentional optional nulls: `contact_time_ms` 10,000, `notes` 10,000,
`n2_dilution_mol_pct` 4,011, `catalyst_loading_wt_pct` 1,407.

If the Parquet is absent, the pipeline fails with an actionable message and the exact
generation command. It does not generate data implicitly.

### 1.2 Targets

| Target | Bounds | Role |
|---|---|---|
| `ch4_conversion` | `[0, 1]` | Primary conversion objective |
| `syngas_yield_mol_per_mol_ch4` | `[0, 8]` | Primary syngas objective |

Both are treated as independent single-target regressors (one model per target), so
metrics and artifacts are attributable per target.

### 1.3 Scientific stance

- The model approximates a deterministic reduced-order surrogate over a synthetic
  envelope.
- The dataset guarantees `co_yield > 0` and `co2_ch4_ratio ≥ 0.05` (Sprint 1 OQ-3), so
  the model has **no coverage** at those exact edges and must not be extrapolated there.
- A perfect score is expected because the generator is smooth and deterministic. A
  high R² therefore demonstrates pipeline correctness and serving integrity, not
  physical validity.
- Report the limitation in `docs/SPRINT_2_REPORT.md` with the same prominence as Sprint
  1's synthetic-data caveat.

### 1.4 Non-negotiables

- Training reads the Parquet; it never mutates it.
- `quality_flag == "rejected"` rows are excluded from training and evaluation.
- The test split is evaluated exactly once per approved run; it is never used for
  tuning.
- No derived or sibling outcome column may enter the feature matrix.
- The generator is deterministic for a given seed and config.
- No network access in training, tests, or inference.
- Missing or corrupt model artifacts produce `503`, never a silent fallback.
- Binary `.joblib` files are never committed.

---

## 2. Feature and Target Mapping

### 2.1 Feature set (allow-list)

`features.py` defines an explicit ordered allow-list. Order is part of the model
contract and is persisted in metadata.

| Feature | Type | Source | Nulls in dataset |
|---|---|---|---|
| `temperature_c` | numeric | required input | 0 |
| `pressure_bar` | numeric | required input | 0 |
| `ch4_o2_ratio` | numeric | required input | 0 |
| `co2_ch4_ratio` | numeric | required input | 0 |
| `h2o_ch4_ratio` | numeric | required input | 0 |
| `ghsv_per_h` | numeric | required input | 0 |
| `catalyst` | categorical | required input | 0 |
| `catalyst_loading_wt_pct` | numeric | optional input | 1,407 |
| `n2_dilution_mol_pct` | numeric | optional input | 4,011 |

Encoding:

- `catalyst` is one-hot encoded with a fixed category order matching
  `schema.ENUMS["catalyst"]`:
  `Ni/Al2O3`, `Ni-MgO`, `Rh`, `Pt`, `none`, `other`.
- Unknown catalyst values are rejected at request validation, not encoded at inference.
- One-hot columns are named `catalyst__<value>` with `/` and spaces normalized, and the
  exact names are persisted in metadata.
- Numeric optional features keep `NaN`; XGBoost handles missing values natively. No
  imputation is applied, so training and inference share identical missing-value
  semantics.

### 2.2 Explicit exclusions and leakage guard

Excluded by construction:

| Group | Columns | Reason |
|---|---|---|
| Identity / provenance | `run_id`, `created_at`, `source`, `schema_version`, `reactor_id` | No predictive meaning; IDs leak row identity |
| Fully null | `contact_time_ms`, `notes` | 100% null (CTO decision) |
| Redundant | `energy_input_kw` | Deterministic function of `temperature_c` and `ghsv_per_h` |
| Quality metadata | `quality_flag`, `balance_error_pct` | Label/quality signal, not physics |
| Target siblings | `co2_conversion`, `o2_conversion`, `h2_yield_mol_per_mol_ch4`, `co_yield_mol_per_mol_ch4`, `carbon_deposition_mg_per_gcat` | Other outcomes; leakage |
| Derived | `h2_co_ratio`, `syngas_yield_mol_per_mol_ch4`, `ch4_slip_pct`, `carbon_risk_class` | Algebraically determined by outcomes |
| Targets | `ch4_conversion`, `syngas_yield_mol_per_mol_ch4` | Never features |

Leakage guard requirements:

1. `assert_no_leakage(features)` intersects the resolved feature list with the union of
   `DERIVED_COLUMNS`, the target list, the sibling outcome list, and the exclusion list;
   any intersection raises `LeakageError`.
2. For each target, `ch4_slip_pct` and `syngas_yield_mol_per_mol_ch4` are excluded even
   when predicting the other target.
3. A test injects `ch4_slip_pct` into the candidate frame and asserts the guard raises.
4. A test asserts the resolved feature list is stable and matches metadata.

### 2.3 Target extraction

- `y = frame[target]` as float64.
- Targets are never clipped; if a predicted value is outside the schema bounds, the
  response reports it unclamped and a test asserts the raw value is returned (OQ-5).
- Training asserts `y` is finite and within `schema.BOUNDS`; a violation aborts the run
  rather than repairing the data.

---

## 3. Data Preparation, Split, and Tuning

### 3.1 Load and filter

`dataset.py`:

1. Read Parquet with `pyarrow` via `pandas.read_parquet`.
2. Assert the contract columns exist and `schema_version == "v1"`; otherwise fail with
   `DatasetContractError`.
3. Drop rows where `quality_flag == "rejected"`. Sprint 1 produced none, so the expected
   filtered count is `10,000`; the count is recorded in metadata.
4. Preserve `suspect` rows for Sprint 2 (no evidence of `suspect` rows exists); record
   the count.

### 3.2 Split strategy

| Parameter | Value | Rationale |
|---|---|---|
| Train/test | 80% / 20% | Standard holdout; ~2,000 test rows |
| Stratify | `carbon_risk_class` | Preserves the 3.6% `high` class in both splits (~71 test rows) |
| `random_state` | `7` | Matches Sprint 1 seed; reproducible |
| CV | 5-fold `StratifiedKFold` on train only | Keeps `high` represented in every fold |
| Grouping | `run_id` is unique, so row-level splitting is equivalent to group splitting | No run-level leakage |

The test split is created once per run, stored in memory, and evaluated after tuning.
It is never passed to a search object. The exact split indices are derived from
`random_state=7` and recorded in metadata as counts and class shares, not as row IDs.

### 3.3 Imbalance handling

- The split and CV folds are stratified, which is the primary control.
- Metrics are reported for the full test set **and** for the `high` risk stratum so
  degradation on the rare class is visible.
- Sample weighting is available behind an explicit `--sample-weight` flag but is **off
  by default**; enabling it changes the gate comparison and must be approved separately
  (OQ-1).
- Because Sprint 2 has no classifier, no `class_weight`/`scale_pos_weight` is used.

### 3.4 Hyperparameter tuning

`RandomizedSearchCV` with a bounded space, 5-fold CV, and
`scoring="neg_root_mean_squared_error"`:

| Parameter | Candidate values |
|---|---|
| `n_estimators` | 200, 400, 600 |
| `max_depth` | 3, 4, 5, 6, 8 |
| `learning_rate` | 0.03, 0.05, 0.1, 0.2 |
| `subsample` | 0.7, 0.85, 1.0 |
| `colsample_bytree` | 0.7, 0.85, 1.0 |
| `min_child_weight` | 1, 3, 5 |
| `reg_lambda` | 1.0, 2.0, 5.0 |

- `n_iter = 30`, `n_jobs = -1`, `random_state = 7`, `tree_method = "hist"`.
- Fixed: `objective = "reg:squarederror"`, `verbosity = 0`.
- Runtime budget: each target must tune and fit in under ~5 minutes on the 10k-row
  dataset; the plan is re-scoped if the measured time exceeds that.
- Tuning is deterministic given `random_state=7`; the selected params are persisted in
  metadata.

### 3.5 Metrics and gates

Reported per target on train, best CV, and test:

- R², RMSE, MAE.
- Test metrics on the full set and on the `high` carbon-risk stratum.
- Prediction range (`min`, `max`) and the count of non-finite predictions (must be 0).

Acceptance gates (CTO-approved):

| Target | R² gate | RMSE gate |
|---|---|---|
| `ch4_conversion` | `> 0.95` | `≤ 0.03` |
| `syngas_yield_mol_per_mol_ch4` | `> 0.95` | `≤ 0.15` |

Additional audit checks:

- All predictions finite; any non-finite prediction fails the run.
- Train R² ≥ test R² is not required, but `abs(CV R² − test R²) ≤ 0.05` is reported as
  an overfit indicator; a breach is recorded in the report and escalated to the CTO
  rather than auto-failing (OQ-2).
- Gate evaluation is a pure function so it can be unit-tested without training.

---

## 4. Artifact Design and Versioning

### 4.1 Layout

```text
models/odrm/
  ch4_conversion/
    latest.json
    <version>/
      model.joblib
      metadata.json
  syngas_yield_mol_per_mol_ch4/
    latest.json
    <version>/
      model.joblib
      metadata.json
```

- `<version>` is `v1-<YYYYMMDDTHHMMSSZ>` (UTC, second precision), assigned once at save
  time.
- `latest.json` is a small committed pointer: `{"version": "...", "target": "..."}`.
- `model.joblib` is gitignored; `metadata.json` and `latest.json` are committed.
- Writes are atomic (temp file + `os.replace`); an existing version directory is never
  overwritten.

### 4.2 `metadata.json` schema

```json
{
  "schema_version": "v1",
  "target": "ch4_conversion",
  "model_version": "v1-20261102T000000Z",
  "created_at": "2026-11-02T00:00:00Z",
  "algorithm": "xgboost.XGBRegressor",
  "xgboost_version": "3.2.0",
  "sklearn_version": "1.9.1",
  "python_version": "3.11.9",
  "random_state": 7,
  "dataset": {
    "path": "data/odrm_dataset.parquet",
    "sha256": "<parquet-sha256>",
    "schema_sha256": "<contract-sha256>",
    "row_count_raw": 10000,
    "row_count_used": 10000,
    "rejected_dropped": 0,
    "suspect_kept": 0,
    "test_size": 0.2,
    "stratify_on": "carbon_risk_class",
    "class_shares": {"none": 0.1263, "low": 0.3662, "moderate": 0.4719, "high": 0.0356}
  },
  "features": ["temperature_c", "...", "catalyst__Ni_Al2O3"],
  "catalyst_categories": ["Ni/Al2O3", "Ni-MgO", "Rh", "Pt", "none", "other"],
  "hyperparameters": {"n_estimators": 400, "max_depth": 6, "...": "..."},
  "metrics": {
    "train": {"r2": 0.0, "rmse": 0.0, "mae": 0.0},
    "cv": {"r2": 0.0, "rmse": 0.0, "mae": 0.0},
    "test": {"r2": 0.0, "rmse": 0.0, "mae": 0.0},
    "test_high_risk": {"r2": 0.0, "rmse": 0.0, "mae": 0.0, "n": 0}
  },
  "gates": {"r2_min": 0.95, "rmse_max": 0.03, "passed": true},
  "git_sha": "<40-hex>",
  "git_dirty": false
}
```

### 4.3 Registry behavior

- `save_model(model, metadata, root)` validates required metadata keys, refuses to
  overwrite an existing version, writes atomically, and updates `latest.json`.
- `load_model(target, root, version=None)` resolves `latest.json` when `version` is
  omitted, verifies the artifact exists and unpickles it, and raises
  `ModelNotFoundError` or `ModelCorruptError` with actionable messages.
- `list_versions(target, root)` returns versions newest-first.
- Loading verifies that the metadata `features` list matches the model's expected input
  order; a mismatch raises `ModelContractError`.
- No network, no automatic retraining, no fallback to a different version.

### 4.4 `.gitignore` change (narrow)

Current rule `models/*.joblib` does not match nested artifact paths. Sprint 2 will
replace it with `models/**/*.joblib` and keep `metadata.json`/`latest.json` tracked. No
other ignore rules change.

---

## 5. API Contract

### 5.1 Route

`POST /api/v1/predict`

- Mounted through the existing `create_app(settings)` factory using
  `settings.api_prefix`.
- Router registered in `main.py`; no change to `GET /health`.
- Synchronous, single-record prediction. Batch is deferred (OQ-4).

### 5.2 Request

`PredictRequest` (Pydantic v2, `extra="forbid"`):

| Field | Type | Required | Constraint |
|---|---|---|---|
| `temperature_c` | float | yes | `schema.BOUNDS`, inclusive 500–1000 |
| `pressure_bar` | float | yes | inclusive 1–30 |
| `ch4_o2_ratio` | float | yes | inclusive 1.4–2.5 |
| `co2_ch4_ratio` | float | yes | inclusive 0–1.5 |
| `h2o_ch4_ratio` | float | yes | inclusive 0–1.5 |
| `ghsv_per_h` | float | yes | inclusive 1,000–100,000 |
| `catalyst` | enum | yes | `schema.ENUMS["catalyst"]` |
| `catalyst_loading_wt_pct` | float \| null | no | inclusive 0–20 |
| `n2_dilution_mol_pct` | float \| null | no | inclusive 0–50 |

All numeric fields reject `NaN`/`inf`. Bounds come from `schema.BOUNDS` so the API and
the dataset contract cannot drift.

### 5.3 Response (200)

```json
{
  "predictions": {
    "ch4_conversion": 0.8731,
    "syngas_yield_mol_per_mol_ch4": 2.4102
  },
  "model": {
    "schema_version": "v1",
    "versions": {
      "ch4_conversion": "v1-20261102T000000Z",
      "syngas_yield_mol_per_mol_ch4": "v1-20261102T000000Z"
    }
  },
  "request_id": "5f0c2b1e-3f5a-4f0e-9a2c-1b2c3d4e5f60"
}
```

- Values are raw floats, not rounded for storage (JSON serialization may shorten).
- Predictions are **not clamped** to target bounds (OQ-5).
- `request_id` is a UUID generated per request and echoed in errors.

### 5.4 Errors

Envelope per `ARCHITECTURE.md` §8:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed",
    "details": [{"loc": ["body", "temperature_c"], "msg": "..."}],
    "request_id": "..."
  }
}
```

| Status | Code | Condition |
|---|---|---|
| 422 | `validation_error` | Pydantic/bounds/enum failure |
| 503 | `model_unavailable` | Artifact missing, unreadable, or contract mismatch |
| 500 | `internal_error` | Unexpected inference failure (no stack trace in body) |

No silent fallback, no default model, no partial response: if either target model is
unavailable, the whole request returns `503`.

### 5.5 Lifecycle and latency

- At startup, `create_app` attempts to load both `latest` models into
  `app.state.models`; failure leaves the slot empty and logs a warning. The app still
  boots so `/health` stays available and `/predict` returns `503`.
- Tests inject a stub model through `app.state` to avoid requiring real artifacts.
- Warm p95 target: `< 50 ms` over 100 sequential requests after a warmup request, on the
  acceptance machine. Cold start is excluded and reported separately.
- Latency is measured in a test marked `slow`; the report records the raw numbers.

---

## 6. TDD and Test Matrix

Tests are written first, observed to fail for the expected reason, then implemented. The
existing `backend/tests/conftest.py` network block is reused; no test may open a socket.

### 6.1 Test files

| File | Marker | Purpose |
|---|---|---|
| `backend/tests/unit/test_ml_features.py` | `unit` | Allow-list, encoding, NaN, leakage guard, determinism |
| `backend/tests/unit/test_ml_dataset.py` | `unit` | Contract check, rejected filtering, stratified split |
| `backend/tests/unit/test_ml_registry.py` | `unit` | Save/load, versioning, corruption, contract mismatch |
| `backend/tests/unit/test_predict_api.py` | `unit` | 200/422/503, response schema, error envelope, no network |
| `backend/tests/ml/test_train_pipeline.py` | `ml` | Tiny-frame training smoke and determinism |
| `backend/tests/ml/test_model_gates.py` | `ml`, `slow` | Full-data R²/RMSE gates and warm p95 latency |

### 6.2 Feature tests

- Resolved feature list equals the documented allow-list plus one-hot columns.
- `catalyst` categories follow `schema.ENUMS` order exactly.
- One-hot names are stable and match metadata.
- Optional nulls survive as `NaN`; no imputation occurs.
- Injecting `ch4_slip_pct`, `syngas_yield_mol_per_mol_ch4`, any sibling outcome, or any
  derived column into the candidate set raises `LeakageError`.
- Target extraction returns float64 with no mutation of the source frame.
- Feature building is deterministic across calls.

### 6.3 Dataset tests

- Loading the real Parquet yields `10000` rows and the expected SHA-256.
- A frame with `quality_flag == "rejected"` rows drops exactly those rows.
- A wrong `schema_version` or missing column raises `DatasetContractError`.
- Split is 80/20 within rounding, `random_state=7` reproduces identical indices.
- All four carbon-risk classes appear in train and test.
- Test indices are disjoint from train indices and cover every row exactly once.
- The search object never sees test indices (asserted via a spy/fake estimator).

### 6.4 Registry tests

- Save then load roundtrips predictions bit-identically.
- `latest.json` points at the newest version.
- Saving the same version twice raises `ArtifactConflict` and leaves files untouched.
- Missing artifact raises `ModelNotFoundError`.
- Truncated `.joblib` raises `ModelCorruptError`.
- Metadata feature order differing from the model raises `ModelContractError`.
- `list_versions` returns newest-first and tolerates a missing directory.

### 6.5 API tests

- Valid request returns 200 with both predictions and both model versions.
- Every field below-min and above-max returns 422 with the error envelope.
- `NaN`, `inf`, unknown catalyst, extra field, and missing field return 422.
- Optional nulls are accepted.
- `request_id` is present and identical between response and error envelope.
- Missing model state returns 503 `model_unavailable`.
- A stub model returning a non-finite value returns 500 `internal_error`.
- `/health` still returns `{"status": "ok", "env": "test"}`.
- No network access during any test.

### 6.6 Training and gate tests

- A 200-row synthetic frame trains end-to-end and writes artifacts under `tmp_path`.
- Same seed and params produce identical predictions.
- Gate function passes at the threshold and fails just outside it (boundary tests).
- Full-data run meets R² > 0.95 and RMSE gates for both targets.
- Warm p95 latency < 50 ms.
- Artifacts are written only after all gates pass; a gate failure writes nothing.

### 6.7 Quality targets

- `pytest backend/tests -q` green, including `ml` markers.
- `ruff check backend scripts` and `ruff format --check` clean.
- `mypy backend/src scripts` clean.
- Line coverage ≥ 90% for `odrm/ml/` and `odrm/api/`.
- No `DeprecationWarning` from `odrm.*`.
- No committed `.joblib`.

---

## 7. Implementation Sequence and Commits

Only after `AUTHORIZED: Sprint 2 implementation phase`. Each step is test-first; commits
only if authorized under the workflow.

| Step | Work | Commit message (proposed) |
|---|---|---|
| 1 | Feature allow-list, encoding, leakage guard + tests | `test(ml): lock ODRM feature contract` |
| 2 | Dataset load/filter/split + tests | `feat(ml): add dataset preparation and split` |
| 3 | Registry save/load/versioning + tests | `feat(ml): add model registry with metadata` |
| 4 | Metric and gate functions + tests | `feat(ml): add model acceptance gates` |
| 5 | Training CLI and tuning + smoke test | `feat(ml): add XGBoost training pipeline` |
| 6 | Train both targets; commit metadata, ignore joblib | `feat(ml): train ODRM surrogate v1` |
| 7 | Pydantic schemas and predict router + tests | `feat(api): add predict endpoint` |
| 8 | Startup model loading and 503 path + tests | `feat(api): serve versioned surrogate models` |
| 9 | README commands and Sprint 2 report | `docs: add Sprint 2 report` |

### 7.1 Documentation

- README: add train, serve, and predict commands plus the synthetic-model caveat.
- `docs/SPRINT_2_REPORT.md`: built items, raw metrics, gate evidence, latency, artifact
  versions/hashes, deviations, known issues, follow-ups.
- `docs/ARCHITECTURE.md`: not edited in Sprint 2; the endpoint-path reconciliation is
  explicitly deferred by CTO decision.

### 7.2 Local commands

PowerShell from the repository root, using the project venv:

```powershell
.\.venv\Scripts\python.exe scripts\generate_odrm_data.py --n 10000 --seed 7
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_ml_features.py -q
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_ml_dataset.py -q
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_ml_registry.py -q
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_predict_api.py -q
.\.venv\Scripts\python.exe -m pytest backend/tests/ml -q -m ml
```

---

## 8. Acceptance and Audit Evidence

Accepted only with raw terminal evidence, not a summary.

### 8.1 Full gate

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
.\.venv\Scripts\python.exe -m ruff check backend scripts
.\.venv\Scripts\python.exe -m ruff format --check backend scripts
.\.venv\Scripts\python.exe -m mypy backend/src scripts
```

### 8.2 Model acceptance

```powershell
.\.venv\Scripts\python.exe -c "import json,pathlib; [print(t, json.loads(pathlib.Path(f'models/odrm/{t}/latest.json').read_text())) for t in ['ch4_conversion','syngas_yield_mol_per_mol_ch4']]"
```

Required evidence:

- Both targets: test R² > 0.95.
- `ch4_conversion` test RMSE ≤ 0.03.
- `syngas_yield_mol_per_mol_ch4` test RMSE ≤ 0.15.
- Warm p95 latency < 50 ms.
- Metadata contains dataset SHA-256, schema SHA-256, feature list, params, metrics,
  gate result, and git SHA.
- `git status --short` shows `metadata.json`/`latest.json` tracked and no `.joblib`.

### 8.3 API acceptance

```powershell
.\.venv\Scripts\python.exe -m uvicorn odrm.main:app --port 8000
```

Then a `POST /api/v1/predict` with a valid body returns 200 and both predictions; a
below-minimum `temperature_c` returns 422 with the envelope; renaming the model
directory and restarting returns 503.

### 8.4 Phase 5 report

`docs/SPRINT_2_REPORT.md` must include:

- What was built.
- Test counts, pass rate, and coverage for `odrm/ml/` and `odrm/api/`.
- Raw R²/RMSE/MAE for train, CV, test, and the `high` risk stratum.
- Warm p95 latency and the measurement method.
- Dataset and schema hashes used for training.
- Artifact versions and metadata excerpts.
- Deviations from this plan.
- Known issues, limitations, and follow-ups.
- Confirmation that no schema, generator, or architecture contract was silently changed.

---

## 9. Risks and Mitigations

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Synthetic model mistaken for validated physics | High | High | Label `source=synthetic`; report limitation; no simulator-equivalence claims |
| R2 | Target leakage inflates metrics | Medium | High | Explicit allow-list; leakage guard; injected-column test; exclude derived/siblings |
| R3 | 3.6% `high` class too small for stable stratum metrics | High | Medium | Stratified split and folds; report `n`; treat stratum metrics as diagnostic |
| R4 | R² > 0.95 gate passes trivially and hides a broken pipeline | Medium | Medium | RMSE ceilings; range/finite checks; API roundtrip test; gate boundary tests |
| R5 | Optional-null handling differs between training and request | Medium | High | Shared feature builder; one-hot names persisted; API tests with nulls |
| R6 | `.joblib` accidentally committed | Medium | Low | Narrow `.gitignore` to `models/**/*.joblib`; `git status` audit |
| R7 | Metadata drifts from model contract | Medium | Medium | `ModelContractError` on feature-order mismatch; metadata roundtrip tests |
| R8 | Endpoint path diverges from `ARCHITECTURE.md` | High | Low | CTO-approved `/api/v1/predict`; architecture reconciliation deferred and recorded |
| R9 | Missing model breaks app boot | Medium | High | Boot with empty state; `/health` stays up; `/predict` returns 503 |
| R10 | Tuning runtime grows unbounded | Medium | Medium | `n_iter=30`, bounded grid, `n_jobs=-1`, ~5 min budget per target |
| R11 | Windows path/encoding issues in artifact writes | Low | Low | `pathlib`, UTF-8, atomic replace, PowerShell-safe commands |
| R12 | Non-finite predictions reach the client | Low | High | Finite check before response; 500 on violation; test with stub |
| R13 | Test set reused during iteration | Medium | High | Single holdout; search sees train only; spy test asserts no test indices |
| R14 | Model extrapolates at dataset edges | Medium | Medium | Document no coverage at `co2_ch4_ratio = 0` and `co_yield = 0`; no clamp |

---

## 10. Assumptions

- Sprint 1 is accepted and `odrm_v1.json` is frozen at `v1`.
- The Sprint 1 dataset is regenerable with `--n 10000 --seed 7` and matches the recorded
  SHA-256.
- Two independent single-target regressors are sufficient for Sprint 2; multi-output and
  classifiers are Sprint 3.
- XGBoost's native `NaN` handling is acceptable for the two partially-null optional
  features.
- The synthetic generator is smooth enough that XGBoost clears the gates comfortably.
- `metadata.json`/`latest.json` are the committed source of truth; `.joblib` is
  reproducible from data + metadata + code.
- The acceptance machine can run the full `ml` suite within a few minutes.
- Python 3.11.9 in `.venv` is the execution environment.
- No real plant, experimental, HYSYS, or COMSOL data is available or required.

---

## 11. Open Questions (CTO Decisions)

The six Sprint 2 scope questions are resolved in §0. Remaining items are non-blocking and
have recommended defaults.

| ID | Question | Recommendation | Impact if unresolved | CTO decision |
|---|---|---|---|---|
| OQ-1 | Should rare-class sample weighting be enabled? | Off by default; stratified split plus `high`-stratum reporting | May bias toward the majority regime | Pending |
| OQ-2 | Is `abs(CV R² − test R²) ≤ 0.05` a hard gate or an advisory indicator? | Advisory; record and escalate, do not auto-fail | Could mask overfitting | Pending |
| OQ-3 | Version naming: wall-clock timestamp or content hash? | `v1-<UTC timestamp>`; metadata records data and git hashes | Reproducibility/audit ergonomics | Pending |
| OQ-4 | Should `/api/v1/predict` accept batch input in Sprint 2? | No; single-record only | Throughput for UI/batch callers | Pending |
| OQ-5 | Should predictions be clamped to schema bounds? | No; return raw values and document | Client may receive out-of-range values | Pending |
| OQ-6 | Should `energy_input_kw` be a feature? | No; deterministic function of `temperature_c` and `ghsv_per_h` | Redundant feature, no gain | Pending |
| OQ-7 | Is a 503 on missing model acceptable at boot, or should the app fail fast? | Boot and return 503; keeps `/health` observable | Deployment health-check semantics | Pending |

---

## 12. Approval Gate

This plan is the only Sprint 2 artifact created before authorization.

- No implementation code, tests, model artifacts, `.gitignore` edits, or commits are made
  until the CTO replies with the exact phrase:

  `AUTHORIZED: Sprint 2 implementation phase`

- If the CTO requests changes, revise this plan first and stop again.
- If an open question changes the contract, update the plan and obtain a new approval
  before coding.
- On approval, implementation proceeds in the TDD order in §7 and reports through
  `docs/SPRINT_2_REPORT.md`.
