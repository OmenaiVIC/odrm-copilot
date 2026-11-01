# ODRM-Copilot — System Architecture

| | |
|---|---|
| Status | Draft — Sprint 0 foundation |
| Owner | CTO / Principal Architect |
| Last updated | 2026-11-01 |
| Scope | Architecture baseline for Sprints 1–8; Sprint 0 delivers no product features |

ODRM-Copilot is a B2B SaaS surrogate-model and decision-support platform for
**Oxy-Dry Reforming of Methane (ODRM)** and flare-gas valorization. It predicts
syngas yield, carbon deposition risk, and economics from process conditions, and
explains those predictions through a tool-constrained agent.

---

## 1. Product context

**Users**

- Process engineers evaluating ODRM / flare-gas conversion concepts.
- Sustainability and operations teams screening carbon and flaring-reduction options.
- EPCs and consultancies producing pre-feasibility studies.
- Platform admins managing tenants, quotas, and audit exports.

**Jobs to be done**

1. "Given these feed and reactor conditions, what syngas yield and carbon risk should I expect?"
2. "Which operating window maximizes syngas while keeping carbon deposition safe?"
3. "What is the bankable economics of this configuration?"
4. "Show me the evidence, uncertainty, and validity envelope behind the answer."

**Non-goals (initial releases)**

- Replacing detailed HYSYS/COMSOL simulation or CFD.
- Closed-loop plant control.
- Cross-tenant model training without explicit, recorded consent.

---

## 2. C4 Level 1 — System context

```
Process engineer / operator / EPC ─┐
Sustainability officer ────────────┤
Platform admin ────────────────────┘
                                   ▼
                        ┌─────────────────────┐
   Gas analysis / SCADA │   ODRM-Copilot      │  LLM provider (tool-calling only)
   historian ──────────►│  (SaaS)             │◄───────────────────────────────
   Lab / HYSYS exports ►│                     │
                        └──────────┬──────────┘
                                   │
                    ┌──────────────┼───────────────┐
                    ▼              ▼               ▼
             Surrogate model  Optimizer /     TEA + report
             (XGBoost)        scenario sweep  exporter
```

External systems are file-based in early sprints (CSV/Parquet upload). Direct
historian connectors are post-pilot.

---

## 3. C4 Level 2 — Containers

| Container | Responsibility | Sprint introduced |
|---|---|---|
| `frontend/` — Next.js App Router | Auth shell, dataset upload, prediction/sweep UI, agent chat, report viewer | 0 (scaffold), 4 (MVP) |
| `backend/` — FastAPI | REST API, validation, orchestration, auth, metering | 0 (health), 3 |
| Physics / bounds guard | Hard validity checks, risk thresholds, OOD gate | 1–2 |
| ML registry | Artifact storage, metadata, promotion, rollback | 2 |
| Data lake | Immutable validated Parquet batches + manifests | 1 |
| Postgres (Neon later) | Tenants, users, datasets metadata, runs, audit log | 3 |
| Object store (later) | Large Parquet artifacts, report exports | 5 |
| Agent runtime | LangChain tool-calling over domain tools | 5 |

### Request path — natural language

```
NL input
  → LangChain agent (tool selection)
  → strict JSON args
  → Pydantic request model
  → BOUNDS / physics guard (hard reject)
  → schema + OOD check
  → XGBoost surrogate (+ uncertainty)
  → optimizer / sweep
  → TEA
  → response + confidence + provenance
```

### Request path — direct API

```
JSON request → Pydantic → physics guard → OOD check → surrogate → response
```

### Failure semantics

| Condition | Behaviour |
|---|---|
| Malformed request | `422` with field-level detail |
| Out of bounds (`temperature_c > 1000`, etc.) | `422`, no prediction, explanation of violated bound |
| In-bounds but out-of-distribution | `200` prediction flagged `ood: true` + confidence penalty; UI warning |
| Unsafe carbon risk | hard block for "recommended" actions; advisory prediction still returned with `risk_class: high` |
| Model missing / corrupt | `503`, no silent fallback |
| LLM unavailable | agent returns typed `503`; direct prediction API unaffected |
| LLM tries free-form physics | rejected before execution; tool args are schema-validated |

---

## 4. Tech stack and decisions

| Component | Choice | Version | Rationale | ADR |
|---|---|---|---|---|
| Frontend | Next.js App Router + TypeScript | 16.4.x (React 19.3) | SSR-capable, deploy to Vercel | ADR-001 |
| Styling | Tailwind CSS v4 | 4.x | Utility-first, zero-runtime, v4 auto-content detection | ADR-002 |
| Client data | TanStack Query (Sprint 4) | 5.x | Cache, retries, request states | ADR-003 |
| Charts | Recharts (Sprint 4) | 3.x | Parity plots, sensitivity curves | ADR-003 |
| API | FastAPI + Pydantic v2 | FastAPI 0.11x / Pydantic 2.x | OpenAPI contract, typed validation | ADR-004 |
| Data | Pandas + PyArrow Parquet | 3.1 / current | Columnar, typed, cheap to version | ADR-005 |
| ML | XGBoost + scikit-learn | 3.x / 1.x | Strong tabular baseline, fast inference | ADR-006 |
| Registry | `joblib` + JSON metadata (Sprint 2) | — | Simple, portable; DB-backed later | ADR-007 |
| Agent | LangChain tool-calling | 1.4.x | Typed tools, provider-agnostic | ADR-008 |
| DB | Postgres 16 + RLS (Sprint 3) | 16 | Tenant isolation at the database layer | ADR-009 |
| Local ops | Docker Compose (Sprint 3) | — | Reproducible dev parity | ADR-010 |
| CI | GitHub Actions (Sprint 3) | — | Lint, typecheck, test, secret scan | ADR-011 |

Python target is **3.11** (`>=3.11,<3.13`) for wheel availability across
XGBoost/scikit-learn/LangChain.

---

## 5. Data architecture

### 5.1 Canonical contract

The ODRM v1 contract is machine-readable at [`data/schemas/odrm_v1.json`](../data/schemas/odrm_v1.json)
(JSON Schema 2020-12) and documented in [`docs/SPRINT_0_PLAN.md`](SPRINT_0_PLAN.md) §5.

- **29 columns: 23 required, 6 nullable.**
- Units are explicit per column; unit-free numbers are rejected.
- Hard physics bound: `temperature_c <= 1000 °C`.
- Derived columns (`h2_co_ratio`, `syngas_yield_mol_per_mol_ch4`, `ch4_slip_pct`,
  `carbon_risk_class`) are **recomputed, never trusted**.
- `quality_flag == "rejected"` rows are dropped before training.

`backend/src/odrm/data/schema.py` (Sprint 1) will implement:

```python
REQUIRED: dict[str, str]
BOUNDS: dict[str, tuple[float, float]]
RISK_THRESHOLDS: dict[str, tuple[float, float | None]]
validate_odrm_frame(df) -> pd.DataFrame   # raises; returns a copy; never mutates
```

All validation failures raise (`SchemaError`, `BoundsError`, `BalanceError`).
**Nothing is clamped silently.**

### 5.2 Storage layout

```
data/
  raw/                       # untouched uploads (gitignored)
  processed/odrm/v1/
    <batch_id>.parquet       # immutable validated batch
    _manifest.json           # row count, SHA-256, schema_version, generator, seed
  schemas/odrm_v1.json       # contract source of truth
models/
  odrm/<target>/<version>/   # joblib artifact + metadata.json
```

### 5.3 Schema versioning policy

- `schema_version` is a column and a filename component.
- Additive optional columns → `v1.x`; breaking changes → `v2` with a migration script.
- Migrations never overwrite a batch: they emit a new batch + manifest.
- A model records the schema version(s) it was trained on; inference rejects
  mismatched required columns.
- Dataset identity = content SHA-256, so duplicate uploads dedupe naturally.

### 5.4 Data quality gates

1. Required columns present; dtypes coerced or rejected.
2. No nulls in required columns.
3. All `BOUNDS` respected, including the 1000 °C cap.
4. Elemental C/H/O closure within ±2 % (`balance_error_pct`).
5. Derived columns recomputed and compared.
6. `carbon_risk_class` consistent with thresholds.
7. Duplicate `run_id` rejected.

---

## 6. ML and surrogate lifecycle

### 6.1 Targets

Primary regressors: `h2_yield_mol_per_mol_ch4`, `co_yield_mol_per_mol_ch4`,
`ch4_conversion`, `carbon_deposition_mg_per_gcat`.
Classifier: `carbon_risk_class`.

### 6.2 Splits and gates

- Grouped split by `run_id`/batch; no leakage across temporal or process groups.
- Train / validation / held-out test; test set touched once per promotion.
- **Promotion gate: test R² > 0.95 per primary target**, plus MAE thresholds and
  no regression on carbon-risk recall. A model failing the gate cannot be promoted.
- Parity plots and residual summaries are attached to every candidate.

### 6.3 Uncertainty and applicability envelope

- Ensemble variance or quantile regressors for prediction intervals.
- Applicability envelope stored with the artifact: feature ranges, convex-hull /
  Mahalanobis distance threshold calibrated on training data.
- OOD = outside envelope but inside physical bounds → prediction returned with
  `ood: true`, lowered confidence, and a UI warning.
- Outside physical bounds → rejected before the model is called.

### 6.4 Registry and drift

- Artifact + `metadata.json`: schema version, training data hash, metrics, git SHA,
  feature list, envelope, creation time.
- Promotion/rollback is explicit; inference pins a version.
- Inference logs store feature hash + model version (not raw customer data by default).
- Drift monitoring on feature distributions and residual trends; alert before
  silent degradation.

### 6.5 Later: hybrid physics-informed models

Phase 2 explores physics-informed neural networks / GNNs for extrapolation and
mechanism awareness. XGBoost remains the trusted baseline and fallback; no hybrid
model ships without beating the R² gate **and** the validation appendix.

---

## 7. Agent architecture (Sprint 5, faked in Sprint 0)

Four layers, each independently testable:

| Layer | Responsibility |
|---|---|
| L1 Orchestration | LangChain/LangGraph loop; chooses tools, never computes physics itself |
| L2 Tools | `validate_conditions`, `predict_syngas`, `simulate_sweep`, `estimate_tea`, `compare_runs`, `retrieve_docs`, `export_report` |
| L3 Domain guardrails | JSON-schema args, bounds check, carbon-risk block, citation requirement, human approval for exports |
| L4 Observability | Structured traces per step, tool-call audit, eval suite, token/cost caps |

Rules:

- The LLM may only emit tool calls with strict JSON schemas; free-form numeric
  answers are not a code path.
- Tool results carry units, model version, and confidence; the agent must surface them.
- Unsafe carbon risk is a hard block with an explanation, not a suggestion.
- Prompt-injection defenses: retrieved documents are data, never instructions.
- Evals assert tool selection and arguments (spy-based), not prose similarity.
- A provider abstraction keeps the LLM swappable; tests use LangChain fake models
  and network is blocked in the test harness.

---

## 8. API design (`/api/v1`)

| Method | Path | Purpose | Sprint |
|---|---|---|---|
| GET | `/health` | Liveness + env | 0 (live) |
| GET | `/ready` | Dependency readiness | 3 |
| POST | `/auth/login`, `/auth/refresh` | JWT issue/rotate | 3 |
| GET/POST | `/plants` | Tenant plant profiles | 3 |
| POST | `/datasets` | Upload + validate batch | 1/3 |
| GET | `/datasets`, `/datasets/{id}` | List/detail + manifest | 3 |
| POST | `/models/train` | Train candidate | 2/3 |
| GET | `/models`, `/models/{id}` | Registry + metrics | 2/3 |
| POST | `/models/{id}/promote` | Gate-checked promotion | 3 |
| POST | `/predictions` | Single prediction | 2/3 |
| POST | `/predictions/batch` | Batch prediction | 4 |
| POST | `/simulations` | Parameter sweep / optimize | 4 |
| POST | `/agent/chat` | Tool-constrained agent turn | 5 |
| GET | `/agent/runs/{id}` | Trace + tool calls | 5 |
| POST | `/reports/tea` | Techno-economic report | 6 |
| GET | `/admin/audit` | Audit export | 6 |

**Error envelope**

```json
{
  "error": {
    "code": "BOUNDS_VIOLATION",
    "message": "temperature_c must be <= 1000",
    "details": {"field": "temperature_c", "value": 1200},
    "request_id": "..."
  }
}
```

- Versioning: URL major version (`/api/v1`); additive changes only within a major.
- Idempotency: `Idempotency-Key` required on dataset upload, training, and reports;
  stored per tenant with request hash.
- Rate limits: per tenant + per API key; metered endpoints return quota headers.
- Pagination: cursor-based for lists; explicit `limit` caps.
- OpenAPI is generated from Pydantic and treated as the frontend contract.

---

## 9. Security, multi-tenancy, compliance

- **Isolation:** `tenant_id` on every row; Postgres Row-Level Security enforced in
  addition to application scoping. Cross-tenant reads fail closed.
- **Training:** customer data never enters cross-tenant training without explicit,
  recorded opt-in; enterprise can pin a private model instance.
- **AuthN/AuthZ:** short-lived JWT access + rotating refresh; Argon2 password hashing;
  role-based access (`owner`, `engineer`, `viewer`, `admin`); API keys stored hashed.
- **Secrets:** environment/secret manager only; `.env.example` committed, `.env` ignored;
  CI secret scan.
- **Transport/at rest:** TLS everywhere; encrypted volumes/backups.
- **Audit:** append-only log of who/what/when/why with input hash and model version;
  hash-chained to detect tampering; exportable for enterprise.
- **Privacy:** no PII in logs; data deletion honored per tenant with verifiable purge.
- **LLM safety:** no customer data to providers beyond the minimum prompt; provider
  zero-retention mode where available; tool-only execution.

---

## 10. Observability and non-functional requirements

| Concern | Target |
|---|---|
| Single prediction latency (p95) | < 300 ms warm |
| Dataset validation (100k rows) | < 60 s async job |
| Agent turn (p95) | < 8 s |
| API availability | 99.5 % (pilot), 99.9 % (enterprise) |
| RPO / RTO | 24 h / 4 h (pilot) |
| Cost ceiling | per-tenant inference + LLM budget enforced |
| Logging | structured JSON, request/trace IDs, no secrets/PII |
| Metrics | latency, error rate, OOD rate, drift, quota burn |
| Traces | per agent step + tool call |

---

## 11. Commercial model — "shovel and picks"

- **Positioning:** sell simulation-grade prediction at a fraction of HYSYS cost;
  customers keep their process IP.
- **ICP:** flare-gas owners/operators, EPCs, consultancies in the Global South.
- **Tiers:** Explorer (free, capped) → Pro (seat + quota) → Enterprise (private model,
  VPC/on-prem, SLA, audit export).
- **Metering:** per successful inference/solve, not per token; failed validations free.
- **Moat:** validated runs improve the surrogate; tenant isolation is non-negotiable.
- **Unit economics:** track cost-to-serve per solve vs price; margin target per tier.
- **Adjacent picks:** bankable TEA reports, API access, calibration services.
- **Anti-pattern:** never claim HYSYS/COMSOL equivalence without the validation
  appendix; always publish error bars and the applicability envelope.

---

## 12. Deployment topology and environments

| Environment | Frontend | Backend | DB | Artifacts |
|---|---|---|---|---|
| Local (Sprint 0–2) | `npm run dev` | `uvicorn` | none / SQLite-free | local Parquet + `models/` |
| Local (Sprint 3+) | Docker Compose | Docker | Postgres 16 | volume |
| CI | build only | lint/test | ephemeral | — |
| Production (later) | Vercel | Render or Fly.io | Neon Postgres | S3-compatible store |

No cloud deployment occurs in Sprint 0. The local stack is kept Docker-compatible
so later containerization does not require restructuring.

---

## 13. ADR index

| ADR | Decision |
|---|---|
| ADR-001 | Next.js App Router + TypeScript |
| ADR-002 | Tailwind CSS v4 (no JS config; auto content detection) |
| ADR-003 | TanStack Query + Recharts deferred to Sprint 4 |
| ADR-004 | FastAPI + Pydantic v2 as schema-first API |
| ADR-005 | Parquet as the canonical validated data format |
| ADR-006 | XGBoost-first surrogate; hybrid models only after the gate |
| ADR-007 | joblib + JSON metadata registry, DB-backed later |
| ADR-008 | LangChain tool-calling only; no free-form physics |
| ADR-009 | Postgres RLS for tenant isolation |
| ADR-010 | Docker Compose for local parity |
| ADR-011 | GitHub Actions as CI, including secret scan |

---

## 14. Risks

| ID | Risk | P | I | Mitigation |
|---|---|---|---|---|
| R0-1 | Dependency churn (LangChain) | M | M | Frozen lock; agent deps isolatable |
| R0-2 | Windows/Python wheel gaps | M | M | Pin 3.11; verified install |
| R0-3 | Scaffold refuses non-empty dir | L | L | Empty-dir scaffold; verified |
| R0-4 | Schema drift (HYSYS/COMSOL) | H | H | Versioned contract + manifest + validator tests |
| R0-5 | Surrogate trusted outside envelope | M | H | OOD guard + documented envelope |
| R0-6 | LLM invents physics | M | H | Tool-only path + argument schema tests |
| R0-7 | Missing workflow contract | H | M | `SPRINT_WORKFLOW.md` created |
| R0-8 | Secrets committed | L | H | `.env.example` only; `.env` ignored; CI scan |
| R1-1 | Cross-tenant data leakage | L | H | RLS + app scoping + tests per tenant |
| R1-2 | Weak validation lets bad data train | M | H | Reject-not-clamp validator; golden fixtures |

---

## 15. Milestones

| Sprint | Outcome | Exit criteria |
|---|---|---|
| 0 | Foundation | Scaffolds, tests green, architecture + schema docs, report |
| 1 | Data | `validate_odrm_frame` + fixtures + Parquet manifests green |
| 2 | Surrogate | R² > 0.95 gate, OOD guard, registry |
| 3 | API + DB | Auth, tenant RLS, dataset/model/prediction endpoints |
| 4 | Frontend MVP | Upload → predict → parity/sweep UI |
| 5 | Agent | Tool-constrained assistant + trace/eval suite |
| 6 | Reports + TEA | Bankable report export, audit trail |
| 7 | Billing + hardening | Quotas, metering, rate limits, load tests |
| 8 | Pilots | Design-partner deployments and validation appendices |

---

## 16. Open questions

1. Which LLM provider is the production default (cost vs data residency)?
2. Enterprise on-prem packaging: container bundle vs private VPC deployment?
3. Minimum validation dataset size per catalyst family before claims are allowed?
4. Pricing unit: per solve, per seat, or blended?
5. Historian/SCADA connector priority for the first pilot?
