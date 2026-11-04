# Sprint 3 — TEA Engine & Financial Output: Review Note

| | |
|---|---|
| Status | **Complete** |
| Date | 2026-11-04 |
| Scope | Deterministic TEA engine, `/api/v1/tea` endpoint, shared inference service |

## 1. Objectives vs. outcome
| Plan Step | Outcome |
|---|---|
| 1. Domain types & formulas | Done — `e72eee5` |
| 2. Engineering defaults | Done — `87db8b1` |
| 3. TEA Pydantic schemas | Done — `0bd7ee1` |
| 4. Shared inference helper | Done — `8923739` |
| 5. TEA API endpoint | Done — `1accf6a` |
| 6. Golden E2E integration | Done — `da602a8` |
| 7. README documentation | Done — `a6b877e` |

## 2. Model Evidence (The Gates)
*   `pytest backend/tests -q` → **248 passed**
*   `ruff check` and `ruff format` → **All checks passed**
*   `mypy backend/src scripts` → **Success: no issues found in 24 source files**
*   `tea.py` coverage → **100%** (104 statements, 20 branches)

## 3. API Evidence (Live Check)
**Scenario A (Valid but Unprofitable):** 
*   Returned HTTP 200.
*   `roi_pct`: -8.41%
*   `payback_years`: null
*   `warnings`: ["negative_annual_cash_flow"]
*   *(Proves the engine accurately models economic failure without crashing).*

**Scenario B (Invalid CAPEX):**
*   Returned HTTP 422 (Validation Error).
*   `capex_usd` must be greater than 0.

## 4. Architecture Integrity
*   `data/schemas/odrm_v1.json` SHA-256 is byte-identical to HEAD.
*   `/api/v1/predict` response shape remains completely unchanged (regression tested).
*   No live network calls, no external API dependencies, no model retraining.

## 5. Known limitations (TEA Engine)
*   This is a screening tool, not investment-grade. Excludes taxes, financing, and variable OPEX.
*   Market prices must be supplied by the caller (no backend defaults).
*   Carbon credits are based on CO2 utilization, defaulting to 0% (conservative).