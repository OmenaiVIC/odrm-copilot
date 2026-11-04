# Sprint 3 Plan — TEA Engine & Financial Output

**Project:** ODRM-Copilot / Valoris  
**Sprint:** 3 — Techno-Economic Analysis (TEA) Engine & Financial Output  
**Owner:** CTO / Systems Architect  
**Status:** 🟡 Awaiting review — execution blocked until approval  
**Date:** 2026-11-04  
**Approval phrase:** `AUTHORIZED: Sprint 3 implementation phase`

> **Phase gate.** This document is the only Sprint 3 artifact created before
> authorization. No implementation code, tests, routes, schemas, or commits are made
> until the CTO replies with the exact approval phrase above. The Phase 5 report
> (`docs/SPRINT_3_REPORT.md`) is explicitly out of scope and requires a separate
> authorization after the CTO audit.

---

## 0. Sprint Charter

### 0.1 Goal

Sprint 3 turns the surrogate prediction into a **screening financial estimate**. Given
process conditions and a small set of economic assumptions, the system returns:

- estimated daily syngas production and revenue,
- estimated carbon-credit value,
- estimated net operating cash flow,
- simple Return on Investment (ROI), and
- simple payback period.

The TEA engine is a **pure, deterministic domain calculation**. It does not call the
network, does not read live market prices, and does not retrain or alter the Sprint 2
models.

### 0.2 In scope

- `backend/src/odrm/domain/tea.py`: pure TEA calculation, input validation, domain
  errors, and unit constants.
- `backend/src/odrm/domain/tea_defaults.py` (optional, small): engineering defaults and
  their provenance. Market prices are **not** defaulted.
- `backend/src/odrm/services/prediction.py`: extract the existing inference loop into a
  shared helper so `/predict` and `/tea` cannot drift.
- `backend/src/odrm/api/schemas.py` (implementation phase only): TEA request/response
  Pydantic models composed around the existing `PredictRequest`.
- `backend/src/odrm/api/routes.py` (implementation phase only): the TEA route.
- Unit tests for the pure engine, Pydantic validation, and the API contract.
- Integration test covering the full request → prediction → TEA → response path with
  stub models.
- Documentation of TEA assumptions and the new endpoint (README/API examples), after
  authorization. The Sprint 3 report is deferred to Phase 5.

### 0.3 Explicitly out of scope

- A new ML model or retraining; including a `co2_conversion` surrogate. Carbon credit
  volume is an explicit assumption, not a new model output.
- Carbon deposition regression or the `carbon_risk_class` classifier.
- The Agentic Orchestrator (LangChain), agent tools, prompts, and chat UI.
- Frontend/UI changes, charts, and the ESG dashboard.
- Live market-price feeds, external APIs, background price refresh, or any network
  access in the engine, tests, or endpoint.
- NPV, IRR, discounted cash flow, tax, depreciation, financing, inflation, FX,
  sensitivity analysis, Monte Carlo, or scenario sweeps.
- Full life-cycle assessment or verified carbon accounting; carbon credits are a
  screening estimate only.
- Batch TEA, async jobs, queues, caching, or persistence of TEA results.
- Changes to `data/schemas/odrm_v1.json`, `data/odrm_dataset.parquet`, or the Sprint 2
  model artifacts.
- The Phase 5 report.

### 0.4 Roadmap reconciliation (must be acknowledged)

The current `docs/strategy/MASTER_ROADMAP.md` labels Sprint 3 as **Agentic
Orchestrator** and Sprint 5 as **TEA**, while `docs/ARCHITECTURE.md` places TEA/report
work around Sprint 6. The Sprint 3 directive in this task explicitly makes **TEA Engine
& Financial Output** the Sprint 3 deliverable.

This plan follows the CTO directive. The Agentic Orchestrator is **deferred, not
removed**. After approval, the roadmap and architecture documents should be reconciled
in a separate documentation change so the repository does not contain contradictory
sprint numbering. This plan does not silently rewrite those documents.

### 0.5 Deliverables checklist (exit criteria)

| # | Deliverable | Verification |
|---|---|---|
| 1 | Pure `TeaInputs` / `TeaResult` / `calculate_tea` domain engine | Golden-value and invariant unit tests pass |
| 2 | Explicit input validation and domain errors | Invalid prices, capex, hours, days, fraction, non-finite values rejected |
| 3 | Carbon-credit calculation with a stated, conservative basis | Credit formula test; zero-fraction warning test |
| 4 | TEA Pydantic schemas composed from `PredictRequest` | 422 tests for missing/extra/out-of-range fields |
| 5 | `POST /api/v1/tea` returns predictions + financials + warnings | 200/422/503/500 API tests pass |
| 6 | Shared inference helper preserves `/predict` behaviour | Existing `/predict` tests still pass |
| 7 | File/line coverage ≥ 90% for `odrm/domain/tea.py` and TEA API paths | Coverage report |
| 8 | `pytest`, `ruff`, and `mypy` clean | Raw gate commands in §7 |
| 9 | No schema/model/network/binary changes | `git status`, diff audit, network-blocked tests |

### 0.6 Definition of Done (global)

Code review approved · TDD evidence recorded · lint clean (`ruff`) · type check clean
(`mypy`) · tests green · docs updated · no secrets committed · no binary artifacts
committed · no schema or model generation touched · reproducible from the project venv ·
no network access in tests or runtime.

### 0.7 Traceability

| Source | Deliverable |
|---|---|
| CTO Sprint 3 directive (2026-11-04) | TEA engine, financial outputs, `/api/v1/tea` design, TDD plan |
| `MASTER_ROADMAP.md` Sprint 5 | "Estimated ROI based on inputted gas costs and carbon credit values"; "Estimated Profit" |
| `ARCHITECTURE.md` §3 request path | surrogate → TEA → response |
| `ARCHITECTURE.md` §8 | `/api/v1` versioning, error semantics, future TEA/report surface |
| `README.md` | TEA is the product's financial differentiator; sub-50 ms surrogate |
| `SPRINT_2_REPORT.md` | Accepted `/api/v1/predict`, model versions, R²/RMSE evidence |
| `SPRINT_WORKFLOW.md` | Plan-first, TDD, review gate, report |
| Sprint 1 `schema.py` / `synthetic.py` | `syngas_yield` is mol syngas per mol CH4 **fed** |

---

## 1. Source of Truth and Modelling Stance

### 1.1 Verified Sprint 2 state

| Item | Value |
|---|---|
| Endpoint | `POST /api/v1/predict` |
| Request model | `PredictRequest` in `backend/src/odrm/api/schemas.py` |
| Response | `predictions: dict[str, float]`, `model_version: str` |
| Targets | `ch4_conversion`, `syngas_yield_mol_per_mol_ch4` |
| `ch4_conversion` model | `v1-20261104T120949Z` (test R² 0.9887, RMSE 0.0285) |
| `syngas_yield` model | `v1-20261104T121024Z` (test R² 0.9888, RMSE 0.1000) |
| Model loading | `create_app` loads both into `app.state.models`; missing model → boot + `503` |
| Test harness | `backend/tests/conftest.py` blocks outbound sockets |

### 1.2 Critical unit definition: syngas yield

`syngas_yield_mol_per_mol_ch4` is **mol of syngas (H2 + CO) produced per mol of CH4
fed**, not per mol of CH4 converted. This is confirmed by:

- `backend/src/odrm/data/synthetic.py`: `ch4_out = 1.0 - ...` and `h2_out` / `co_out`
  are computed on a 1-mol CH4-feed basis; `syngas_yield` is `h2_yield + co_yield`.
- `backend/src/odrm/data/schema.py`: `syngas_yield_mol_per_mol_ch4 = h2_yield +
  co_yield`, and `ch4_slip_pct = (1 - ch4_conversion) * 100`.

Therefore:

```text
syngas_kmol_per_day = ch4_feed_kmol_per_h × syngas_yield × operating_hours_per_day
```

**Do not** multiply by `ch4_conversion` again. A regression test will lock this basis.

### 1.3 Production basis

The Sprint 2 request contains `ghsv_per_h` but **not** a reactor volume or a molar feed
flow. GHSV alone cannot determine absolute molar throughput without reactor volume and
gas density/composition. Sprint 3 therefore requires an explicit
`ch4_feed_kmol_per_h` in the TEA assumptions. This is a deliberate contract addition,
not a derived value.

### 1.4 What this engine is and is not

- It is a **screening tool** for pre-feasibility comparisons, not an investment-grade
  financial model.
- It is deterministic and offline. The caller supplies prices; the backend does not
  fetch them.
- It inherits the synthetic-data limitation of the Sprint 2 surrogate. Financial
  outputs are only as credible as the process prediction and the user's assumptions.
- It does not account for purification, compression, downstream syngas conditioning,
  catalyst replacement cycles, taxes, depreciation, financing, inflation, or currency
  risk unless they are folded into the user-supplied CAPEX/OPEX.
- It does not make ESG or carbon-credit eligibility claims. Carbon credit value is a
  scenario estimate under an explicit assumption.

### 1.5 Non-negotiables

- No network access in the engine, tests, or endpoint.
- No silent fallback, no default market prices, no model substitution.
- No clamping of model predictions or financial outputs.
- No mutation of Sprint 2 artifacts, dataset, schema, or model metadata.
- No division by zero, no `NaN`/`Inf` in JSON responses.
- No `.joblib` files committed.
- No implementation before the exact approval phrase.

---

## 2. TEA Domain Engine

### 2.1 Module contract

`backend/src/odrm/domain/tea.py` exports:

| Symbol | Kind | Purpose |
|---|---|---|
| `TeaInputs` | frozen dataclass | Validated calculation inputs with units documented |
| `TeaResult` | frozen dataclass | Financial outputs plus warnings |
| `TeaInputError` | exception | Invalid assumption or prediction input |
| `TeaCalculationError` | exception | Non-finite/unrepresentable result |
| `calculate_tea(inputs)` | function | Pure, deterministic calculation |
| `CH4_LHV_MMBTU_PER_KMOL` | constant | `0.7603` (see §2.7) |
| `CO2_MOLAR_MASS_KG_PER_KMOL` | constant | `44.01` |
| `MOLAR_VOLUME_NM3_PER_KMOL` | constant | `22.414` at 0 °C, 1 atm |

The domain module must not import FastAPI, Pydantic, pandas, or any I/O library. It is
plain Python plus `math` so it can be tested in isolation.

### 2.2 Inputs

`TeaInputs` fields, units, and validation:

| Field | Unit | Required | Default | Validation |
|---|---|---|---|---|
| `syngas_yield_mol_per_mol_ch4` | mol syngas / mol CH4 fed | yes | — | finite; `≥ 0`; `> 8` allowed but warned |
| `ch4_feed_kmol_per_h` | kmol CH4 / h | yes | — | finite; `> 0`; `≤ 1,000,000` |
| `co2_ch4_ratio` | mol CO2 / mol CH4 fed | yes | — | finite; `≥ 0`; `≤ 1.5` |
| `natural_gas_price_usd_per_mmbtu` | USD / MMBtu | yes | — | finite; `≥ 0`; `≤ 1,000` |
| `syngas_price_usd_per_kmol` | USD / kmol syngas | yes | — | finite; `≥ 0`; `≤ 1,000,000` |
| `carbon_credit_price_usd_per_tonne_co2e` | USD / t CO2e | yes | — | finite; `≥ 0`; `≤ 100,000` |
| `co2_utilization_fraction` | fraction of feed CO2 consumed | yes | `0.0` | finite; `0–1` |
| `capex_usd` | USD, total installed | yes | — | finite; `> 0`; `≤ 1e12` |
| `opex_pct_of_capex_per_year` | % of CAPEX / year | yes | `5.0` | finite; `0–100` |
| `operating_hours_per_day` | h / day | yes | `24.0` | finite; `> 0`; `≤ 24` |
| `operating_days_per_year` | days / year | yes | `330.0` | finite; `> 0`; `≤ 365` |

Notes:

- **Market prices are required.** Sprint 3 does not ship default gas, syngas, or carbon
  prices. A static price book is an option only if the CTO requests it (OQ-6).
- Engineering defaults (`24 h/day`, `330 days/year`, `5 % CAPEX/year`) are screening
  assumptions, not market data. They live in `tea_defaults.py` with provenance.
- `co2_utilization_fraction` defaults to `0.0`: no carbon credit is invented unless the
  caller explicitly supplies a utilization fraction. A warning is emitted when the
  fraction is zero and the carbon price is positive (OQ-5).
- The API composes the process fields from the existing `PredictRequest`, so process
  bounds cannot drift from Sprint 2. The domain re-checks the values it consumes.

### 2.3 Calculation pipeline

Let:

- `Y` = `syngas_yield_mol_per_mol_ch4` (mol syngas / mol CH4 fed)
- `n` = `ch4_feed_kmol_per_h`
- `h` = `operating_hours_per_day`
- `d` = `operating_days_per_year`
- `r_co2` = `co2_ch4_ratio`
- `f_co2` = `co2_utilization_fraction`
- `P_syngas` = `syngas_price_usd_per_kmol`
- `P_gas` = `natural_gas_price_usd_per_mmbtu`
- `P_co2` = `carbon_credit_price_usd_per_tonne_co2e`
- `C` = `capex_usd`
- `o` = `opex_pct_of_capex_per_year`

Equations:

```text
syngas_kmol_per_day        = n × Y × h
syngas_nm3_per_day         = syngas_kmol_per_day × 22.414
syngas_revenue_usd_per_day = syngas_kmol_per_day × P_syngas

co2_consumed_kmol_per_h    = n × r_co2 × f_co2
co2_consumed_t_per_day     = co2_consumed_kmol_per_h × h × 44.01 / 1000
carbon_credit_usd_per_day  = co2_consumed_t_per_day × P_co2

feed_cost_usd_per_day      = n × h × P_gas × 0.7603
opex_usd_per_day           = C × (o / 100) / d

total_revenue_usd_per_day  = syngas_revenue_usd_per_day + carbon_credit_usd_per_day
net_cash_flow_usd_per_day  = total_revenue_usd_per_day − feed_cost_usd_per_day
                             − opex_usd_per_day
annual_net_cash_flow_usd   = net_cash_flow_usd_per_day × d

roi_pct       = (annual_net_cash_flow_usd / C) × 100
payback_years = C / annual_net_cash_flow_usd   if annual_net_cash_flow_usd > 0
                else None
```

Interpretation:

- `roi_pct` is a **simple, pre-tax, undiscounted annual return** on total installed
  CAPEX. It is not IRR and not NPV.
- `payback_years` is **simple undiscounted payback**. It is `None` when annual net cash
  flow is zero or negative; the API serialises it as JSON `null`.
- Positive carbon credit value is added to cash flow. A caller who does not want
  credits in the ROI can set `carbon_credit_price_usd_per_tonne_co2e = 0`.
- `opex_pct_of_capex_per_year` is a fixed annual charge, independent of throughput.
  This deliberately lumps maintenance, labour, overhead, and consumables into one
  screening number. Variable OPEX is out of scope (OQ-7).

### 2.4 Outputs

`TeaResult` fields:

| Field | Unit | Notes |
|---|---|---|
| `syngas_kmol_per_day` | kmol / day | Production volume |
| `syngas_nm3_per_day` | Nm³ / day | At 0 °C, 1 atm; diagnostic |
| `syngas_revenue_usd_per_day` | USD / day | Volume × syngas price |
| `co2_consumed_tonnes_per_day` | t CO2 / day | Utilization basis |
| `carbon_credit_value_usd_per_day` | USD / day | Consumed CO2 × credit price |
| `total_revenue_usd_per_day` | USD / day | Syngas + carbon credit |
| `feed_cost_usd_per_day` | USD / day | Natural gas cost |
| `opex_usd_per_day` | USD / day | Annual OPEX / operating days |
| `net_cash_flow_usd_per_day` | USD / day | Total revenue − feed − OPEX |
| `annual_net_cash_flow_usd` | USD / year | Daily × operating days |
| `roi_pct` | % | Simple annual return on CAPEX |
| `payback_years` | years or `None` | Simple payback |
| `warnings` | tuple[str, ...] | Machine-readable warning codes |

Warning codes (stable strings, tested):

- `carbon_credit_not_included` — `co2_utilization_fraction == 0` while carbon price > 0.
- `negative_annual_cash_flow` — `annual_net_cash_flow_usd <= 0`; payback is null.
- `syngas_yield_out_of_envelope` — `Y > 8`; value is used unclamped and flagged.
- `zero_syngas_price` — syngas price is zero; product revenue is zero.
- `zero_carbon_price` — carbon price is zero; credit value is zero.

### 2.5 Numeric rules

- All inputs must be finite (`math.isfinite`). `NaN` and `±Inf` raise `TeaInputError`.
- `capex_usd` must be strictly positive; ROI and payback are undefined at zero CAPEX.
- Negative annual cash flow is **not** an error: it returns negative ROI and
  `payback_years = None` with `negative_annual_cash_flow`.
- Zero syngas yield is valid: production and syngas revenue are zero, feed/OPEX still
  apply, and payback may be null. No division by zero.
- No clamping. If the model returns `Y > 8`, TEA computes with that value and adds
  `syngas_yield_out_of_envelope`; it does not silently change the model output.
- Domain returns full float precision. Presentation rounding (USD to 2 decimals, ROI to
  2 decimals, payback to 4 decimals) happens in the response layer only.
- Any non-finite intermediate or output raises `TeaCalculationError` and maps to a
  `500`, never to a partial response.

### 2.6 Carbon-credit basis

**Recommended v1 basis: CO2 utilization.**

```text
CO2 consumed = CH4 feed × (CO2/CH4 feed ratio) × CO2 utilization fraction
CO2 credit value = CO2 consumed (tonnes) × carbon credit price
```

Rationale:

- It is tied to the ODRM reaction chemistry (CO2 is a reactant).
- It uses only the process conditions already in the request plus one explicit
  assumption (`co2_utilization_fraction`); it does not require a new `co2_conversion`
  model.
- It is conservative by default: the fraction is `0.0` unless the caller supplies one,
  so the system does not invent an environmental benefit.

Alternatives considered:

| Basis | Formula | Why not v1 |
|---|---|---|
| Avoided flaring | CH4 feed × flaring emission factor (≈2.75 tCO2/tCH4) | Credits the feed, ignores product emissions and baseline/additionality; easy to overclaim |
| User-supplied credit volume | Caller supplies tCO2e/day | Not a TEA calculation; hides the assumption |
| New `co2_conversion` surrogate | ML prediction | Scope expansion into model training, gates, and artifacts; deferred |

The response must carry `carbon_credit_not_included` when the fraction is zero, and the
documentation must state that the value is a screening scenario, not a verified credit.
The CTO must confirm this basis (OQ-5).

### 2.7 Unit constants and provenance

| Constant | Value | Basis |
|---|---|---|
| `CH4_LHV_MMBTU_PER_KMOL` | `0.7603` | CH4 LHV ≈ 50.0 MJ/kg; molar mass 16.04 kg/kmol; 1 MMBtu = 1,055.06 MJ |
| `CO2_MOLAR_MASS_KG_PER_KMOL` | `44.01` | Standard molar mass |
| `MOLAR_VOLUME_NM3_PER_KMOL` | `22.414` | Ideal gas at 0 °C, 1 atm |
| `DEFAULT_OPERATING_HOURS_PER_DAY` | `24.0` | Screening assumption; caller-overridable |
| `DEFAULT_OPERATING_DAYS_PER_YEAR` | `330.0` | Conservative 90.4 % availability; caller-overridable |
| `DEFAULT_OPEX_PCT_OF_CAPEX_PER_YEAR` | `5.0` | Screening assumption; caller-overridable |
| `DEFAULT_CO2_UTILIZATION_FRACTION` | `0.0` | Conservative: no credit unless supplied |

These are engineering conversions/assumptions, not market forecasts. They are kept in
one module with comments so they can be audited and changed in one place.

### 2.8 Worked example (golden test basis)

Inputs:

| Input | Value |
|---|---|
| `syngas_yield_mol_per_mol_ch4` | `2.5` |
| `ch4_feed_kmol_per_h` | `100.0` |
| `co2_ch4_ratio` | `0.5` |
| `co2_utilization_fraction` | `0.4` |
| `natural_gas_price_usd_per_mmbtu` | `3.0` |
| `syngas_price_usd_per_kmol` | `4.0` |
| `carbon_credit_price_usd_per_tonne_co2e` | `25.0` |
| `capex_usd` | `5,000,000.0` |
| `opex_pct_of_capex_per_year` | `5.0` |
| `operating_hours_per_day` | `24.0` |
| `operating_days_per_year` | `330.0` |

Expected outputs (full precision in tests, 6 decimals shown):

| Output | Expected |
|---|---:|
| `syngas_kmol_per_day` | 6000.000000 |
| `syngas_nm3_per_day` | 134484.000000 |
| `syngas_revenue_usd_per_day` | 24000.000000 |
| `co2_consumed_tonnes_per_day` | 21.124800 |
| `carbon_credit_value_usd_per_day` | 528.120000 |
| `total_revenue_usd_per_day` | 24528.120000 |
| `feed_cost_usd_per_day` | 5474.160000 |
| `opex_usd_per_day` | 757.575758 |
| `net_cash_flow_usd_per_day` | 18296.384242 |
| `annual_net_cash_flow_usd` | 6037806.800000 |
| `roi_pct` | 120.756160 |
| `payback_years` | 0.828115 |

Warnings: none.

---

## 3. API Design

### 3.1 Options

| Option | Shape | Pros | Cons |
|---|---|---|---|
| **A. Extend `/predict`** | Optional `assumptions` in `PredictRequest`; optional `financials` in `PredictResponse` | One round trip; existing clients keep working | Grows the accepted Sprint 2 contract; mixes prediction and finance validation; response becomes conditionally shaped |
| **B. New `/api/v1/tea`** | `conditions` + `assumptions` in; `predictions` + `financials` out | Keeps `/predict` stable; TEA can evolve independently; clear error semantics; maps to future `/reports/tea` | Slightly larger payload; UI may call two endpoints if it wants both |

**Recommendation: Option B — `POST /api/v1/tea`.** Sprint 2 is accepted and should not
be destabilised. TEA has a larger assumption surface and distinct validation rules.
The new route composes the existing `PredictRequest` so process bounds cannot drift.
If the CTO prefers Option A, the domain engine and tests remain valid; only the
transport layer changes (OQ-2).

### 3.2 Recommended contract (Option B)

`POST /api/v1/tea`

Request:

```json
{
  "conditions": {
    "temperature_c": 800.0,
    "pressure_bar": 10.0,
    "ch4_o2_ratio": 2.0,
    "co2_ch4_ratio": 0.5,
    "h2o_ch4_ratio": 0.2,
    "ghsv_per_h": 5000.0,
    "catalyst": "Ni/Al2O3",
    "catalyst_loading_wt_pct": 10.0,
    "n2_dilution_mol_pct": null
  },
  "assumptions": {
    "ch4_feed_kmol_per_h": 100.0,
    "natural_gas_price_usd_per_mmbtu": 3.0,
    "syngas_price_usd_per_kmol": 4.0,
    "carbon_credit_price_usd_per_tonne_co2e": 25.0,
    "co2_utilization_fraction": 0.4,
    "capex_usd": 5000000.0,
    "opex_pct_of_capex_per_year": 5.0,
    "operating_hours_per_day": 24.0,
    "operating_days_per_year": 330.0
  }
}
```

Response (200):

```json
{
  "predictions": {
    "ch4_conversion": 0.8731,
    "syngas_yield_mol_per_mol_ch4": 2.4102
  },
  "model_versions": {
    "ch4_conversion": "v1-20261104T120949Z",
    "syngas_yield_mol_per_mol_ch4": "v1-20261104T121024Z"
  },
  "financials": {
    "syngas_kmol_per_day": 5784.48,
    "syngas_nm3_per_day": 129674.39,
    "syngas_revenue_usd_per_day": 23137.92,
    "co2_consumed_tonnes_per_day": 21.1248,
    "carbon_credit_value_usd_per_day": 528.12,
    "total_revenue_usd_per_day": 23666.04,
    "feed_cost_usd_per_day": 5474.16,
    "opex_usd_per_day": 757.58,
    "net_cash_flow_usd_per_day": 17434.30,
    "annual_net_cash_flow_usd": 5753319.0,
    "roi_pct": 115.07,
    "payback_years": 0.8691,
    "currency": "USD"
  },
  "warnings": []
}
```

Notes:

- The example numbers use a hypothetical prediction (`syngas_yield = 2.4102`), so they
  are illustrative only. The golden test uses the exact values in §2.8.
- `model_versions` is a TEA-only provenance block. `/predict` keeps its existing
  `model_version` field unchanged.
- `payback_years` is `null` when annual cash flow is not positive.
- `warnings` is always present (possibly empty).

### 3.3 Pydantic models (implementation phase)

- `TeaAssumptions` — `extra="forbid"`, `allow_inf_nan=False` on all floats, bounds per
  §2.2, defaults for engineering assumptions.
- `TeaRequest` — `extra="forbid"`; `conditions: PredictRequest`; `assumptions:
  TeaAssumptions`.
- `TeaFinancials` — response model mirroring `TeaResult` plus `currency: "USD"`.
- `TeaResponse` — `predictions`, `model_versions`, `financials`, `warnings`.

The API layer converts Pydantic models to `TeaInputs`, calls `calculate_tea`, and maps
domain exceptions to HTTP responses. It must not re-implement financial formulas.

### 3.4 Error semantics

| Status | Condition | Body |
|---|---|---|
| 200 | Valid request; models loaded; finite prediction | Predictions + financials + warnings |
| 422 | Pydantic/bounds/enum failure in conditions or assumptions; `TeaInputError` | FastAPI validation detail (consistent with `/predict`) |
| 503 | Either model missing, unreadable, or contract mismatch | `{"detail": "Model unavailable..."}` |
| 500 | Non-finite prediction or `TeaCalculationError` | Generic internal-error detail; no stack trace |

No silent fallback, no default model, no partial response. If either target model is
unavailable, the whole TEA request returns `503`.

### 3.5 Lifecycle and latency

- No new model loading. TEA reuses `app.state.models` populated by `create_app`.
- The prediction step is the existing warm inference path; TEA arithmetic is O(1).
- Target: TEA endpoint p95 < 50 ms warm, excluding cold start, measured in the same
  style as Sprint 2. The report records raw numbers at Phase 5.
- No caching or persistence in Sprint 3.

### 3.6 Option A (if the CTO prefers extending `/predict`)

- Add optional `assumptions: TeaAssumptions | None = None` to `PredictRequest`.
- Add optional `financials: TeaFinancials | None = None` and `warnings: list[str] =
  []` to `PredictResponse`.
- The route calculates TEA only when `assumptions` is present.
- Existing requests without `assumptions` must be byte-for-byte behaviour-compatible
  with Sprint 2. A regression test asserts the response shape is unchanged when
  assumptions are omitted.
- The same `calculate_tea` engine, error mapping, and golden tests apply.

---

## 4. File and Module Layout

New files (implementation phase):

```text
backend/src/odrm/domain/tea.py              # pure engine, types, constants, errors
backend/src/odrm/domain/tea_defaults.py     # engineering defaults + provenance (small)
backend/src/odrm/services/prediction.py     # shared inference helper (extracted)
backend/tests/unit/test_tea_engine.py       # golden values, invariants, errors
backend/tests/unit/test_tea_schemas.py      # Pydantic validation
backend/tests/unit/test_tea_api.py          # 200/422/503/500, warnings, regression
backend/tests/integration/test_tea_flow.py  # app + stub models + TEA end-to-end
```

Modified files (implementation phase only):

```text
backend/src/odrm/api/schemas.py             # add TEA request/response models
backend/src/odrm/api/routes.py              # add /tea route; use shared predictor
README.md                                   # TEA usage + assumptions + caveat
```

Untouched:

```text
data/schemas/odrm_v1.json
data/odrm_dataset.parquet
backend/src/odrm/data/**
backend/src/odrm/ml/**
models/**
```

This phase (plan-first) creates only `docs/SPRINT_3_PLAN.md`.

---

## 5. TDD Strategy and Test Matrix

### 5.1 TDD rules

1. Write the test(s) first for the step.
2. Run them and record the expected failure (missing module, missing symbol, assertion
   mismatch). Do not commit a failing suite.
3. Implement the minimum code to pass.
4. Run the focused tests, then the full suite.
5. Run `ruff` and `mypy` before committing.
6. Commit only after the step is green and atomic.

No network access. Reuse `backend/tests/conftest.py`; the session fixture blocks
outbound sockets. No real model artifacts are required for unit/API tests; use stub
models injected into `app.state.models`.

### 5.2 Test files and cases

#### `backend/tests/unit/test_tea_engine.py`

Golden and invariant tests:

- `test_golden_scenario_matches_hand_calculation` — asserts every field in §2.8 with
  `pytest.approx`.
- `test_syngas_volume_is_per_mol_ch4_fed` — `Y=2.5`, feed 100, 24 h → 6,000 kmol/day;
  a regression that multiplies by conversion would fail.
- `test_syngas_revenue_equals_volume_times_price`.
- `test_feed_cost_uses_mmbtu_conversion` — asserts `100 × 24 × 3 × 0.7603`.
- `test_carbon_credit_uses_co2_consumption` — asserts the 21.1248 t/day and 528.12 USD.
- `test_opex_prorates_annual_percentage` — 5 % of 5M over 330 days.
- `test_net_cash_flow_identity` — revenue + credit − feed − OPEX.
- `test_annual_cash_flow_identity` — daily × operating days.
- `test_roi_identity` — annual cash flow / CAPEX × 100.
- `test_payback_identity` — CAPEX / annual cash flow.
- `test_negative_cash_flow_returns_null_payback_and_warning`.
- `test_zero_yield_is_valid_and_has_zero_revenue` — no division by zero.
- `test_zero_carbon_price_yields_zero_credit`.
- `test_zero_utilization_yields_zero_credit_and_warning`.
- `test_out_of_envelope_yield_is_not_clamped_and_warns` — `Y=8.5` produces 8.5-based
  volume plus `syngas_yield_out_of_envelope`.
- `test_invalid_inputs_raise` — negative/zero feed, negative prices, `capex=0`,
  `hours=0`, `hours>24`, `days=0`, `days>365`, fraction `<0`/`>1`, NaN/Inf.
- `test_outputs_are_finite`.
- `test_determinism` — same inputs produce identical results.

#### `backend/tests/unit/test_tea_schemas.py`

- `extra="forbid"` rejects unknown fields at both `conditions` and `assumptions`.
- Missing required assumptions produce 422.
- Out-of-range values produce 422: capex 0, negative price, hours 25, days 366,
  fraction 1.1, feed 0.
- `NaN`/`Inf` are rejected.
- `conditions` reuses `PredictRequest` bounds (e.g., `temperature_c=1200` → 422).
- `payback_years=None` serialises as `null`.
- Engineering defaults apply when omitted; market prices do not have defaults.

#### `backend/tests/unit/test_tea_api.py`

- Valid request with stub models returns 200, both predictions, both model versions,
  financials, and an empty warnings list.
- Invalid conditions (temperature 1200) → 422.
- Invalid assumptions (capex 0, negative price) → 422.
- Extra field at top level or inside assumptions → 422.
- Empty `app.state.models` → 503 `Model unavailable`.
- Stub model returning `NaN` → 500, no partial financials.
- `warnings` present for zero carbon utilization and negative cash flow.
- `/api/v1/predict` still returns the Sprint 2 shape (regression).
- No outbound socket is opened (harness enforces this).

#### `backend/tests/integration/test_tea_flow.py`

- Build the app with `create_app` and inject two stub models.
- Post a full TEA request; assert the response matches the golden engine result.
- Assert `model_versions` provenance.
- Assert `payback_years` is null for a deliberately unprofitable scenario.
- Assert no network and no filesystem writes outside `tmp_path`.

#### Regression suite

- `backend/tests/unit/test_ml_features.py`
- `backend/tests/unit/test_predict_api.py`
- `backend/tests/unit/test_ml_dataset.py`
- `backend/tests/unit/test_ml_registry.py`
- `backend/tests/unit/test_ml_gates.py`
- `backend/tests/unit/test_ml_train.py`
- `backend/tests/unit/test_schema_*.py`
- `backend/tests/integration/test_dataset_artifacts.py`
- Any `ml`-marked tests that are part of the default suite.

### 5.3 Coverage targets

- `backend/src/odrm/domain/tea.py`: ≥ 90 % line and branch coverage.
- TEA API paths: ≥ 90 % line coverage.
- No coverage regression for `odrm/ml/` or `odrm/api/`.

### 5.4 Quality gates

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
.\.venv\Scripts\python.exe -m ruff check backend scripts
.\.venv\Scripts\python.exe -m ruff format --check backend scripts
.\.venv\Scripts\python.exe -m mypy backend/src scripts
```

No `DeprecationWarning` from `odrm.*`; no unhandled warnings; no `.joblib` changes.

---

## 6. Implementation Sequence and Commits

Only after `AUTHORIZED: Sprint 3 implementation phase`. Each step is test-first. The
plan itself is committed as the baseline after approval, before Step 1.

| Step | Work | TDD evidence | Proposed commit |
|---|---|---|---|
| 0 | Commit this plan as the Sprint 3 baseline | Plan reviewed and approved | `docs: add Sprint 3 TEA plan` |
| 1 | Domain types, constants, validation, formulas + golden/invariant tests | New engine tests fail first (`ModuleNotFoundError`/assertions), then pass | `test(tea): lock financial contract` |
| 2 | Engineering defaults and provenance constants + tests | Default tests fail first; no market-price defaults | `feat(tea): add engineering assumption defaults` |
| 3 | TEA Pydantic request/response schemas + validation tests | Schema tests fail first; 422 cases pass | `feat(api): add TEA schemas` |
| 4 | Extract shared inference helper; `/predict` regression tests | Existing `/predict` tests stay green; helper tests pass | `feat(api): share surrogate inference` |
| 5 | Add `POST /api/v1/tea`; wire engine, errors, warnings + API tests | 200/422/503/500 tests fail first, then pass | `feat(api): add TEA endpoint` |
| 6 | Golden end-to-end integration test with stub models | End-to-end test fails without wiring, then passes | `test(tea): add golden end-to-end scenario` |
| 7 | README TEA usage, assumptions, caveat, sample request | Docs-only; no behaviour change | `docs: document TEA API and assumptions` |
| 8 | Final lint/type/test cleanup; no behaviour changes | Full gate clean | `chore: finalize Sprint 3 quality gates` |

Rules:

- Step 1 may include tests plus the minimal implementation needed to make the commit
  green, matching the Sprint 2 `test(ml)` commit pattern.
- A step that reveals a plan ambiguity stops the work and returns to the plan/CTO.
- No step may modify `data/schemas/odrm_v1.json`, the dataset, or the Sprint 2 model
  artifacts.
- No step may add network calls.
- The Phase 5 report is **not** part of this sequence and is not created until a
  separate authorization.

---

## 7. Acceptance and Audit Evidence

Accepted only with raw terminal evidence, not a summary.

### 7.1 Full gate

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
.\.venv\Scripts\python.exe -m ruff check backend scripts
.\.venv\Scripts\python.exe -m ruff format --check backend scripts
.\.venv\Scripts\python.exe -m mypy backend/src scripts
```

### 7.2 TEA-specific evidence

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_tea_engine.py -q
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_tea_schemas.py -q
.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_tea_api.py -q
.\.venv\Scripts\python.exe -m pytest backend/tests/integration/test_tea_flow.py -q
```

The step report must include:

- The golden scenario's raw output (all fields).
- The negative-cash-flow case showing `payback_years = null` and the warning.
- The out-of-envelope yield case showing no clamping and the warning.
- 422/503/500 evidence.
- `pytest` total counts.
- `ruff` and `mypy` raw output.
- Coverage for `odrm/domain/tea.py`.
- `git status --short` showing no `.joblib`, no schema, no dataset changes.
- Confirmation that `data/schemas/odrm_v1.json` is byte-identical.
- Confirmation that no network access occurred (the conftest guard would raise).

### 7.3 Manual API check

Start the API, then:

```powershell
curl -X POST http://localhost:8000/api/v1/tea `
     -H "Content-Type: application/json" `
     -d '{"conditions":{"temperature_c":800.0,"pressure_bar":10.0,"ch4_o2_ratio":2.0,"co2_ch4_ratio":0.5,"h2o_ch4_ratio":0.2,"ghsv_per_h":5000.0,"catalyst":"Ni/Al2O3"},"assumptions":{"ch4_feed_kmol_per_h":100.0,"natural_gas_price_usd_per_mmbtu":3.0,"syngas_price_usd_per_kmol":4.0,"carbon_credit_price_usd_per_tonne_co2e":25.0,"co2_utilization_fraction":0.4,"capex_usd":5000000.0}}'
```

Expected: 200 with predictions, financials, and warnings. A request with `capex_usd:
0` returns 422. Renaming a model directory and restarting returns 503.

---

## 8. Risks and Mitigations

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | TEA numbers are mistaken for investment-grade advice | High | High | Label every response/doc as a screening estimate; no bankability claim; list exclusions (tax, financing, DCF) |
| R2 | Market prices are stale or fabricated | High | High | Require gas/syngas/carbon prices in the request; no network; no positive defaults; document price sources for the UI |
| R3 | Syngas yield basis is misinterpreted as per-mol-converted | Medium | High | Explicit unit definition in §1.2; regression test with per-mol-fed expected volume |
| R4 | Feed flow is not derivable from GHSV | High | High | Add explicit `ch4_feed_kmol_per_h`; document why reactor volume is required |
| R5 | Carbon credit overclaim / double counting | High | High | Conservative utilization basis; default fraction `0.0`; warning when omitted; no ESG eligibility claim; OQ-5 |
| R6 | Negative cash flow causes division by zero or `Inf` | Medium | High | `payback_years = None` + warning; tests |
| R7 | Unit conversion errors (MMBtu, Nm³, molar mass) | Medium | High | Named constants, provenance table, golden test |
| R8 | Float precision/rounding inconsistencies | Medium | Medium | Full precision in domain; `pytest.approx`; presentation-only rounding |
| R9 | `/predict` regresses during shared-inference extraction | Medium | High | Regression tests; extract without changing response shape; atomic commit |
| R10 | Out-of-envelope model output silently clamped | Medium | High | No clamping; explicit warning; non-finite → 500 |
| R11 | TEA endpoint becomes a de facto `co2_conversion` model | Medium | Medium | Explicit assumption input, not a hidden surrogate; OQ-12 |
| R12 | Scope creep into frontend/agent/report | Medium | Medium | Out-of-scope list; Phase 5 gate; stop and ask |
| R13 | Roadmap numbering conflicts confuse reviewers | High | Low | §0.4 reconciliation note; separate docs change after approval |
| R14 | OPEX percentage hides variable costs | Medium | Medium | Document the simplification; allow caller to fold costs into CAPEX/OPEX; future variable-OPEX model |
| R15 | API contract drift between `/predict` and `/tea` | Medium | Medium | Compose `PredictRequest`; shared inference helper; no duplicate feature building |

---

## 9. Assumptions

- Sprint 2 is accepted; `/api/v1/predict` and both models are stable.
- `syngas_yield_mol_per_mol_ch4` is per mol CH4 **fed**.
- Steady-state operation; no transients, recycle loops, or startup/shutdown economics.
- All produced syngas is saleable at the caller's blended price; no purification,
  compression, or downstream losses are modeled.
- Prices are constant over the year; no escalation, inflation, or FX.
- CAPEX is the caller's total installed cost; OPEX is an annual percentage of CAPEX.
- ROI and payback are simple, pre-tax, undiscounted metrics. No NPV/IRR.
- Carbon credit value is based on CO2 utilization, not avoided flaring; no additionality
  or verification claim.
- The model's applicability envelope is respected by the caller; out-of-envelope values
  are flagged, not silently corrected.
- The system is offline; the caller is responsible for supplying current market prices.
- Engineering defaults are screening placeholders, not market data.
- The acceptance machine can run the full suite in the existing venv.
- No real plant, experimental, HYSYS, or COMSOL data is available or required.

---

## 10. Open Questions (CTO Decisions)

| ID | Question | Recommendation | Impact if unresolved |
|---|---|---|---|
| OQ-1 | Confirm TEA is Sprint 3 and the Agentic Orchestrator is deferred, despite the roadmap numbering conflict. | Yes; reorder and reconcile `MASTER_ROADMAP.md`/`ARCHITECTURE.md` in a separate docs change. | Implementation scope and sprint numbering remain contradictory. |
| OQ-2 | New `POST /api/v1/tea` or extend `/api/v1/predict` with an optional `financials` block? | New endpoint; keep the accepted Sprint 2 contract stable. | API shape and regression surface. |
| OQ-3 | How is the production basis supplied? `ch4_feed_kmol_per_h` vs reactor volume + GHSV. | Require `ch4_feed_kmol_per_h`; GHSV alone is insufficient without reactor volume and gas density. | Cannot compute absolute daily revenue reliably. |
| OQ-4 | Syngas pricing: blended USD/kmol vs separate H2/CO pricing. | Blended USD/kmol for v1; H2/CO split requires a new model or assumption. | Revenue accuracy and future model scope. |
| OQ-5 | Carbon-credit basis: CO2 utilization, avoided flaring, or user-supplied volume? | CO2 utilization with explicit `co2_utilization_fraction`, default `0.0` + warning. | Environmental claims and credit value. |
| OQ-6 | Where do gas/syngas/carbon price defaults come from? | No backend defaults for market prices; require them. Optional documented sample request only. | Risk of stale/fabricated prices; UI convenience. |
| OQ-7 | OPEX model: `% of CAPEX/year`, fixed USD/day, or detailed cost stack. | `% of CAPEX/year` for v1; document the simplification; defer variable OPEX. | Accuracy of net cash flow and ROI. |
| OQ-8 | ROI/payback definitions: simple pre-tax vs discounted/NPV/IRR. | Simple pre-tax, undiscounted; defer NPV/IRR. | Comparability with investor models. |
| OQ-9 | Default operating days per year: 330, 350, or 365? | 330 (conservative, ~90 % availability), caller-overridable. | Annualized cash flow and payback. |
| OQ-10 | Out-of-envelope `syngas_yield > 8`: warn and compute, or fail? | Warn and compute unclamped; fail only on non-finite/negative. | Consistency with Sprint 2's no-clamp decision. |
| OQ-11 | Should ROI include carbon-credit revenue by default? | Yes, but report the credit value separately; caller can set carbon price to 0. | ROI interpretation and overclaim risk. |
| OQ-12 | Does Sprint 3 need a `co2_conversion` surrogate? | No; use an explicit assumption. Adding a model expands training/gates/artifacts. | Carbon credit accuracy vs scope. |
| OQ-13 | Currency and geography: USD-only v1? | USD-only; no FX. | Global South localization later. |
| OQ-14 | Should the response echo all assumptions for audit? | Include the key assumption basis in documentation; full evidence-chain hashing is Sprint 7. | Auditability and response size. |

---

## 11. Approval Gate

This plan is the only Sprint 3 artifact created before authorization.

- No implementation code, tests, schema/route changes, model changes, `.gitignore`
  changes, or commits are made until the CTO replies with the exact phrase:

  `AUTHORIZED: Sprint 3 implementation phase`

- If the CTO requests changes, revise this plan first and stop again.
- If an open question changes the financial contract, update the plan and obtain a new
  approval before coding.
- On approval, implementation proceeds in the TDD order in §6.
- The Phase 5 report (`docs/SPRINT_3_REPORT.md`) is explicitly **not** authorized by
  this plan and must wait for the CTO audit and a separate instruction.
