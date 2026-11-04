# Sprint 4 — Market Data Service & UI Dashboard: Review Note

| | |
|---|---|
| Status | **Complete** |
| Date | 2026-11-04 |
| Scope | Market Data API, React/Next.js Screening Dashboard, TanStack Query |

## 1. Objectives vs. outcome
| Plan Step | Outcome |
|---|---|
| 1. Market Data Service & Cache | Done |
| 2. Expose `/api/v1/market-prices` | Done |
| 3. Market-to-TEA Integration Test | Done |
| 4. Frontend Test Harness & API Clients | Done |
| 5. Market Price Panel & Query Hook | Done |
| 6. Screening Forms & Validation | Done |
| 7. Results, Warnings, & Provenance | Done |
| 8. Main Dashboard Composition | Done |

## 2. Backend Evidence
*   `pytest backend/tests -q` → **277 passed**
*   `ruff check` and `mypy` → **Clean**
*   New Endpoint: `GET /api/v1/market-prices` (Mocked with 24h TTL cache).
*   `/api/v1/predict` and `/api/v1/tea` contracts remain unchanged.

## 3. Frontend Evidence
*   `npm run test` → **14 passed** (Vitest + React Testing Library)
*   `npm run lint` → **Clean**
*   `npm run typecheck` → **Clean**
*   `npm run build` → **Compiled successfully (Next.js 16.4.3 Turbopack)**

## 4. Architecture & Deviations
*   **Missing Outputs Deferred:** H2/CO ratio, carbon-risk scoring, and confidence scores are explicitly NOT shown in the UI because the current ML models do not predict them. The UI honestly displays only CH4 conversion and Syngas yield.
*   **Mock Market Data:** The market endpoint uses a mock provider (`is_mock=true`). The UI correctly displays a "MOCK DATA" warning badge.
*   **TEA Integration:** The dashboard successfully handles `payback_years: null` by displaying "Not available" rather than a fake number.

## 5. Known limitations
*   Frontend uses manual `fetch` for API calls wrapped in TanStack Query.
*   No Playwright E2E tests yet (deferred to a later sprint).