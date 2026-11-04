# Sprint 2 — Surrogate Training & Prediction API: Review Note

| | |
|---|---|
| Status | **Complete** |
| Date | 2026-11-04 |
| Scope | XGBoost surrogate models, model registry, FastAPI `/predict` endpoint |

## 1. Objectives vs. outcome
| Plan Step | Outcome |
|---|---|
| 1. Feature contract & leakage guard | Done — `c9de8c9` |
| 2. Dataset preparation & split | Done — `4ef9e69` |
| 3. Model registry with metadata | Done — `dad6da3` |
| 4. Model acceptance gates | Done — `67fc2d2` |
| 5. XGBoost training pipeline | Done — `08a3be8` |
| 6. Train ODRM surrogate v1 | Done — `8fef374` |
| 7. Add predict endpoint | Done — `39e3d31` |
| 8. Serve versioned surrogate models | Done — `0ddb527` |

## 2. Model Evidence (The Gates)
The models were trained on the 10,000-row synthetic dataset (Seed 7) and strictly passed the CTO-approved gates.

| Target | R² Gate | Test R² | RMSE Gate | Test RMSE |
|---|---|---|---|---|
| `ch4_conversion` | > 0.95 | **0.9887** | ≤ 0.03 | **0.0285** |
| `syngas_yield_mol_per_mol_ch4` | > 0.95 | **0.9888** | ≤ 0.15 | **0.1000** |

*Artifacts saved to `models/odrm/<target>/v1-<timestamp>/` with `.joblib` files ignored by Git and `metadata.json` committed.*

## 3. API Evidence
*   **Endpoint:** `POST /api/v1/predict`
*   **Latency:** Loads models into memory at startup (`app.state.models`), ensuring sub-50ms inference time.
*   **Validation:** Pydantic rejects any physics bounds violations (e.g., Temp > 1000°C) with a 422 error.
*   **Resilience:** If models are missing on boot, the API returns a 503 error, preventing silent failures.

## 4. Gate Evidence (CI)
*   `pytest backend/tests -q` → **132 passed**
*   `ruff check` and `ruff format` → **All checks passed**
*   `mypy backend/src scripts` → **Success: no issues found in 21 source files**

## 5. Known issues & limitations
*   The model is trained on reduced-order synthetic data, not real HYSYS/COMSOL output.
*   The `high` carbon risk class is only 3.6% of the dataset, so metrics for that specific stratum may vary.
*   No batch prediction endpoint (deferred to later sprint).