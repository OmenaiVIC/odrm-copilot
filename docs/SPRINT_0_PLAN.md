# Sprint 0 Plan — Foundation & Setup

**Project:** ODRM-Copilot (Syngas Shovel)
**Sprint:** 0 — Foundation (no feature code)
**Owner:** CTO / Systems Architect
**Status:** 🟡 Awaiting review — execution blocked until approval
**Date:** 2026-11-01

---

## 0. Sprint Charter

Sprint 0 delivers a *run-able skeleton*, not features. At the end of this sprint a new
contributor must be able to: clone, install, run the API, run the test suite, run the
frontend, and understand the commercial model — without asking a question.

### In scope
- Python backend project definition (dependencies + tool config)
- Test harness structure and canonical commands
- Next.js frontend scaffold command + baseline config
- `docs/ARCHITECTURE.md` outline and ownership
- ODRM dataset schema (Pandas) for Sprint 1

### Explicitly out of scope (deferred)
- Any FastAPI route, ML training, LangChain tool, UI screen
- Synthetic dataset generation, model training, optimization engine
- Auth, billing, deployment pipelines, CI secrets

### Deliverables checklist (exit criteria)
| # | Deliverable | Verification |
|---|---|---|
| 1 | `pyproject.toml` committed at repo root | `pip install -e ".[dev]"` succeeds |
| 2 | `backend/tests/conftest.py` + smoke test | `pytest backend/tests -q` passes |
| 3 | `frontend/` Next.js app builds | `npm run build` succeeds |
| 4 | `docs/ARCHITECTURE.md` written | Reviewed by owner |
| 5 | ODRM schema documented + fixture parquet | `validate_odrm_frame()` on fixture passes |
| 6 | `SPRINT_WORKFLOW.md` created (see §7) | Reviewed by owner |

### Definition of Done (global)
Code review approved · lint clean (`ruff`) · type check clean (`mypy`) · tests green ·
docs updated · no secrets committed · reproducible from a clean venv.

---

## 1. Backend Setup

### 1.1 Decision: `pyproject.toml` (primary), `requirements.txt` (resolved lock)

**Rationale.** One source of truth for dependencies *and* tooling (pytest/ruff/mypy).
`requirements.txt` is still emitted as a fully pinned artifact so deployments and
reviewers get byte-reproducible installs. Two files, one owner: `pyproject.toml`.

**Layout decision.** Root-level `pyproject.toml` with a `src`-layout package under
`backend/src/`, so `pip install -e .` installs the app and `pytest` works from the repo
root without `sys.path` hacks.

```
odrm-copilot/
├── pyproject.toml
├── requirements.txt            # generated, fully pinned
├── backend/
│   ├── src/odrm/
│   │   ├── __init__.py
│   │   ├── main.py             # app factory (Sprint 1)
│   │   ├── api/                # routers (Sprint 1+)
│   │   ├── core/               # config, logging, errors
│   │   ├── domain/             # Pydantic schemas, units, physics bounds
│   │   ├── data/               # loaders, validators, parquet I/O
│   │   ├── ml/                 # training, inference, registry
│   │   ├── agents/             # LangChain tools (Sprint 2+)
│   │   └── services/           # orchestration / TEA
│   └── tests/
│       ├── conftest.py
│       ├── unit/
│       ├── integration/
│       ├── ml/
│       └── agent/
├── data/{raw,processed,schemas}/
├── models/
├── scripts/
├── frontend/
└── docs/
```

### 1.2 Proposed `pyproject.toml`

> Floors only. Treat the resolved set as authoritative and freeze it into
> `requirements.txt` via `pip freeze` (or `uv pip compile`) immediately after the first
> successful install, then review. LangChain's 0.x → 1.x import surface must be confirmed
> at install time before any agent code is written.

```toml
[build-system]
requires = ["setuptools>=69", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "odrm-copilot"
version = "0.1.0"
description = "AI surrogate process & optimization API for flare gas valorization (ODRM)"
readme = "README.md"
requires-python = ">=3.11,<3.13"
license = { text = "Proprietary" }

dependencies = [
  # API
  "fastapi>=0.115",
  "uvicorn[standard]>=0.30",
  "pydantic>=2.8",
  "pydantic-settings>=2.4",
  "httpx>=0.27",
  # Data
  "pandas>=2.2",
  "pyarrow>=17.0",
  "numpy>=1.26",
  # ML / surrogate
  "xgboost>=2.1",
  "scikit-learn>=1.5",
  "joblib>=1.4",
  # Agent layer
  "langchain>=0.3",
  "langchain-core>=0.3",
  "langchain-openai>=0.2",
  # Config
  "python-dotenv>=1.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.2",
  "pytest-cov>=5.0",
  "pytest-asyncio>=0.23",
  "anyio>=4.4",
  "ruff>=0.5",
  "mypy>=1.10",
  "pandas-stubs",
  "types-requests",
  "ipykernel",
]

[project.scripts]
odrm = "odrm.main:main"

[tool.setuptools.packages.find]
where = ["backend/src"]

[tool.pytest.ini_options]
minversion = "8.0"
testpaths = ["backend/tests"]
pythonpath = ["backend/src"]
addopts = "-ra --strict-markers --strict-config"
asyncio_mode = "auto"
filterwarnings = ["error::DeprecationWarning:odrm.*"]
markers = [
  "unit: fast, no I/O",
  "integration: crosses a boundary (DB, API, filesystem)",
  "ml: touches model training/inference",
  "agent: exercises LangChain tool selection",
  "slow: excluded from the commit gate",
]

[tool.ruff]
line-length = 100
target-version = "py311"
src = ["backend/src", "backend/tests"]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "RUF"]
ignore = ["E501"]

[tool.mypy]
python_version = "3.11"
strict = true
packages = ["odrm"]
mypy_path = "backend/src"
warn_unused_ignores = true
disallow_untyped_defs = true
```

### 1.3 Proposed `requirements.txt` (generated, not hand-written)

```
# Generated: python -m pip freeze > requirements.txt
# Do not edit by hand. Regenerate after changing pyproject.toml.
-r pyproject.toml   # not valid pip syntax — see note
```

> Note: pip cannot `-r` a `pyproject.toml`. The lock workflow is:
> `pip install -e ".[dev]" && pip freeze --exclude-editable > requirements.txt`.
> `requirements.txt` therefore contains only pinned transitives and is the artifact
> copied into Docker images.

### 1.4 Environment & bootstrap commands (for approval, not yet run)

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
pip freeze --exclude-editable > requirements.txt
```

**Install-order risk.** `xgboost` on Windows/CPython 3.12 may need a wheel-compatible
version; if resolution fails, pin to the newest version publishing `cp312-win_amd64`
wheels rather than downgrading Python below 3.11. LangChain's transitive set is the
largest source of resolver churn — freeze immediately after the first green install.

### 1.5 Config contract (`.env.example`, committed; `.env` ignored)

```
ODRM_ENV=local
ODRM_LOG_LEVEL=INFO
ODRM_API_PREFIX=/api/v1
ODRM_CORS_ORIGINS=http://localhost:3000
ODRM_MODEL_DIR=./models
ODRM_DATA_DIR=./data
OPENAI_API_KEY=            # required only for agent tests; never committed
ODRM_LLM_MODEL=gpt-4o-mini
ODRM_MAX_TEMPERATURE_C=1000
```

---

## 2. Testing Foundation

### 2.1 Proposed `backend/tests/conftest.py` structure

Purpose: one place that guarantees *determinism*, *isolation from the network*, and
*physics-valid fixtures*. Fixtures are grouped, not monolithic.

```python
# backend/tests/conftest.py  (structure proposal — not implemented yet)

# ---- 1. Environment isolation -------------------------------------------
# session-scoped, autouse:
#   - force ODRM_ENV=test, ODRM_MODEL_DIR=<tmp>, deterministic seeds
#   - block outbound sockets so no test can hit OpenAI or a live DEX/API
#   - fail fast if OPENAI_API_KEY is read when the test is not marked `agent`

# ---- 2. App / client -----------------------------------------------------
# @pytest.fixture(scope="session")  app()        -> create_app(settings=test_settings)
# @pytest.fixture()                 client()     -> fastapi.testclient.TestClient(app)

# ---- 3. Data fixtures ----------------------------------------------------
# @pytest.fixture()  odrm_row()          -> one valid dict, canonical units
# @pytest.fixture()  odrm_frame()        -> ~200-row deterministic DataFrame
# @pytest.fixture()  odrm_frame_bad()    -> violates bounds (T=1200C, nulls, conv>1)
# @pytest.fixture()  parquet_path(tmp_path) -> writes frame, returns Path

# ---- 4. ML fixtures ------------------------------------------------------
# @pytest.fixture(scope="session")  tiny_model()  -> 12-tree XGBoost, seeded
# @pytest.fixture(scope="session")  model_dir(tmp_path_factory)

# ---- 5. Agent fixtures ---------------------------------------------------
# @pytest.fixture()  fake_llm()        -> scripted LangChain chat model (no network)
# @pytest.fixture()  tool_spy()        -> records every tool call name + args
#     (asserts the agent passed validated params, never invented physics)

# ---- 6. Assertion helpers ----------------------------------------------
# assert_valid_odrm_frame(df)  -> dtype + null + range + mass-balance checks
# assert_tool_called(spy, name, **expected_args)
```

**Rules enforced by the harness**
1. No test may call a real LLM, real network, or the production model registry.
2. Every random operation is seeded; `odrm_frame()` is byte-identical across runs.
3. ML tests assert **R² > 0.95** on the held-out split (skill requirement), not just "runs".
4. Agent tests assert *tool selection and argument schema*, never generated prose.
5. Physics-bound violations must **raise**, not silently clamp.

### 2.2 Exact commands

```powershell
# Full suite (commit gate)
pytest backend/tests -q

# Fast inner loop
pytest backend/tests -m "not slow and not integration" -q

# Coverage
pytest backend/tests --cov=odrm --cov-report=term-missing --cov-fail-under=80

# Single layer
pytest backend/tests/unit -q
pytest backend/tests/ml -m ml -q
pytest backend/tests/agent -m agent -q

# Quality gates
ruff check backend && ruff format --check backend
mypy backend/src
```

**CI gate order (Sprint 1):** `ruff` → `mypy` → `pytest -m "not slow"` → build.
Coverage floor starts at 80% and only ratchets upward.

---

## 3. Frontend Setup

### 3.1 Scaffold command

Run from the repo root; `frontend/` exists but is empty, which `create-next-app` accepts.

```powershell
npx create-next-app@latest frontend `
  --typescript `
  --tailwind `
  --eslint `
  --app `
  --src-dir `
  --import-alias "@/*" `
  --turbopack `
  --use-npm
```

If the CLI refuses a pre-existing directory, scaffold into a temp dir and move contents:

```powershell
npx create-next-app@latest .odrm-tmp --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --use-npm
Move-Item -Path .odrm-tmp\* -Destination frontend\ -Force
Move-Item -Path .odrm-tmp\.gitignore -Destination frontend\.gitignore -Force
Remove-Item -Recurse -Force .odrm-tmp
```

### 3.2 Post-scaffold baseline (Sprint 0, config only)

- `frontend/.env.local.example` → `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1`
- `frontend/src/lib/api.ts` → typed fetch wrapper with error normalization (thin, no features)
- Add scripts: `"typecheck": "tsc --noEmit"`, `"format": "prettier --write ."`
- Tailwind: confirm `content` globs cover `src/**/*.{ts,tsx}`
- Add `frontend/README.md` linking to `docs/ARCHITECTURE.md`

**Deferred to Sprint 1+:** shadcn/ui, TanStack Query, Recharts, Playwright, auth.

### 3.3 Frontend gates

```powershell
npm run lint
npm run typecheck
npm run build
```

---

## 4. `docs/ARCHITECTURE.md` — Outline

### 4.1 Tech stack
Table of component / choice / version / rationale / ADR link:
- **Frontend:** Next.js (App Router, TS), Tailwind, Recharts (parity plots), TanStack Query
- **API:** FastAPI + Pydantic v2 (schema-first, OpenAPI as contract)
- **Data:** Pandas + Parquet (columnar, typed, cheap to version)
- **ML:** XGBoost (tabular surrogate) + scikit-learn (preprocessing, metrics), joblib registry
- **Agent:** LangChain tool-calling, strict JSON schemas, no free-form physics
- **Storage:** local Parquet + model dir (Sprint 0–1) → Postgres + object store (later)
- **Ops:** Docker Compose locally; managed container + CDN in production

### 4.2 System flow
- C4 Level 1 context: Engineer → ODRM-Copilot → (Surrogate | Optimizer | TEA) → Report
- C4 Level 2 container: Next.js → FastAPI → Domain/Physics Guard → ML Registry → Data Lake
- Sequence (natural language path):
  `NL input → LangChain agent → JSON params → Pydantic validation → physics-bound guard
   → OOD check → XGBoost surrogate → optimizer → TEA → response + confidence + provenance`
- Failure paths: invalid params (422), out-of-distribution (flag + confidence penalty),
  model unavailable (503), unsafe carbon risk (hard block with explanation)
- Data flow diagram: raw → validated → train/test split → model artifact → inference log

### 4.3 The Shovel-and-Picks commercial model
- **Positioning:** we sell the *shovel* (simulation-grade prediction at 1% of HYSYS cost),
  not the gold. Customers keep their process IP; we monetize access.
- **ICP:** flare-gas owners/operators, EPCs, and engineering consultancies in the Global South
- **Tiers:** Explorer (free, capped runs) → Pro (seat + run quota) → Enterprise (private
  model instance, on-prem/VPC, SLA, audit export)
- **Metering:** per successful inference/solve, not per token; failed validations are free
- **Moat / data flywheel:** validated runs improve the surrogate; customer data stays
  tenant-isolated and is never used for cross-tenant training without explicit consent
- **Unit economics:** cost-to-serve per solve vs. price per solve; gross-margin target
- **Adjacent "picks":** premium reports (bankable TEA), API access, model calibration
  services — high margin, no extra inference cost
- **Anti-pattern guard:** no claim of HYSYS/COMSOL equivalence without a validation
  appendix; publish error bars and applicability envelope

### 4.4 Also required in the doc
- Data architecture & schema versioning policy
- ML lifecycle: splits, R²>0.95 gate, OOD detection, drift monitoring, model registry
- API design: versioning (`/api/v1`), error envelope, idempotency, rate limits
- Security & multi-tenancy: tenant isolation, secret handling, no PII in logs
- Observability: structured JSON logs, immutable audit trail (who/what/why/inputs hash)
- Non-functional requirements: p95 latency, uptime, cost ceilings
- Risk register (see §7) and ADR index

---

## 5. Data Placeholder — ODRM Schema (Sprint 1 input)

**Storage:** Parquet under `data/processed/odrm/v1/`, one file per batch, plus
`_manifest.json` (row count, SHA-256, schema version, generator version, seed).

**Units:** SI-adjacent engineering units, stated per column. No unit-free numbers.
**Hard physics bound:** `temperature_c <= 1000` (per data-engineer rule); violations
reject the row, they are never clamped.

| Column | dtype | Unit | Valid range | Null? | Notes |
|---|---|---|---|---|---|
| `run_id` | string | — | UUID | no | primary key |
| `created_at` | datetime64[ns, UTC] | — | — | no | provenance |
| `source` | category | — | experimental, aspen_hysys, comsol, synthetic, plant | no | lineage |
| `schema_version` | string | — | `v1` | no | migration anchor |
| `reactor_id` | string | — | — | yes | nullable |
| `catalyst` | category | — | Ni/Al2O3, Ni-MgO, Rh, Pt, none, other | no | |
| `catalyst_loading_wt_pct` | float32 | wt% | 0–20 | yes | |
| `temperature_c` | float32 | °C | 500–1000 | no | **hard cap 1000** |
| `pressure_bar` | float32 | bar | 1–30 | no | |
| `ch4_o2_ratio` | float32 | mol/mol | 1.4–2.5 | no | |
| `co2_ch4_ratio` | float32 | mol/mol | 0.0–1.5 | no | |
| `h2o_ch4_ratio` | float32 | mol/mol | 0.0–1.5 | no | steam |
| `ghsv_per_h` | float32 | h⁻¹ | 1e3–1e5 | no | space velocity |
| `n2_dilution_mol_pct` | float32 | mol% | 0–50 | yes | |
| `contact_time_ms` | float32 | ms | derived | yes | recomputed, not trusted |
| `ch4_conversion` | float32 | fraction | 0–1 | no | |
| `co2_conversion` | float32 | fraction | 0–1 | no | |
| `o2_conversion` | float32 | fraction | 0–1 | no | |
| `h2_yield_mol_per_mol_ch4` | float32 | mol/mol | 0–4 | no | |
| `co_yield_mol_per_mol_ch4` | float32 | mol/mol | 0–4 | no | |
| `h2_co_ratio` | float32 | mol/mol | derived | no | `h2/co`, guard `co>0` |
| `syngas_yield_mol_per_mol_ch4` | float32 | mol/mol | derived | no | `h2 + co` |
| `ch4_slip_pct` | float32 | % | 0–100 | no | `(1-conv)*100` |
| `carbon_deposition_mg_per_gcat` | float32 | mg C/g_cat | 0–100 | no | safety-critical |
| `carbon_risk_class` | category | — | none, low, moderate, high | no | derived |
| `energy_input_kw` | float32 | kW | 0–1e5 | yes | TEA input |
| `balance_error_pct` | float32 | % | −2…+2 | no | elemental C/H/O closure |
| `quality_flag` | category | — | valid, suspect, rejected | no | |
| `notes` | string | — | — | yes | |

### 5.1 Proposed Pandas schema + validator contract

```python
# backend/src/odrm/data/schema.py  (proposal — Sprint 1)
import pandas as pd

REQUIRED: dict[str, str] = {
    "run_id": "string", "created_at": "datetime64[ns, UTC]",
    "source": "category", "schema_version": "string",
    "catalyst": "category", "temperature_c": "float32",
    "pressure_bar": "float32", "ch4_o2_ratio": "float32",
    "co2_ch4_ratio": "float32", "h2o_ch4_ratio": "float32",
    "ghsv_per_h": "float32", "ch4_conversion": "float32",
    "co2_conversion": "float32", "o2_conversion": "float32",
    "h2_yield_mol_per_mol_ch4": "float32", "co_yield_mol_per_mol_ch4": "float32",
    "h2_co_ratio": "float32", "syngas_yield_mol_per_mol_ch4": "float32",
    "ch4_slip_pct": "float32", "carbon_deposition_mg_per_gcat": "float32",
    "carbon_risk_class": "category", "balance_error_pct": "float32",
    "quality_flag": "category",
}

BOUNDS = {
    "temperature_c": (500.0, 1000.0),   # HARD max 1000
    "pressure_bar": (1.0, 30.0),
    "ch4_o2_ratio": (1.4, 2.5),
    "co2_ch4_ratio": (0.0, 1.5),
    "h2o_ch4_ratio": (0.0, 1.5),
    "ch4_conversion": (0.0, 1.0),
    "co2_conversion": (0.0, 1.0),
    "o2_conversion": (0.0, 1.0),
    "carbon_deposition_mg_per_gcat": (0.0, 100.0),
    "balance_error_pct": (-2.0, 2.0),
}

RISK_THRESHOLDS = {  # mg C / g_cat -> class
    "none": (0.0, 1.0), "low": (1.0, 5.0),
    "moderate": (5.0, 20.0), "high": (20.0, None),
}

def validate_odrm_frame(df: pd.DataFrame) -> pd.DataFrame: ...
# raises SchemaError / BoundsError / BalanceError; returns a copy with
# derived columns recomputed and quality_flag set. Never mutates in place.
```

**Validation rules (all raise, none clamp)**
1. Required columns present; dtypes coerced or rejected.
2. No nulls in required columns.
3. `temperature_c <= 1000` and all `BOUNDS` respected.
4. Elemental C/H/O balance within ±2% (`balance_error_pct`).
5. `h2_co_ratio`, `syngas_yield_mol_per_mol_ch4`, `ch4_slip_pct` recomputed and compared.
6. `carbon_risk_class` consistent with `RISK_THRESHOLDS`.
7. `quality_flag == "rejected"` rows are dropped before training, never silently kept.

---

## 6. Sprint 0 Execution Order (on approval)

1. Create `pyproject.toml` + `.env.example`; install into `.venv`; freeze `requirements.txt`.
2. Scaffold `backend/src/odrm/` packages and `backend/tests/` tree (empty modules + `__init__.py`).
3. Write `conftest.py` + one smoke test asserting the harness blocks network calls.
4. Scaffold Next.js frontend; add `typecheck` script and `api.ts` stub.
5. Write `docs/ARCHITECTURE.md` from the §4 outline.
6. Write `docs/SPRINT_WORKFLOW.md` (§7) and schema docs under `data/schemas/`.
7. Run all gates; report evidence in the Sprint 0 review note.

---

## 7. Governance Gaps & Risks

### 7.1 Governance gap (blocking a clean gate)
`cto-architect` binds us to `SPRINT_WORKFLOW.md`, but **no such file exists in the repo**
(only referenced from `.opencode/skills/cto-architect/SKILL.md:3`). Sprint 0 should create
it — covering plan→approval→execute→evidence→review, commit hygiene, and the "no code
before approved plan" rule. Until it exists, this document is the operative contract.

### 7.2 Risk register (Sprint 0)
| ID | Risk | P | I | Mitigation |
|---|---|---|---|---|
| R0-1 | LangChain dependency churn breaks install | M | M | Freeze lock immediately; isolate agent deps behind `[agent]` extra if needed |
| R0-2 | Windows + Python 3.12 wheels for XGBoost/sklearn | M | M | Pin to wheel-publishing versions; fall back to 3.11 |
| R0-3 | Frontend scaffold refuses non-empty dir | L | L | Temp-dir scaffold + move (§3.1) |
| R0-4 | Schema drifts once HYSYS/COMSOL exports arrive | H | H | `schema_version` + manifest + validator tests from day one |
| R0-5 | Surrogate trusted outside validity envelope | M | H | Explicit OOD guard + applicability envelope documented in ARCHITECTURE |
| R0-6 | LLM invents physics parameters | M | H | Tool-calling + strict JSON schema tests; no free-form numbers path |
| R0-7 | `SPRINT_WORKFLOW.md` missing | H | M | Create in Sprint 0 (§7.1) |
| R0-8 | Secrets committed during setup | L | H | `.env.example` only; `.env` in `.gitignore`; secret scan in CI |

### 7.3 Open questions for the reviewer
1. Python **3.11** baseline (max compatibility) vs **3.12** (performance)? Recommend 3.11.
2. Hosting target for the API — Render/Railway/Fly/AWS? Affects container choices later.
3. Is tenant data ever permitted to improve the shared surrogate? Affects §4.3 and ToS.
4. Confirm `SPRINT_WORKFLOW.md` should be authored by me in Sprint 0.

---

## 8. Approval Gate

**STOP.** No terminal commands, dependency installs, scaffolds, or code will be executed
until this plan is approved. On approval I will execute §6 in order and return a review
note with command output as evidence.

**Requested decision:** Approve as-is · Approve with changes (list them) · Reject.
