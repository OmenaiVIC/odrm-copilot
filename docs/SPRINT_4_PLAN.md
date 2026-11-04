# Sprint 4 Plan - Market Data Service & UI Dashboard

| | |
|---|---|
| Status | **Draft - awaiting CTO approval** |
| Date | 2026-11-04 |
| Scope | Market Data Service, `/api/v1/market-prices`, Next.js screening dashboard |
| Dependency | Sprint 3 complete and accepted |
| Approval phrase | `AUTHORIZED: Sprint 4 implementation phase` |

> **Planning gate:** this document is the only Sprint 4 artifact allowed before approval.
> No implementation code, tests, routes, schemas, dependency installs, or commits are to be
> created until the CTO approves this plan with the exact phrase above.

---

## 1. Executive summary

Sprint 4 delivers two connected capabilities:

1. **Market Data Service** - a server-side service and read-only endpoint that returns a
   cached, clearly labelled mock market-price snapshot in the exact units required by the
   existing TEA engine.
2. **Screening dashboard** - a Next.js client dashboard that collects reactor conditions and
   financial assumptions, calls the existing `/api/v1/tea` endpoint, and presents predictions,
   financial results, warnings, and model provenance.

The dashboard will **not** invent H2/CO ratio, carbon-risk, or confidence-score outputs. Those
items appear in the master roadmap but are not available from the current models or API. They
are either deferred or explicitly marked unavailable in Sprint 4. See section 3.

The market endpoint and the TEA endpoint remain independent. The dashboard composes them; the
TEA engine never fetches market data.

---

## 2. Sprint scope

### 2.1 In scope

- `MarketDataService` with a provider abstraction, offline mock provider, TTL cache, and
  deterministic clock injection for tests.
- `GET /api/v1/market-prices` returning a typed, TEA-ready mock quote.
- TTL configuration through `ODRM_MARKET_DATA_TTL_SECONDS`.
- Clear mock-data labelling in both the API response and the UI.
- Next.js dashboard with:
  - reactor-condition form;
  - financial-assumptions form;
  - market-price panel with editable overrides;
  - TEA submission through `/api/v1/tea`;
  - predictions, financial KPIs, detailed financial breakdown, warnings, and model provenance;
  - loading, empty, validation, network, 422, 500, and 503 states.
- Backend unit and API tests, frontend component/API-client tests, and one market-to-TEA
  integration test.
- README and environment documentation updates in the implementation phase.

### 2.2 Out of scope

- Training, retraining, replacing, or adding surrogate models.
- H2/CO ratio, carbon-risk prediction, confidence scores, or model intervals.
- A cryptographic/Merkle evidence chain or immutable audit trail.
- Live market-data integrations, API keys, scraping, or outbound network calls.
- Persistence, database, user accounts, authentication, multi-tenancy, or rate limiting.
- Deployment, containerisation, CI changes, or production observability.
- Historical charts, parity plots, sensitivity sweeps, or other time-series visualisations.
- Native mobile application or internationalisation.

---

## 3. Roadmap reconciliation

The master roadmap and the frozen Sprint 3 API do not fully agree. Sprint 4 must be explicit
about the gap rather than silently claiming completion.

| Roadmap Sprint 4 item | Current capability | Sprint 4 treatment |
|---|---|---|
| Input form for feed composition and temperature | `/predict` and `/tea` accept conditions | Implemented for all current condition fields |
| Results panel with H2/CO ratio and carbon risk | Not returned by either endpoint; models predict CH4 conversion and syngas yield only | **Deferred.** Show the two available predictions plus TEA financials. Report the gap. |
| Market Data Service with caching | No service exists | Implemented with a mock provider and TTL cache |
| Evidence Chain Component with model version and confidence | `/tea` returns `model_versions`; no confidence score or hash chain | **Reduced.** Show model provenance only. Do not label it an evidence chain. |
| TanStack Query and Recharts | Neither is installed | Add TanStack Query for request state; **defer Recharts** because Sprint 4 has no series/curve data |
| Playwright E2E | Not installed | **Defer.** Use React Testing Library plus a manual smoke checklist |

### 3.1 Why the missing outputs are not stubbed

- H2/CO ratio would require separate H2 and CO yield predictions; those are sibling outcomes
  excluded from the current model target contract. Deriving them in the UI would be a new
  model/product decision, not a presentation change.
- Carbon risk has no agreed definition, target, threshold, or output contract.
- No confidence score or prediction interval exists in the model metadata. A fabricated
  percentage would be misleading in a screening tool.
- The full Merkle/immutable evidence chain belongs to a later sprint. Sprint 4 can show
  provenance without claiming cryptographic auditability.

If the CTO requires any missing item in Sprint 4, it is a scope change requiring model/API work
and a revised plan.

---

## 4. Current baseline

### 4.1 Backend

- FastAPI application factory in `backend/src/odrm/main.py`.
- Existing routes:
  - `POST /api/v1/predict` - `{predictions, model_version}`.
  - `POST /api/v1/tea` - `{predictions, model_versions, financials, warnings}`.
- Existing TEA response fields include syngas production, revenue, feed cost, OPEX, net cash
  flow, annual cash flow, ROI, and nullable payback.
- `TeaAssumptions` bounds are the source of truth for financial-input validation.
- Model loading already fails soft: missing models produce a 503 on prediction/TEA routes.
- CORS currently allows `http://localhost:3000` by default.
- `backend/tests/conftest.py` blocks all outbound network access for the test session.

### 4.2 Frontend

- Next.js `16.4.3`, React `19.3.0`, strict TypeScript, App Router.
- Tailwind CSS v4 through `@tailwindcss/turbopack`; no `tailwind.config.*`.
- Existing `src/lib/api.ts` provides `apiFetch<T>` and `ApiError`.
- The current page is still the create-next-app starter.
- No test runner, React Testing Library, TanStack Query, or Recharts is installed.
- `next.config.ts` enables `cacheComponents` and `partialPrefetching`.
- `frontend/AGENTS.md` requires reading the bundled Next.js 16 docs before implementation.

### 4.3 Verified Sprint 3 baseline

- Full backend suite: 248 passed.
- Ruff and mypy clean.
- TEA domain coverage: 100%.
- `/api/v1/predict` response shape unchanged.
- `/api/v1/tea` contract accepted and covered by unit, integration, and live checks.
- No live network calls in the backend test suite.

---

## 5. Architecture

### 5.1 Component and request flow

```text
Browser
  |
  |  Next.js dashboard (client component)
  |    - GET /api/v1/market-prices on mount
  |    - POST /api/v1/tea on submit
  v
FastAPI
  |
  +--> /api/v1/market-prices
  |      -> MarketDataService
  |           -> MarketPriceProvider (mock only in Sprint 4)
  |           -> in-memory TTL cache
  |
  +--> /api/v1/tea
         -> existing prediction service
         -> existing TEA engine
         -> no market-data dependency
```

### 5.2 Architectural rules

1. **Separation:** the market service does not import TEA, and TEA does not import or call the
   market service.
2. **Composition in the client:** the dashboard fetches prices, lets the user edit them, and
   submits them as TEA assumptions.
3. **Offline by default:** Sprint 4 uses only an in-process mock provider. No HTTP client,
   credentials, scraping, or network access is added.
4. **Server-side cache:** caching belongs to the service, not to the browser or Next.js.
5. **Explicit mock state:** every response and the UI identify mock data. A mock quote must
   never be presented as a live market price.
6. **Contract-first:** response fields use the same names and units as `TeaAssumptions` so the
   UI does not perform hidden financial conversions.
7. **Failure isolation:** market failure does not prevent TEA use; the user can enter prices
   manually.

### 5.3 Request lifecycle

1. Dashboard mounts and requests market prices.
2. On success, pristine price fields are populated; metadata is displayed.
3. User edits conditions and assumptions. Price edits are never overwritten by a late fetch.
4. Submit validates locally, builds a `TeaRequest`, and posts it.
5. Dashboard renders predictions, financials, warnings, and provenance.
6. On failure, the form remains intact and the error is shown without losing inputs.

---

## 6. Market Data Service design

### 6.1 Backend components

| Component | Location | Responsibility |
|---|---|---|
| `MarketPriceQuote` | `backend/src/odrm/services/market_data.py` | Immutable, validated quote value object |
| `MarketPriceProvider` | same | Protocol for a quote source |
| `MockMarketPriceProvider` | same | Offline fixed fixture with generated `as_of` |
| `MarketDataService` | same | TTL cache and provider orchestration |
| `MarketDataError` | same | Safe, domain-level market-data failure |
| `MarketPricesResponse` | `backend/src/odrm/api/schemas.py` | API response model |
| `market_prices` route | `backend/src/odrm/api/routes.py` | HTTP adapter, error mapping |
| `market_data_ttl_seconds` | `backend/src/odrm/core/config.py` | Configurable cache lifetime |
| app wiring | `backend/src/odrm/main.py` | Build service and store on `app.state` |

The service layer must not import `odrm.api.schemas`; API models depend on the service/domain,
not the reverse.

### 6.2 Service contract

- `MarketPriceQuote` is immutable and carries:
  - natural-gas price in `USD/MMBtu`;
  - syngas price in `USD/kmol`;
  - carbon-credit price in `USD/tonne CO2e`;
  - currency (`USD` only for Sprint 4);
  - source label;
  - mock flag;
  - `as_of` timestamp in UTC.
- `MarketPriceProvider.fetch()` returns a `MarketPriceQuote` or raises `MarketDataError`.
- `MockMarketPriceProvider` returns a fixed fixture and sets `as_of` to the current UTC time.
- `MarketDataService.get_prices()` returns the quote plus `cached: bool`.
- Quote validation rejects:
  - non-finite values (`NaN`, infinity);
  - negative values;
  - values above the matching TEA-assumption safety caps;
  - currencies other than `USD`.
- Invalid provider output is never cached.

### 6.3 Cache behavior

- The cache stores one quote and the monotonic time at which it was fetched.
- `get_prices()`:
  1. acquires the service lock;
  2. compares elapsed monotonic time with the TTL;
  3. returns the cached quote with `cached=true` on a hit;
  4. otherwise calls the provider, validates the quote, stores it, and returns `cached=false`.
- Holding the lock across the provider call coalesces concurrent cold-start requests into one
  fetch. This is acceptable for the in-process mock. A future live HTTP provider must revisit
  single-flight/latency behavior.
- `TTL = 0` disables caching: every call fetches and returns `cached=false`.
- A provider error does not replace or extend a previous cache entry. The route returns 503.
- Failed fetches are not cached; the next request retries.
- `as_of` is preserved on cache hits.
- TTL uses `time.monotonic`; `as_of` uses UTC wall time. Tests inject both clocks.
- No stale-while-revalidate and no silent stale fallback in Sprint 4.

### 6.4 API contract

**Endpoint:** `GET /api/v1/market-prices`

- Authentication: none in Sprint 4.
- Request body/query parameters: none.
- Success: HTTP 200, `application/json`.
- Failure: HTTP 503 with `{"detail":"Market data unavailable."}` for provider or quote
  validation failures. Internal exception details are not exposed.
- The route is read-only and does not mutate models or TEA state.
- The response uses a dedicated market router so the existing `/predict` and `/tea` OpenAPI tag
  remains unchanged.

### 6.5 Response schema

| Field | Type | Unit | Notes |
|---|---|---|---|
| `natural_gas_price_usd_per_mmbtu` | number | USD/MMBtu | Same name and unit as TEA assumptions |
| `syngas_price_usd_per_kmol` | number | USD/kmol | TEA-ready; see unit decision below |
| `carbon_credit_price_usd_per_tonne_co2e` | number | USD/tonne CO2e | Same name and unit as TEA assumptions |
| `currency` | string | - | Always `USD` in Sprint 4 |
| `source` | string | - | Mock fixture identifier |
| `is_mock` | boolean | - | `true` for the Sprint 4 provider |
| `as_of` | string | ISO 8601 UTC | Quote timestamp; unchanged on cache hits |
| `cached` | boolean | - | `false` on a fresh fetch, `true` on a cache hit |
| `cache_ttl_seconds` | integer | seconds | Configured TTL, including on cache hits |

Example first response:

```json
{
  "natural_gas_price_usd_per_mmbtu": 3.25,
  "syngas_price_usd_per_kmol": 4.1,
  "carbon_credit_price_usd_per_tonne_co2e": 28.5,
  "currency": "USD",
  "source": "mock-fixture-v1",
  "is_mock": true,
  "as_of": "2026-11-04T12:00:00Z",
  "cached": false,
  "cache_ttl_seconds": 86400
}
```

The second request within the TTL returns the same prices and `as_of`, with `cached: true`.

### 6.6 Mock fixture values

| Price | Value | Notes |
|---|---:|---|
| Natural gas | `3.25 USD/MMBtu` | Placeholder, not a forecast |
| Syngas | `4.10 USD/kmol` | TEA-ready placeholder |
| Carbon credit | `28.50 USD/tonne CO2e` | Placeholder, not a forecast |

These values are deliberately close to the Sprint 3 golden TEA scenario so the dashboard
demonstrates a plausible result. They are not market data and must remain labelled as mock.

### 6.7 Unit decision: syngas price

The market-data strategy describes methanol/syngas spot prices in `USD/tonne`, while the TEA
engine requires `USD/kmol`. Converting between them requires a syngas composition and molar
mass, which the current TEA contract does not carry.

Sprint 4 therefore returns **TEA-ready `USD/kmol`** and documents that the mock fixture uses a
placeholder. A future live provider must either:

- obtain a source already quoted in `USD/kmol`; or
- expose both the raw `USD/tonne` quote and the conversion assumption used.

The API must not apply an undocumented fixed molecular weight. This is an open question for
production data.

### 6.8 Configuration and wiring

- Add `market_data_ttl_seconds: int = 86400` to `Settings`.
- Validate the setting as `0..604800` seconds (zero disables caching).
- Add `ODRM_MARKET_DATA_TTL_SECONDS=86400` to `.env.example`.
- In `create_app`:
  - construct `MockMarketPriceProvider`;
  - construct `MarketDataService` with the configured TTL;
  - assign it to `app.state.market_data`.
- No new third-party backend dependency is required.
- The route reads `request.app.state.market_data`.

### 6.9 Future live adapter (not Sprint 4)

A future provider can implement the same protocol around an HTTP client, with timeout, retry,
source attribution, and stale-cache policy. That work requires a separate decision on provider,
credentials, licensing, and failure semantics. It is not part of this sprint.

---

## 7. Frontend design

### 7.1 UX goals

- Make the screening workflow obvious: enter conditions, confirm prices, run, read result.
- Keep financial assumptions visible but not overwhelming; advanced assumptions collapse.
- Distinguish **predictions** from **financial calculations**.
- Make mock market data unmistakable.
- Never hide warnings or present a nullable payback as a number.
- Work on a laptop and a narrow mobile viewport.
- Keep the form usable when the market endpoint is down.

### 7.2 Page layout

```text
+--------------------------------------------------------------------------------+
| ODRM Copilot                                      [Screening estimate badge]   |
| Flare-gas valorization screening                                                |
+--------------------------------------------------------------------------------+
| LEFT (form)                                      | RIGHT (result)                |
|                                                  |                               |
| 1. Reactor conditions                            | 3. Screening result           |
|    temperature, pressure, ratios, GHSV,          |    prediction cards           |
|    catalyst, optional loading/dilution           |    financial KPI cards        |
|                                                  |    detailed financial table   |
| 2. Financial assumptions                         |    warnings                   |
|    feed rate, market prices, utilization,        |    model provenance           |
|    CAPEX, advanced OPEX/operating assumptions    |                               |
|                                                  |                               |
| [Run screening] [Reset]                          |                               |
+--------------------------------------------------------------------------------+
| Footer: screening-only disclaimer, API status                                  |
+--------------------------------------------------------------------------------+
```

- Desktop: two-column layout with a sticky result column.
- Mobile: one column; submit controls remain visible; result follows the form.
- Max width roughly 1280 px; generous spacing; no marketing hero.
- Cards use clear section numbering and units.

### 7.3 Component inventory

| Component | Responsibility |
|---|---|
| `app/providers.tsx` | Client-only TanStack Query provider |
| `app/page.tsx` | Server shell rendering the dashboard |
| `components/dashboard/dashboard.tsx` | Client owner of form state, queries, mutation |
| `components/dashboard/conditions-fields.tsx` | Reactor-condition fieldset |
| `components/dashboard/financial-fields.tsx` | Financial-assumption fieldset, including market overrides |
| `components/dashboard/market-price-panel.tsx` | Market quote metadata, refresh/reset controls |
| `components/dashboard/results-panel.tsx` | Predictions, KPIs, financial table, warnings |
| `components/dashboard/provenance-list.tsx` | Model-version provenance |
| `components/ui/field.tsx` | Label, unit hint, input, error association |
| `components/ui/section-card.tsx` | Consistent card/section shell |
| `components/ui/alert.tsx` | Success, warning, and error alerts |
| `hooks/use-market-prices.ts` | Query hook and market error state |
| `hooks/use-tea-calculation.ts` | TEA mutation hook |
| `lib/api.ts` | Typed `getMarketPrices` and `postTea` wrappers |
| `lib/types.ts` | Market and TEA request/response types |
| `lib/validation.ts` | Numeric parsing, client bounds, payload construction |
| `lib/format.ts` | Currency, percentage, number, date, and TTL formatting |
| `lib/constants.ts` | Defaults, catalyst options, labels, warning copy |

### 7.4 Reactor-condition fields

| Field | Default | UI bounds | Unit | Required |
|---|---:|---|---|---|
| `temperature_c` | 800 | 500-1000 | C | yes |
| `pressure_bar` | 10 | 1-30 | bar | yes |
| `ch4_o2_ratio` | 2.0 | 1.4-2.5 | mol/mol | yes |
| `co2_ch4_ratio` | 0.5 | 0-1.5 | mol/mol | yes |
| `h2o_ch4_ratio` | 0.2 | 0-1.5 | mol/mol | yes |
| `ghsv_per_h` | 5000 | 1000-100000 | 1/h | yes |
| `catalyst` | `Ni/Al2O3` | `Ni/Al2O3`, `Ni-MgO`, `Rh`, `Pt`, `none`, `other` | - | yes |
| `catalyst_loading_wt_pct` | 10.0 | 0-20 | wt% | no |
| `n2_dilution_mol_pct` | blank | 0-50 | mol% | no |

Optional blank values are sent as `null`, which the existing `PredictRequest` accepts. The
catalyst list mirrors `schema.ENUMS["catalyst"]`; the duplication is documented as a contract
risk.

### 7.5 Financial-assumption fields

| Field | Default/source | UI bounds | Unit | Required |
|---|---|---|---|---|
| `ch4_feed_kmol_per_h` | 100 | >0-1,000,000 | kmol/h | yes |
| `natural_gas_price_usd_per_mmbtu` | market | 0-1,000 | USD/MMBtu | yes |
| `syngas_price_usd_per_kmol` | market | 0-1,000,000 | USD/kmol | yes |
| `carbon_credit_price_usd_per_tonne_co2e` | market | 0-100,000 | USD/tonne CO2e | yes |
| `co2_utilization_fraction` | 0 | 0-1 | fraction | yes |
| `capex_usd` | 5,000,000 | >0-1e12 | USD | yes |
| `opex_pct_of_capex_per_year` | 5 | 0-100 | %/year | advanced |
| `operating_hours_per_day` | 24 | >0-24 | h/day | advanced |
| `operating_days_per_year` | 330 | >0-365 | days/year | advanced |

The UI shows `co2_utilization_fraction` as a fraction with a helper example (`0.40 = 40%`) to
avoid a hidden conversion.

### 7.6 Market-price panel behavior

- Loading: skeleton with `aria-busy`.
- Success:
  - display all three prices, source, `as_of`, `cached`, and TTL;
  - show a prominent **MOCK DATA** badge because `is_mock=true`;
  - explain that prices are editable and should be replaced with contract prices for a real
    screening.
- Error:
  - show an inline alert: "Market prices are unavailable. Enter your own prices.";
  - leave price fields editable and required;
  - allow TEA submission once the user supplies values;
  - provide a retry button.
- Field population:
  - populate only fields that are still pristine;
  - once the user edits a price, a later fetch or refresh never overwrites it;
  - a **Use market values** action resets the three price fields to the latest quote.
- Refresh:
  - re-runs the query;
  - does not overwrite edited price fields;
  - updates metadata and cached state.
- A zero price is allowed (TEA emits warnings), but a blank or invalid price blocks submit.

### 7.7 Submission and payload

- Use a native form with controlled string values; no form-library dependency.
- `noValidate` plus explicit client validation for consistent messages and testability.
- On submit:
  1. trim and parse all fields;
  2. reject blank required values, non-finite numbers, and values outside the mirrored bounds;
  3. build a `TeaRequest` containing only API fields;
  4. call `postTea`;
  5. retain all inputs on failure.
- Submit is disabled while the TEA mutation is pending.
- Server validation remains authoritative. A 422 response maps field locations back to the
  corresponding inputs and also shows a general summary.
- Do not silently clamp values to the nearest bound.

### 7.8 Results panel

Prediction cards:

- CH4 conversion: `predictions.ch4_conversion * 100`, two decimals, percent.
- Syngas yield: `predictions.syngas_yield_mol_per_mol_ch4`, three decimals,
  `mol/mol CH4`.

Financial KPI cards:

- annual net cash flow;
- ROI;
- payback (or "Not available" when `null`);
- daily net cash flow.

Detailed table:

| Result | Format/unit |
|---|---|
| Syngas production | kmol/day and Nm3/day |
| Syngas revenue | USD/day |
| CO2 consumed | tonnes/day |
| Carbon-credit value | USD/day |
| Total revenue | USD/day |
| Feed cost | USD/day |
| OPEX | USD/day |
| Net cash flow | USD/day |
| Annual net cash flow | USD/year |
| ROI | percent |
| Payback | years or "Not available" |
| Currency | USD |

Presentation rules:

- Negative annual cash flow and unavailable payback use a warning treatment, not an error.
- Money uses grouping and two decimals for daily values; annual values may use zero decimals.
- Large values are not abbreviated in the detailed table.
- Empty state before the first submit explains what will appear.
- Loading state disables submit, sets `aria-busy`, and announces progress.
- Success result is announced through a polite live region; focus may move to the result
  heading for keyboard/screen-reader users without a large scroll jump.
- Result content is derived only from the `/tea` response. No client-side financial
  calculations and no fabricated metrics.

### 7.9 Warnings and provenance

Warning codes from the TEA engine are mapped to human-readable copy while preserving the raw
code in a secondary line or tooltip:

| Code | Meaning |
|---|---|
| `carbon_credit_not_included` | CO2 utilization is zero, so carbon-credit revenue is not included |
| `negative_annual_cash_flow` | Annual cash flow is negative; payback is unavailable |
| `syngas_yield_out_of_envelope` | Predicted syngas yield is outside the screening envelope |
| `zero_syngas_price` | Syngas price is zero |
| `zero_carbon_price` | Carbon-credit price is zero |

Provenance:

- Render `model_versions` as a labelled "Model provenance" list.
- Use readable target labels, but show the exact version strings returned by the API.
- Do **not** show a confidence score, interval, hash, or "verified" badge.
- Do not call this component an evidence chain; the full audit chain is future work.

### 7.10 Client state and data fetching

**Decision proposed:** add `@tanstack/react-query` v5 for server-state handling, consistent with
ADR-003. Do not add Recharts because Sprint 4 has no time-series, parity, or sensitivity plot.

- `providers.tsx` creates one `QueryClient` per browser session with sensible defaults:
  - `retry: 1` for queries;
  - `retry: 0` for mutations;
  - no refetch on window focus for the screening workflow.
- `useMarketPrices` uses a stable query key and a five-minute client `staleTime`; the server
  owns the authoritative 24-hour cache.
- `useTeaCalculation` uses a mutation and exposes idle/pending/success/error states.
- Test utilities create a fresh `QueryClient` with retries disabled.

If the CTO prefers no runtime query dependency, the fallback is native `fetch` plus
`useState`/`useEffect`; the component contracts and tests remain the same. This is the only
frontend architecture choice that still needs confirmation.

### 7.11 Error mapping

| Condition | UI behavior |
|---|---|
| Client validation failure | Field-level messages; focus first invalid field |
| 422 from FastAPI | Map `detail[].loc` to condition/assumption fields; show summary |
| Custom 422 string detail | Show as a general form alert |
| 503 from TEA | "Prediction service unavailable. Check that models are loaded." |
| 500 from TEA | "Calculation failed. Adjust inputs and try again." |
| Market 503 | "Market prices unavailable. Enter prices manually." |
| Network failure | "Cannot reach the API. Check that the backend is running." |
| Unexpected response shape | Generic error alert; do not crash the page |

Raw stack traces and internal exception text are never shown.

### 7.12 Accessibility

- Every input has a persistent `<label>` and unit hint.
- Errors use `aria-invalid` and `aria-describedby`.
- Fieldsets/legends group reactor and financial inputs.
- Alerts use `role="alert"`; results use a polite live region.
- Submit pending state uses `aria-busy` and a visible label change.
- Focus remains visible and keyboard order follows the visual order.
- Meaning is not conveyed by colour alone; warning/error text is explicit.
- Financial table has a caption and proper header cells.
- Controls meet a minimum 44 px touch target where practical.
- Verify at 320 px, 768 px, and 1280 px widths.

### 7.13 Styling and Next.js specifics

- Extend the existing `globals.css` with light/dark CSS variables for surface, border, text,
  muted text, accent, success, warning, and danger.
- Keep Tailwind v4 utility classes; do not add `tailwind.config.*`.
- Remove the starter content and the `Arial` override so the existing Geist variables are used.
- Keep the dashboard as a client boundary below a server `page.tsx`; avoid build-time backend
  fetches under `cacheComponents`.
- Do not introduce dynamic server APIs or a proxy route in Sprint 4. The browser calls the
  FastAPI base URL directly, using the existing `NEXT_PUBLIC_API_BASE_URL` convention and CORS.
- Read the bundled Next.js 16 docs in `frontend/node_modules/next/dist/docs/` before editing
  routing, caching, or client-component code.

---

## 8. File and module plan

### 8.1 Backend

Create:

```text
backend/src/odrm/services/market_data.py
backend/tests/unit/test_market_data_service.py
backend/tests/unit/test_market_prices_api.py
backend/tests/integration/test_market_prices_flow.py
```

Modify:

```text
backend/src/odrm/api/schemas.py      # MarketPricesResponse
backend/src/odrm/api/routes.py       # market router and handler
backend/src/odrm/core/config.py      # market_data_ttl_seconds
backend/src/odrm/main.py             # service construction and router inclusion
backend/tests/unit/test_app_boot.py  # only if app-state assertion needs updating
.env.example                         # ODRM_MARKET_DATA_TTL_SECONDS
README.md                            # endpoint and dashboard usage
```

Do not modify:

```text
backend/src/odrm/domain/tea.py
backend/src/odrm/domain/tea_defaults.py
backend/src/odrm/ml/features.py
backend/src/odrm/services/prediction.py
data/schemas/odrm_v1.json
existing `/predict` and `/tea` response contracts
```

### 8.2 Frontend

Create:

```text
frontend/src/app/providers.tsx
frontend/src/components/dashboard/dashboard.tsx
frontend/src/components/dashboard/conditions-fields.tsx
frontend/src/components/dashboard/financial-fields.tsx
frontend/src/components/dashboard/market-price-panel.tsx
frontend/src/components/dashboard/results-panel.tsx
frontend/src/components/dashboard/provenance-list.tsx
frontend/src/components/ui/field.tsx
frontend/src/components/ui/section-card.tsx
frontend/src/components/ui/alert.tsx
frontend/src/hooks/use-market-prices.ts
frontend/src/hooks/use-tea-calculation.ts
frontend/src/lib/types.ts
frontend/src/lib/validation.ts
frontend/src/lib/format.ts
frontend/src/lib/constants.ts
frontend/src/test/setup.ts
frontend/src/test/test-utils.tsx
frontend/src/lib/api.test.ts
frontend/src/lib/validation.test.ts
frontend/src/components/dashboard/market-price-panel.test.tsx
frontend/src/components/dashboard/results-panel.test.tsx
frontend/src/components/dashboard/dashboard.test.tsx
frontend/vitest.config.ts
```

Modify:

```text
frontend/src/app/page.tsx       # render dashboard shell
frontend/src/app/layout.tsx     # metadata/provider wrapper
frontend/src/app/globals.css    # design tokens and base styles
frontend/src/lib/api.ts         # typed market/TEA calls
frontend/package.json           # scripts and dependencies
frontend/package-lock.json      # generated by install
```

No changes to `next.config.ts` are planned. No chart, component-library, or form-library
dependency is planned.

---

## 9. TDD and validation plan

### 9.1 TDD rules

- Write a failing test before each behavior.
- Keep service logic testable without FastAPI; keep route tests thin.
- Use injected clocks and providers; never `sleep` in tests.
- No outbound network in backend tests; the existing conftest guard must remain active.
- Frontend tests render client components directly, not the Next.js server page.
- Mock `fetch` at the API-client boundary; do not test implementation details of TanStack Query.
- Refactor only after the relevant tests are green.
- Run the smallest relevant test during development and the full gate before each commit.

### 9.2 Backend test matrix

`test_market_data_service.py`

- fresh fetch returns `cached=false` and provider called once;
- second call within TTL returns `cached=true`, same `as_of`, provider not called again;
- TTL expiry refetches and returns `cached=false` with a new `as_of`;
- `TTL=0` always fetches;
- provider failure is propagated as `MarketDataError` and not cached;
- invalid quote (negative, non-finite, above cap, wrong currency) is rejected and not cached;
- concurrent cold-start calls perform one provider fetch;
- mock quote exposes `source`, `is_mock`, and UTC `as_of`.

`test_market_prices_api.py`

- `GET /api/v1/market-prices` returns 200 with the exact field set and values;
- first call is `cached=false`; second is `cached=true`;
- `as_of` is parseable and UTC;
- configured TTL is echoed in `cache_ttl_seconds`;
- a failing provider returns 503 with the generic detail and no internal error text;
- a malformed provider quote returns 503;
- `app.state.market_data` exists after app creation;
- existing `/predict` and `/tea` tests remain green.

`test_market_prices_flow.py`

- fetch market prices, build TEA assumptions from them, submit `/api/v1/tea`, and assert 200
  with predictions, financials, warnings, and model versions;
- use stub models so the test is deterministic and model-file independent;
- confirm the market response values can be submitted unchanged to TEA.

### 9.3 Frontend test matrix

API client:

- `getMarketPrices` uses `GET`, the configured base URL, and `cache: "no-store"`;
- `postTea` uses `POST` with the exact JSON payload;
- non-2xx responses throw `ApiError` with status and detail;
- malformed 422 detail is handled without crashing.

Validation:

- required numeric fields reject blank, non-numeric, non-finite, and out-of-range values;
- optional blank fields become `null`;
- valid values build the exact TEA payload shape;
- market price fields are required;
- error messages are attached to the correct field keys.

Market panel:

- loading state is exposed;
- success fills pristine price fields and shows mock/source/timestamp/cache metadata;
- user-edited prices are not overwritten by a refresh;
- "Use market values" restores the latest quote;
- market failure leaves price fields editable and shows the manual-entry message.

Results panel:

- renders CH4 conversion as a percentage and syngas yield with units;
- renders financial KPIs and the detailed table from the API response;
- renders `null` payback as "Not available", not zero;
- renders all warning codes with human-readable copy;
- renders model versions and does not render confidence/H2/CO/carbon-risk claims;
- empty and loading states behave correctly.

Dashboard:

- renders the form, market panel, result placeholder, and disclaimer;
- client validation blocks submission and focuses the first invalid field;
- successful submission shows predictions, financials, warnings, and provenance;
- changed market prices are sent in the TEA assumptions;
- 422 maps errors to fields; 503/500/network errors show the correct alert and retain inputs;
- submit is disabled while pending;
- model provenance and result region are accessible.

### 9.4 Test tooling and dependencies

Backend: existing pytest, FastAPI `TestClient`, existing fixtures. No new runtime dependency.

Frontend dev dependencies:

- `vitest`
- `vite`
- `@vitejs/plugin-react`
- `jsdom`
- `@testing-library/react`
- `@testing-library/jest-dom`
- `@testing-library/user-event`
- `@testing-library/dom`

Frontend runtime dependency:

- `@tanstack/react-query` v5

Not added:

- Recharts
- React Hook Form or another form library
- MSW or a browser E2E framework
- Playwright (deferred unless the CTO requires a smoke test)

Scripts:

- `test`: `vitest run`
- `test:watch`: `vitest`

### 9.5 Quality gates

Backend:

```text
pytest backend/tests -q
ruff check backend
ruff format --check backend
mypy backend/src scripts
```

Frontend:

```text
npm run lint
npm run typecheck
npm run test
npm run build
```

Coverage:

- New `market_data.py` target: 100% line and branch coverage.
- API route tested on success and 503 paths.
- No reduction in existing backend coverage or test count.
- Frontend critical states are covered by behavior tests; no arbitrary coverage threshold in
  Sprint 4.

### 9.6 Manual smoke checklist

1. Start backend and frontend; open `http://localhost:3000`.
2. Confirm the page renders without a backend request at build time.
3. Confirm the market panel shows mock prices and a visible mock badge.
4. Run the default scenario; confirm predictions, financials, and provenance render.
5. Edit a market price; refresh market data; confirm the edit is preserved.
6. Use "Use market values"; confirm the latest quote is restored.
7. Submit with a blank or out-of-range field; confirm the correct field error.
8. Submit an unprofitable scenario; confirm warnings and "Not available" payback.
9. Stop the backend; confirm market and TEA failures are recoverable and inputs persist.
10. Check 320 px, 768 px, and 1280 px widths; check keyboard-only operation.

---

## 10. Implementation sequence (after approval)

| Step | Work | Tests first | Commit |
|---|---|---|---|
| 0 | Commit the approved plan | - | `docs: add Sprint 4 plan` |
| 1 | Market service value object, provider, cache | `test_market_data_service.py` | `feat: add cached market data service` |
| 2 | Response schema, route, config, app wiring | `test_market_prices_api.py` | `feat: expose market prices endpoint` |
| 3 | Market-to-TEA integration | `test_market_prices_flow.py` | `test: cover market price to TEA flow` |
| 4 | Frontend test harness and typed API client | API-client tests | `test: add frontend test harness` then `feat: add market and TEA API clients` |
| 5 | Market price panel and query hook | panel tests | `feat: add market price panel` |
| 6 | Condition/financial forms and validation | validation/component tests | `feat: add screening forms` |
| 7 | Results, warnings, provenance | results tests | `feat: add screening results panel` |
| 8 | Dashboard composition, layout, styles | dashboard tests | `feat: build screening dashboard` |
| 9 | README/env docs and full gates | - | `docs: document Sprint 4 dashboard` |
| 10 | Phase 5 report after all gates and manual smoke | - | `docs: add Sprint 4 report` |

Rules for each step:

- Do not start a step until its failing test exists.
- Keep commits focused; do not mix unrelated cleanup.
- Run the full backend/frontend gate before the final commit of each affected area.
- Record command output for the Phase 5 report.
- If a design assumption fails during implementation, stop and update this plan before
  continuing.

---

## 11. Acceptance criteria

### 11.1 Backend

- `GET /api/v1/market-prices` returns 200 with the contract in section 6.5.
- The first response has `cached=false`; a request within the TTL has `cached=true` and the
  same `as_of`.
- TTL expiry causes a fresh fetch.
- TTL is configurable and `0` disables caching.
- Provider and quote failures return 503 with no internal details.
- No outbound network call is made by the service or tests.
- `MarketPriceQuote` rejects negative, non-finite, over-cap, and non-USD values.
- `/api/v1/predict` and `/api/v1/tea` contracts are unchanged.
- The market-to-TEA integration test passes.
- Ruff, format check, mypy, and the full pytest suite pass.
- `data/schemas/odrm_v1.json` hash is unchanged.

### 11.2 Frontend

- The dashboard renders and is usable at 320 px, 768 px, and 1280 px.
- Market prices load on mount, are clearly labelled mock, and can be edited.
- Market loading/error states do not block manual TEA submission.
- A successful TEA submission renders both predictions, all financial KPIs/table rows,
  warnings, and model versions.
- `null` payback is never displayed as a number.
- No H2/CO, carbon-risk, confidence, or "verified evidence" claim is rendered.
- 422, 500, 503, and network errors are recoverable and preserve inputs.
- Client validation blocks invalid payloads before the request.
- Labels, errors, alerts, results, and keyboard flow meet the accessibility requirements.
- `npm run lint`, `npm run typecheck`, `npm run test`, and `npm run build` pass.

### 11.3 Documentation

- README documents:
  - the new endpoint and response fields;
  - mock-only status and mock values;
  - the TTL environment variable;
  - the dashboard workflow and local startup;
  - the screening-only limitation and missing roadmap outputs.
- `.env.example` documents the new setting.
- Phase 5 report records gates, live API checks, UI smoke results, and deviations.

---

## 12. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Roadmap asks for H2/CO, carbon risk, or confidence that the API cannot provide | Scope confusion or fabricated UI | Explicit deferral in this plan; report the gap in Phase 5; require a scope change to add |
| Mock prices mistaken for live market data | Misleading financial screening | `is_mock=true`, `source="mock-fixture-v1"`, prominent UI badge, README disclaimer |
| Syngas unit mismatch (`USD/tonne` vs `USD/kmol`) | Incorrect economics | Return TEA-ready `USD/kmol`; no hidden conversion; require documented conversion for a live provider |
| Cache serves stale data after an upstream change | User sees old prices | Show `as_of`, `cached`, and TTL; configurable TTL; manual refresh; no silent stale fallback |
| Concurrent cold-start requests duplicate provider calls | Wasted work | Service lock around fetch; single-fetch unit test |
| TEA accidentally coupled to market data | Architecture regression | Separate modules; no cross-imports; integration test composes only at the API-client/UI boundary |
| Market endpoint failure blocks the dashboard | User cannot use TEA | Manual price entry remains available; isolated alert |
| Frontend defaults/catalyst list drift from backend | 422 errors or invalid payloads | Central constants; mirror documented bounds; backend remains authoritative; contract risk noted |
| Next.js 16 caching/build behavior | Build-time fetch or hydration issues | Client-only dashboard fetch; static server shell; consult bundled docs; run `next build` |
| TanStack Query adds dependency/complexity | Larger surface, test setup | Use only for server state; no charts/form library; fresh test client per test |
| Numeric parsing/rounding differs from Pydantic | Preventable 422s | Mirror bounds, reject blanks/non-finite values, map server 422 back to fields, no silent clamping |
| Inaccessible form/results | Unusable for keyboard/screen-reader users | Labels, fieldsets, `aria-invalid`, live regions, visible focus, manual keyboard smoke |
| Unclear 422 detail shape | Poor error UX | Parse both Pydantic issue arrays and custom string details; fallback alert |
| Missing models in local dev | TEA 503 during demo | Document model prerequisite; UI shows actionable 503 message; tests use stubs |
| CORS/base URL misconfiguration | Browser requests fail | Keep default `http://localhost:3000` and `NEXT_PUBLIC_API_BASE_URL`; document both |
| No auth/rate limiting on market endpoint | Abuse if deployed | Out of scope; explicitly note as a production hardening item before public deployment |

---

## 13. Assumptions

- The Sprint 3 API contracts are frozen for Sprint 4.
- Models are present in the developer environment; missing models are reported as 503, not
  hidden.
- Mock market values are acceptable for Sprint 4 and are not used for investment decisions.
- No live market-data provider, credentials, or network access is required this sprint.
- The dashboard is a single-user local screening tool; no accounts or persistence are needed.
- All monetary values are USD; no FX conversion is required.
- The UI is English-only and metric, matching the backend contract.
- Modern evergreen browsers are the target.
- The market endpoint is public within the local deployment; production auth/rate limiting is
  future work.
- The CTO accepts the roadmap reconciliation in section 3 or requests a scope change before
  implementation.

---

## 14. Decisions proposed for approval

| ID | Decision |
|---|---|
| D-1 | Keep market data and TEA as separate services; compose them in the dashboard only. |
| D-2 | Use an offline mock provider in Sprint 4; add no live feed or network client. |
| D-3 | Return a flat, TEA-ready response with the three exact assumption field names. |
| D-4 | Use a configurable 24-hour server-side TTL; `0` disables caching. |
| D-5 | Validate provider quotes before caching and return a generic 503 on failure. |
| D-6 | Do not implement or fabricate H2/CO, carbon-risk, confidence, or Merkle evidence outputs. |
| D-7 | Show model provenance only; label it "Model provenance", not "Evidence Chain". |
| D-8 | Add TanStack Query for server state; do not add Recharts in Sprint 4. |
| D-9 | Use Vitest + React Testing Library; defer Playwright. |
| D-10 | Keep the market endpoint unauthenticated for local Sprint 4 use; document production hardening. |

---

## 15. Open questions for CTO review

| ID | Question | Recommended answer | Impact if changed |
|---|---|---|---|
| OQ-1 | The roadmap asks for H2/CO ratio, carbon risk, and confidence, but the current API cannot produce them. Should Sprint 4 show only available outputs? | **Yes.** Defer the missing outputs and report the gap. | Requires model/API expansion and a revised plan. |
| OQ-2 | Should the evidence component be reduced to `model_versions` provenance? | **Yes.** No confidence or hash chain in Sprint 4. | Requires new backend evidence metadata or Sprint 7 work. |
| OQ-3 | Are the mock values and TEA-ready syngas unit acceptable? | **Yes.** `3.25 USD/MMBtu`, `4.10 USD/kmol`, `28.50 USD/tCO2e`; replace later with a documented live adapter. | Changes fixture values/tests and possibly the unit contract. |
| OQ-4 | Is a 24-hour cache TTL appropriate? | **Yes.** Configurable via `ODRM_MARKET_DATA_TTL_SECONDS`; `0` disables caching. | Changes default demo freshness and tests. |
| OQ-5 | Should Sprint 4 add TanStack Query and skip Recharts? | **Yes.** TanStack Query aligns with ADR-003; no chart is needed yet. | If no, use native fetch and simplify tests; if Recharts is required, add a chart scope. |
| OQ-6 | Is React Testing Library sufficient, with Playwright deferred? | **Yes.** RTL covers the interactive contract; manual smoke covers the full browser. | If E2E is required, add browser installation and CI time. |
| OQ-7 | Should optional catalyst loading and N2 dilution be exposed, and should advanced financials be collapsed? | **Yes.** Expose optional fields and collapse OPEX/operating assumptions. | Changes form layout and test cases. |
| OQ-8 | Is an unauthenticated local market endpoint acceptable for Sprint 4? | **Yes.** Treat auth/rate limiting as production hardening. | Requires auth design and tests. |

---

## 16. Approval gate

No implementation begins until the CTO replies with exactly:

```text
AUTHORIZED: Sprint 4 implementation phase
```

Before that phrase, the expected state is:

- only `docs/SPRINT_4_PLAN.md` added or changed;
- no backend/frontend source changes;
- no dependency installs;
- no commits;
- no generated report.
