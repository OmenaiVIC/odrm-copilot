\# Sprint 11 Deliverable D4: Detection Hotspots Dashboard



\*\*Status:\*\* Complete (Table View)

\*\*Date:\*\* 2026-11-26

\*\*Commit:\*\* `9d32bc9` (implementation), `d1f216d` (plan)

\*\*Tag:\*\* none



\## 1. What was built

Wired the existing detection mock adapter into the frontend dashboard. Operators can now see the list of methane hotspots from the `MockNogietAdapter` on their screening screen, labeled clearly as synthetic demonstration data.



\### Backend

\- \*\*New route:\*\* `GET /api/v1/detection/hotspots`. Authenticated via `get\_current\_user`. Returns the full `Hotspot` list from `app.state.detection\_source`.

\- \*\*Query parameters:\*\* `bbox` (comma-separated `min\_lat,min\_lon,max\_lat,max\_lon`) and `since` (ISO 8601 timezone-aware datetime). Both optional.

\- \*\*Error mapping:\*\* Invalid `bbox` or naive `since` produces HTTP 422 with `{"code": "INVALID\_DETECTION\_QUERY", "message": "..."}`.

\- \*\*Adapter injection:\*\* `create\_app` accepts an optional `detection\_source: DetectionSource | None = None` parameter. If absent, it defaults to `MockNogietAdapter()`. Tests inject a stub.

\- \*\*Tests:\*\* `backend/tests/detection/test\_detection\_api.py` with 8 tests covering auth (401), default response (200, six items), `bbox` filtering, `since` filtering, and 422 error cases.



\### Frontend

\- \*\*Types:\*\* `Hotspot` interface added to `frontend/src/lib/types.ts` with six fields matching the backend schema.

\- \*\*API client:\*\* `getDetectionHotspots()` added to `frontend/src/lib/api.ts`.

\- \*\*Hook:\*\* `useDetectionHotspots()` added to `frontend/src/hooks/use-detection.ts`.

\- \*\*Component:\*\* `DetectionPanel` in `frontend/src/components/detection/detection-panel.tsx`. Renders loading, error, empty, and populated states. Includes a table view with hotspot ID, coordinates, intensity (ppb), detection time (UTC), source, and a copy-coordinates action. Displays a `SYNTHETIC DATA` badge.

\- \*\*Dashboard integration:\*\* `<DetectionPanel />` inserted as a full-width section above the existing two-column screening form.

\- \*\*Tests:\*\* `frontend/src/components/detection/detection-panel.test.tsx`.



\## 2. Test coverage and pass rates

\- \*\*Backend targeted:\*\* 8 passed.

\- \*\*Frontend targeted:\*\* 2 passed.

\- \*\*Full backend suite:\*\* 622 passed (614 prior + 8 new).

\- \*\*Full frontend suite:\*\* 35 passed.

\- \*\*Ruff:\*\* Clean.

\- \*\*Mypy:\*\* Success (69 source files).

\- \*\*Frontend typecheck:\*\* Clean.

\- \*\*Frontend lint:\*\* Clean.

\- \*\*Frontend build:\*\* Successful (Next.js 16.4.3).



\## 3. Deviations from the plan

\### Deviation 1 — Badge rename to `SYNTHETIC DATA`

The original plan specified a `MOCK DATA` badge. However, the existing `MarketPricePanel` already rendered `MOCK DATA`. Adding a second `MOCK DATA` badge caused a duplicate-string test failure in `dashboard.test.tsx`. The badge was renamed to `SYNTHETIC DATA`, which is a more accurate label. The test was updated.



\## 4. Known issues / technical debt

\- \*\*Map visualization deferred.\*\* An interactive map view is a necessary UX addition for a geospatial interface but was not in the original D4 scope. It has been added to the backlog as a formal Scope Change and will go through its own Phase 1-5 workflow.

\- \*\*Real adapter not yet implemented.\*\* The panel currently renders the six deterministic `MockNogietAdapter` fixtures.

\- \*\*No `bbox`/`since` UI controls.\*\*

\- \*\*Clipboard fallback.\*\* Depends on `navigator.clipboard.writeText`.



\## 5. Next deliverable

\*\*D4 Scope Change (Map View):\*\* Add an interactive Leaflet map to the detection panel. 

\*\*D5 — Soroban Evidence Registry Prototype:\*\* Deploy Rust contract to Testnet.

