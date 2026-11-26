# Sprint 11 D4 Plan - Detection Hotspots API and Dashboard Wiring

| | |
|---|---|
| Status | Draft - awaiting CTO Phase 2 approval |
| Date | 2026-11-26 |
| Deliverable | D4 (detection hotspots API + dashboard panel) |
| Baseline | `5fbd913` (Sprint 11 D3 Phase 5 report) |
| Phase 4 authorization phrase on record | `AUTHORIZED: Sprint 11 D4 implementation phase` |
| Resolutions incorporated | Q1 test path `backend/tests/detection/test_detection_api.py`; Q2 direct `MockNogietAdapter` import; Q3 comma-separated `bbox`; Q4 async route; Q5 component-owned hook with `QueryClientProvider` and clipboard stub; Q6 full-width panel above the form grid |

No implementation code, test code, or file creation beyond this plan until the CTO
approves this document and authorizes Phase 3.

This plan supersedes the pre-fill behavior in `docs/SPRINT_11_PLAN.md` AC-8 and test
#15. D4 now exposes the missing backend endpoint and makes the dashboard panel display
hotspots with a copy-coordinates action. The screening form is not modified.

---

## 1. Goal

Build the missing authenticated backend route that serves detection hotspots from the
configured `DetectionSource`, defaulting to `MockNogietAdapter`, and wire that route into
the dashboard through a TanStack Query hook and a new `DetectionPanel`. The panel displays
the synthetic hotspots, labels them as mock data, and lets the operator copy a hotspot's
coordinates for manual use. The panel is full-width above the existing two-column
screening form and does not alter form state or submission.

---

## 2. Deliverables

1. **Backend route.** `GET /api/v1/detection/hotspots` returns a JSON list of `Hotspot`
   objects from `app.state.detection_source`. The route is authenticated, supports
   optional `bbox` and `since` filters, and maps invalid filter values to HTTP 422.
2. **Adapter injection.** `create_app` instantiates `MockNogietAdapter` by default and
   exposes it as `app.state.detection_source`; an optional `detection_source` argument
   allows tests to inject a stub without changing route code.
3. **Frontend client and type.** `getDetectionHotspots()` and the `Hotspot` interface are
   added to the existing API and type modules.
4. **Frontend hook.** `useDetectionHotspots()` wraps the client function in TanStack Query.
5. **Detection panel.** `DetectionPanel` renders loading, error, empty, and populated
   states; displays hotspot coordinates, intensity, detection time, and source; shows a
   `MOCK DATA` badge and disclaimer; and copies coordinates with visible confirmation.
6. **Dashboard wiring.** `<DetectionPanel />` is placed as a full-width section between the
   header and the screening form.
7. **Tests.** Backend API tests cover authentication, default fetch, `bbox`, `since`, and
   invalid inputs. Frontend Vitest tests cover rendering and clipboard copying.

---

## 3. Acceptance criteria mapped to tests

| ID | Criterion | Primary test(s) |
|---|---|---|
| D4-1 | `GET /api/v1/detection/hotspots` exists, is registered under `/api/v1`, and returns a JSON list of hotspots from the configured `DetectionSource`. | `test_detection_endpoint_returns_all_fixtures` |
| D4-2 | Anonymous requests return `401`; authenticated requests succeed. | `test_detection_endpoint_requires_auth` |
| D4-3 | With no query parameters, the route returns all six deterministic mock fixtures with `source="mock_nogiet"`. | `test_detection_endpoint_returns_all_fixtures` |
| D4-4 | Optional `bbox` and `since` query parameters filter using the adapter's inclusive semantics. | `test_detection_endpoint_filters_by_bbox`, `test_detection_endpoint_filters_by_since` |
| D4-5 | Invalid `bbox` values and naive `since` timestamps return `422` with an `INVALID_DETECTION_QUERY` envelope, not `500`. | `test_detection_endpoint_rejects_invalid_bbox`, `test_detection_endpoint_rejects_naive_since` |
| D4-6 | Backend tests cover auth-required, default response, `bbox`, `since`, and invalid inputs. | The backend test module listed in section 7 |
| D4-7 | `getDetectionHotspots()` calls the new endpoint through `apiFetch`. | `test_detection_panel_renders` (asserts the request URL) |
| D4-8 | The `Hotspot` interface matches the backend JSON: `id`, `latitude`, `longitude`, `intensity_ppb`, `detected_at`, `source`; `detected_at` is a string. | `npm run typecheck`; `test_detection_panel_renders` |
| D4-9 | `useDetectionHotspots()` is a TanStack Query v5 hook with a stable query key. | `test_detection_panel_renders` (query fires and resolves) |
| D4-10 | `DetectionPanel` renders loading, error, empty, and populated states. | `test_detection_panel_renders` plus Phase 3 review; optional error-state test |
| D4-11 | Clicking a hotspot copies `latitude, longitude` to the clipboard and shows a visible confirmation. | `test_detection_panel_copies_coordinates` |
| D4-12 | `<DetectionPanel />` appears in the dashboard as a full-width section above the two-column grid. | Phase 3 review; `npm run build` |
| D4-13 | Vitest mocks fetch, asserts the hotspot list renders, and covers the clipboard interaction. | `test_detection_panel_renders`, `test_detection_panel_copies_coordinates` |
| D4-14 | AC-10 gates pass: backend suite, `ruff`, `mypy`, frontend typecheck, lint, build, and Vitest. | Phase 4 gate commands in section 7 |

---

## 4. Files to create

```
backend/src/odrm/api/detection.py
backend/tests/detection/test_detection_api.py
frontend/src/hooks/use-detection.ts
frontend/src/components/detection/detection-panel.tsx
frontend/src/components/detection/detection-panel.test.tsx
```

`backend/tests/detection/__init__.py` already exists, so no new package initializer is
required.

---

## 5. Files to modify

```
backend/src/odrm/main.py
frontend/src/lib/api.ts
frontend/src/lib/types.ts
frontend/src/components/dashboard/dashboard.tsx
```

`backend/src/odrm/detection/__init__.py` is not modified. `MockNogietAdapter` remains
available only through `odrm.detection.mock_nogiet`, per the Sprint 10B export decision.

---

## 6. Technical design

### 6.1 Backend route and adapter injection

**Router.** `backend/src/odrm/api/detection.py` defines an `APIRouter` with
`dependencies=[Depends(get_current_user)]`, matching `backend/src/odrm/api/evidence.py`.
The route is `GET /detection/hotspots`, declared `async def`, with
`response_model=list[Hotspot]`. It reads the adapter from
`req.app.state.detection_source` and awaits `source.fetch_hotspots(...)`.

**Why `app.state`.** The repository already constructs services in `create_app` and stores
them on `app.state` (`backend/src/odrm/main.py:53-112`), and routers retrieve them through
`req.app.state` (`backend/src/odrm/api/evidence.py:27`,
`backend/src/odrm/api/routes.py:66`, `backend/src/odrm/api/whitelist.py:37`). FastAPI
`Depends` is reserved for the auth boundary. Using `app.state` keeps one service-resolution
pattern and lets tests replace the adapter after app creation or through the new optional
argument.

**`create_app` changes in `backend/src/odrm/main.py`.**

1. Import `DetectionSource` from `odrm.detection.base`.
2. Import `MockNogietAdapter` directly from `odrm.detection.mock_nogiet`.
3. Import the detection router from `odrm.api.detection`.
4. Add a keyword-only `detection_source: DetectionSource | None = None` parameter to
   `create_app`, alongside the existing injectable services.
5. Set `app.state.detection_source = detection_source or MockNogietAdapter()`.
6. Register the router with `prefix="/api/v1"` and `tags=["detection"]`, after the
   evidence router.

No database, migration, or settings change is required. The adapter performs no I/O.

### 6.2 Query parameters

**`bbox`** is an optional string query parameter in the order
`min_latitude,min_longitude,max_latitude,max_longitude`, for example
`4.80,7.00,4.83,7.06`.

Parsing rules in the route:

1. Split on commas.
2. Require exactly four tokens.
3. Convert each token to `float`.
4. Pass the resulting four-tuple to `fetch_hotspots`.
5. The existing `_require_bbox_valid` in `backend/src/odrm/detection/base.py:21-46`
   enforces finite values, latitude range `[-90, 90]`, longitude range `[-180, 180]`,
   and `min <= max`.

Filtering is inclusive on both axes, as implemented by `MockNogietAdapter`.

**`since`** is an optional ISO 8601 datetime query parameter with a timezone offset, for
example `2026-02-01T00:00:00Z`. FastAPI parses the value. The existing
`_require_timezone_aware` in `backend/src/odrm/detection/base.py:49-51` rejects naive
datetimes. Filtering is inclusive (`detected_at >= since`).

No other query parameters are added in D4. With neither parameter, the route returns all
six fixtures in their defined order.

### 6.3 Error handling

The route parses `bbox` and calls `fetch_hotspots` inside one `try` block. Any
`ValueError` from comma-count validation, float conversion, finite-value validation,
range/order validation, or naive-`since` validation becomes:

```
HTTP 422
detail: {"code": "INVALID_DETECTION_QUERY", "message": "<validation reason>"}
```

Malformed `since` syntax is rejected by FastAPI/Pydantic with its standard 422 response
before the handler runs. Unauthenticated requests are rejected by `get_current_user` with
the existing 401 envelope. Expected validation failures never become 500s. The route does
not log request bodies or secrets.

### 6.4 Frontend API client and type

**`frontend/src/lib/types.ts`.** Add an exported `Hotspot` interface with:

| Field | Type |
|---|---|
| `id` | `string` |
| `latitude` | `number` |
| `longitude` | `number` |
| `intensity_ppb` | `number` |
| `detected_at` | `string` |
| `source` | `string` |

`detected_at` is typed as a string because the backend serializes its Pydantic
`datetime` as ISO 8601 JSON.

**`frontend/src/lib/api.ts`.** Add `Hotspot` to the type import and add
`getDetectionHotspots(): Promise<Hotspot[]>`, which calls
`apiFetch<Hotspot[]>("/detection/hotspots", { method: "GET" })`. No query parameters are
exposed in the D4 UI; the backend filters are tested independently and remain available
for a later UI.

### 6.5 TanStack Query hook

`frontend/src/hooks/use-detection.ts` exports `useDetectionHotspots()`. It uses
`useQuery` from `@tanstack/react-query` with `queryKey: ["detection-hotspots"]` and
`queryFn: getDetectionHotspots`. It relies on the app-level `QueryClient` defaults in
`frontend/src/app/providers.tsx` and does not add custom retry, polling, or refetch
behavior. The mock fixtures are static, so the default five-minute stale time is
acceptable.

### 6.6 Detection panel layout and copy interaction

`frontend/src/components/detection/detection-panel.tsx` is a client component
(`'use client'`) that owns `useDetectionHotspots()`.

**Structure.**

- Full-width `section` with the same border, background, radius, and shadow treatment as
  the dashboard sections.
- Header with the title `Methane Detection Hotspots`, a `MOCK DATA` badge, and a short
  disclaimer that the fixtures are synthetic demonstration data, not real observations.
- A responsive table inside an `overflow-x-auto` container.

**Table columns.**

| Column | Content |
|---|---|
| Hotspot | `id` |
| Coordinates | latitude and longitude to four decimal places |
| Intensity | `intensity_ppb` formatted with thousands separators, plus `ppb` |
| Detected | `detected_at` formatted in UTC with an explicit `UTC` suffix |
| Source | raw `source` value, e.g. `mock_nogiet` |
| Action | copy button |

**States.**

- Loading: `role="status"` message, e.g. `Loading detection hotspots...`.
- Error: `role="alert"` message plus a `Retry` button wired to `refetch()`.
- Empty: a short `No hotspots returned.` message.
- Populated: the table and a result count.

**Copy interaction.**

- Each row has a `type="button"` button labelled `Copy coordinates` with an
  `aria-label` that includes the hotspot id.
- The handler writes the raw numeric values joined by `", "` (for example
  `4.8156, 7.0498`) through `navigator.clipboard.writeText`.
- On success, the button shows `Copied` for two seconds and an `aria-live="polite"`
  region announces the copy. On failure, it shows `Copy failed` for two seconds and the
  panel does not crash.
- The timeout is cleared on unmount.
- The panel sits outside the screening form, but `type="button"` is still required to
  prevent any future form association from submitting.

The table is used instead of cards because it keeps the coordinate, intensity, time, and
source fields aligned and easy to scan; the overflow container handles narrow viewports.

### 6.7 Dashboard integration

In `frontend/src/components/dashboard/dashboard.tsx`:

1. Import `DetectionPanel` from `@/components/detection/detection-panel`.
2. Insert `<DetectionPanel />` between the closing `</header>` at line 162 and the
   `<form>` at line 164.

The dashboard container is already a vertical flex column with `gap-8`, so the panel
occupies the full content width above the two-column form. No form state, submit handler,
or results layout changes.

### 6.8 Risks and edge cases

- **Mock data presented as real.** The panel must show the `MOCK DATA` badge and
  disclaimer; the source column keeps `mock_nogiet` visible.
- **Clipboard permission or API unavailable.** The handler catches rejection and shows
  `Copy failed`; the page remains usable.
- **Invalid `bbox` or naive `since`.** The route maps `ValueError` to 422; tests cover
  short tuples, out-of-range values, non-finite values, and naive datetimes.
- **Malformed `since` syntax.** FastAPI returns its standard 422 before the handler.
- **Authentication.** The router-level dependency protects the endpoint; an anonymous
  test asserts 401.
- **Precision.** Display rounds to four decimals, but the copied string uses the raw
  numeric values so the operator does not lose precision.
- **Hydration and time zones.** The panel is a client component and formats times in UTC
  with an explicit suffix, avoiding locale-dependent output.
- **Test flakiness.** Frontend tests await the rendered rows and the copy confirmation
  instead of asserting immediate state; timers are only used for the two-second label
  reset and are not advanced in the required tests.
- **Import policy.** `MockNogietAdapter` is imported directly from
  `odrm.detection.mock_nogiet`; `odrm.detection.__init__` is untouched.

---

## 7. TDD test plan

### 7.1 Backend tests

File: `backend/tests/detection/test_detection_api.py`
Marker: `pytestmark = pytest.mark.integration`

| Test | AC | What it proves |
|---|---|---|
| `test_detection_endpoint_requires_auth` | D4-2 | `anonymous_client` receives 401; the route is protected at the router level. |
| `test_detection_endpoint_returns_all_fixtures` | D4-1, D4-3 | Authenticated 200; six items; exact ids `mock-nogiet-001` through `006` in order; every item has exactly the six schema keys; every `source` is `mock_nogiet`. |
| `test_detection_endpoint_filters_by_bbox` | D4-4 | `bbox=4.80,7.00,4.83,7.06` returns only `mock-nogiet-001` and `mock-nogiet-005`. |
| `test_detection_endpoint_filters_by_since` | D4-4 | `since=2026-02-01T00:00:00Z` returns `mock-nogiet-004`, `005`, and `006`. |
| `test_detection_endpoint_rejects_invalid_bbox` | D4-5 | Three-value bbox, out-of-range latitude, and `nan` each return 422 with `detail.code == "INVALID_DETECTION_QUERY"`. |
| `test_detection_endpoint_rejects_naive_since` | D4-5 | `since=2026-02-01T00:00:00` returns 422 with `detail.code == "INVALID_DETECTION_QUERY"`. |

Tests use the existing `client` and `anonymous_client` fixtures from
`backend/tests/conftest.py`. Query parameters are passed through `params=` so httpx
performs the encoding.

### 7.2 Frontend tests

File: `frontend/src/components/detection/detection-panel.test.tsx`

The test creates a fresh `QueryClient` with `retry: false`, wraps `DetectionPanel` in
`QueryClientProvider`, mocks `global.fetch`, and defines `navigator.clipboard.writeText`
with `Object.defineProperty`. It uses the existing Vitest/jsdom setup.

| Test | AC | What it proves |
|---|---|---|
| `test_detection_panel_renders` | D4-7, D4-8, D4-9, D4-10, D4-13 | Fetch is called for `/detection/hotspots`; the two fixture ids, coordinates, intensity, source, and `MOCK DATA` badge render after the query resolves. |
| `test_detection_panel_copies_coordinates` | D4-11, D4-13 | Clicking the first row's copy button calls `navigator.clipboard.writeText` with `4.8156, 7.0498` and shows the `Copied` confirmation. |

An optional third test for the error state may be added if the Phase 3 review requests it;
it is not required by D4-13.

### 7.3 Red-green order and focused commands

Backend, in this order:

1. `test_detection_endpoint_requires_auth`
2. `test_detection_endpoint_returns_all_fixtures`
3. `test_detection_endpoint_filters_by_bbox`
4. `test_detection_endpoint_filters_by_since`
5. `test_detection_endpoint_rejects_invalid_bbox`
6. `test_detection_endpoint_rejects_naive_since`

For each test: write the failing test only, run the focused command, paste the failure,
implement the minimum production code, re-run and paste the pass, then move on.

```
.\.venv\Scripts\python.exe -m pytest backend/tests/detection/test_detection_api.py::<test> -q
```

Frontend, in this order:

1. `test_detection_panel_renders`
2. `test_detection_panel_copies_coordinates`

```
npm test -- src/components/detection/detection-panel.test.tsx
```

### 7.4 Full Phase 4 gates

After the focused tests pass, run and paste each result:

```
.\.venv\Scripts\python.exe -m pytest backend/tests -q
.\.venv\Scripts\python.exe -m ruff check backend/src backend/tests
.\.venv\Scripts\python.exe -m mypy
npm run typecheck
npm run lint
npm run build
npm test
```

D4 touches the frontend, so the frontend gates are required for this deliverable, unlike
D2.

---

## 8. Commit message

```
feat(detection): wire detection hotspots into frontend dashboard
```

One commit after all D4 gates pass. Per sprint protocol: commit, push, then stop for the
CTO audit. Do not begin D5.

---

## 9. Audit protocol (Phases 3 and 4)

**Phase 3 - Review gate (no disk writes).**

Show the exact proposed contents in chat, in this order:

1. `backend/src/odrm/api/detection.py`
2. `backend/src/odrm/main.py` delta
3. `backend/tests/detection/test_detection_api.py`
4. `frontend/src/lib/types.ts` delta
5. `frontend/src/lib/api.ts` delta
6. `frontend/src/hooks/use-detection.ts`
7. `frontend/src/components/detection/detection-panel.tsx`
8. `frontend/src/components/detection/detection-panel.test.tsx`
9. `frontend/src/components/dashboard/dashboard.tsx` delta

No files are written and no tests run during Phase 3. The CTO audits and requests
revisions. Phase 3 ends only when the CTO explicitly authorizes Phase 4.

Per `frontend/AGENTS.md`, before writing the client component in Phase 4, read the
relevant Next.js guide under `frontend/node_modules/next/dist/docs/` for this installed
version.

D4 adds no new trust boundary, data store, secret, external integration, or personal data
flow; it reuses the existing authenticated browser-to-API path. No `docs/THREAT_MODEL.md`
or `docs/DATAFLOW.md` diff is proposed. If the CTO treats the new authenticated read-only
route as security-sensitive, Phase 3 will include a short threat-model addendum instead.

**Phase 4 - Implementation (TDD).**

For each test in section 7.3: write the failing test, run the focused command, paste the
failure, implement the minimum production code, re-run, paste the pass. No implementation
ahead of a failing test.

After all D4 tests pass, run the full gates in section 7.4 and paste each result. Then
commit with the section 8 message, push, and stop for the CTO audit. Do not begin D5.

---

## 10. Out of scope for D4

- Pre-filling the screening form with hotspot coordinates (superseded by the approved
  copy-coordinates action)
- Real satellite, NOGIET, NUPRC, or NMDPRA ingestion; a real `DetectionSource`
- Map visualization, clustering, heatmaps, or geospatial rendering
- User-facing filter controls for `bbox` or `since`
- Pagination, polling, websockets, or live refresh
- Persistence or caching beyond the existing TanStack Query defaults
- Authentication, authorization, or session changes
- Changes to the screening form, results panel, market panel, or chat
- Global navigation or layout changes outside the full-width panel insertion
- D5 Soroban registry work
- Deployment, hosting, or environment changes

---

## 11. Audit Readiness Impact

| # | Item | Impact | Evidence / deferral |
|---|---|---|---|
| 1 | Scope traceability | Affected | This plan, sections 1-2 and 10; sprint plan D4 scope; approved Phase 1 scope change. |
| 2 | Repo hygiene | Affected | New files follow existing backend/frontend directory and naming conventions; no dead code; no new dependency. |
| 3 | Integration tests | Affected | Backend API test marked `integration` and frontend Vitest tests; raw focused and full-gate output pasted in Phase 4. |
| 4 | Threat model | No impact | No new trust boundary, data store, secret, or external integration; the route reuses `get_current_user` and serves synthetic data. No `docs/THREAT_MODEL.md` change proposed. |
| 5 | Dataflow diagram | No impact | Existing browser-to-API flow only; no new data entity or external flow. |
| 6 | Cryptographic correctness | No impact | No hashing, Merkle, signing, or verification change. |
| 7 | LLM boundary integrity | No impact | No LLM, prompt, or tool-calling path. |
| 8 | Personal data handling | No impact | Hotspot fixtures are synthetic; no personal data is added, stored, or exposed. |
| 9 | Tooling scan (bonus) | No impact | No new dependency; sprint-level scan remains unchanged. |
| 10 | Remediation plan (bonus) | No impact | No findings introduced by D4. |
| 11 | Dependency review | No impact | No `pyproject.toml`, `package.json`, or `Cargo.toml` change. |

No audit-readiness evidence is deferred by D4. The only new authenticated surface is a
read-only endpoint over synthetic data, and its auth behavior is covered by
`test_detection_endpoint_requires_auth`.

---

## Phase 2 gate

Stopping at Phase 2. No implementation code, no test code, no files beyond this plan, and
no test execution. Awaiting CTO approval of this plan before Phase 3.
