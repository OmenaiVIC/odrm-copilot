# Sprint 11 D4 Map Scope Change — Plan

| | |
|---|---|
| Status | Phase 2 — awaiting CTO approval |
| Date | 2026-11-26 |
| Baseline | `70433f8` (D4 Phase 5 report) |
| Scope Change trigger | CTO identified geospatial interface requirement during D4 Phase 4 |

## §1 Goal

Add an interactive Leaflet map to `DetectionPanel` so operators can
see synthetic hotspots geographically. The map is a visual enhancement
above the existing accessible table. It does not replace the table.

Constraint: must not break Next.js 16 App Router SSR. Must load
client-side only.

## §2 Deliverables

1. `frontend/src/components/detection/hotspot-map.tsx` — the map
   component, client-only.
2. `frontend/src/components/detection/detection-panel.tsx` —
   modified to render `<HotspotMap>` above the table via
   `next/dynamic` with `ssr: false`.
3. `frontend/src/components/detection/detection-panel.test.tsx` —
   modified with two new tests (map renders, markers per hotspot)
   and a `vi.mock('react-leaflet')` at the top.

## §3 Acceptance criteria

1. Map renders above the table when hotspot data is present.
2. Each hotspot renders a `<Marker>` at `[latitude, longitude]`.
3. Clicking a marker opens a `<Popup>` showing ID, coordinates,
   intensity.
4. Map is centered on `[4.8, 7.0]` at zoom 10 (Niger Delta demo
   center; mock data only).
5. Loading placeholder ("Loading map...") shows while the dynamic
   import resolves.
6. Existing table view still renders below the map and all prior
   tests still pass.
7. `SYNTHETIC DATA` badge remains visible in the panel header (the
   map inherits this — the badge is in the panel, not duplicated in
   the map).
8. No hydration mismatch warnings in the console during dev.

## §4 Files to Create

| Path | Purpose |
|---|---|
| `frontend/src/components/detection/hotspot-map.tsx` | Client-only map component |

## §5 Files to Modify

| Path | Change |
|---|---|
| `frontend/src/components/detection/detection-panel.tsx` | Add `next/dynamic` import, render `<HotspotMap>` above the table |
| `frontend/src/components/detection/detection-panel.test.tsx` | Add `vi.mock('react-leaflet')`, add 2 new tests |

**No other files touched.** `package.json` already has the deps
installed. If Phase 3 discovers a peer-dep mismatch, that becomes a
plan addendum, not an in-phase fix.

## §6 Technical design

### Map component (`hotspot-map.tsx`)

- **First line must be `'use client';`.** The component uses
  `react-leaflet` which relies on `window` at module load.
- Import `leaflet/dist/leaflet.css` at the top of this file. This is
  the ONLY place the CSS is imported.
- Exports a default `HotspotMap` component taking a single prop:
  `{ hotspots: Hotspot[] }`.
- Uses `MapContainer`, `TileLayer`, `Marker`, `Popup` from
  `react-leaflet`.
- `MapContainer center=[4.8, 7.0] zoom=10 style={{ height: '400px', width: '100%' }}`.
- `<TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="© OpenStreetMap contributors" />`.
- For each hotspot: `<Marker position={[h.latitude, h.longitude]}><Popup>...</Popup></Marker>`.
  Popup content: `ID: {h.id}`, `Latitude: {h.latitude}`, `Longitude: {h.longitude}`, `Intensity: {h.intensity}`.
- If `hotspots.length === 0`, render a small `<p>No hotspots in current view.</p>` inside the map's container (above the map, or as an overlay — your choice, but document it).

### Panel modification (`detection-panel.tsx`)

- Ensure the file has `'use client';` at the top if not already
  present. If it doesn't, add it (App Router requires this for
  components using `next/dynamic` with `ssr: false`).
- Import: `import dynamic from 'next/dynamic';`
- Import: `const HotspotMap = dynamic(() => import('./hotspot-map'), { ssr: false, loading: () => <div className="p-4 text-sm text-gray-500">Loading map...</div> });`
- Render `<HotspotMap hotspots={data.hotspots} />` above the existing `<table>` (or equivalent list rendering).
- Do NOT duplicate the "SYNTHETIC DATA" badge inside the map. It
  lives in the panel; the map inherits it visually.

### Test mock (`detection-panel.test.tsx`)

At the top of the file, add:

```typescript
vi.mock('react-leaflet', () => ({
  MapContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="map-container">{children}</div>
  ),
  TileLayer: () => <div data-testid="tile-layer" />,
  Marker: ({ children, position }: { children: React.ReactNode; position: [number, number] }) => (
    <div data-testid="map-marker" data-lat={position[0]} data-lng={position[1]}>
      {children}
    </div>
  ),
  Popup: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="map-popup">{children}</div>
  ),
}));
```

The mock must expose `data-testid` attributes so tests can query
markers by test ID and assert count and position.

## §7 TDD test plan

Two new tests in `detection-panel.test.tsx`:

1. `test_detection_panel_renders_map` — Given a mocked fetch returning
   2 hotspots, the panel renders `data-testid="map-container"` when
   the dynamic import resolves. Use `await waitFor(() => expect(screen.getByTestId('map-container')).toBeInTheDocument())`.

2. `test_detection_panel_renders_marker_per_hotspot` — Given the
   same mocked fetch, after map loads, assert
   `screen.getAllByTestId('map-marker')` has length 2, and the
   data-lat/data-lng attributes match the hotspot fixture values.

Existing tests in the file must still pass unmodified.

## §8 Verification (Phase 4 evidence checklist)

- `npm --prefix frontend run typecheck` — clean
- `npm --prefix frontend run test` — new total = prior 35 + 2 = 37
  passing, 0 failing
- `npm --prefix frontend run build` — routes generate, no SSR errors
  from leaflet
- `git status -uall --short` — exactly the 3 files listed in §4 + §5
- Manual dev check: `npm --prefix frontend run dev` and visit
  `/dashboard` — confirm map loads without console errors

## §9 Audit Readiness Impact

Per `docs/SPRINT_WORKFLOW.md` Audit Readiness Requirements.

| # | Item | Status for D4 Map |
|---|---|---|
| 1 | Scope traceability | ✅ Produced — §1 names the Scope Change trigger |
| 2 | Repo hygiene | ⚠️ Partial — no new dependencies; CONTRIBUTING/CODE_OF_CONDUCT deferred to Sprint 12 |
| 3 | Integration tests | ⚠️ Partial — 2 new frontend component tests (Vitest). Not true integration tests. Documented as frontend unit coverage |
| 4 | Threat model | ➖ N/A — no new attack surface. Leaflet renders client-side from public OSM tiles; no user data flows to tile provider beyond IP |
| 5 | Dataflow diagram | ➖ N/A — no new dataflow |
| 6 | Cryptographic correctness | ➖ N/A |
| 7 | LLM boundary integrity | ➖ N/A |
| 8 | Personal data handling | ➖ N/A — no personal data in map |
| 9 | Tooling scan (bonus) | ➖ N/A — no new runtime deps installed (already in package.json from CTO Phase 1) |
| 10 | Remediation plan (bonus) | ➖ N/A |
| 11 | Dependency review (bonus) | ⚠️ Partial — new deps (`leaflet`, `react-leaflet`, `@types/leaflet`) were installed by CTO during Phase 1. Phase 3 pre-check will verify peer-dep compatibility; `npm audit` should be run in Phase 4 |

**Bundle size note:** Leaflet + react-leaflet adds ~150KB gzipped to
the dashboard bundle. This is accepted for a geospatial interface,
but noted here so it is not a surprise in future bundle analysis.

**Accessibility note:** the map is a visual enhancement. The
accessible table remains the primary interaction surface for screen
readers. No keyboard-only map controls are added in this deliverable.
Documented as a future enhancement.

## §10 Out of Scope

- Real satellite data (still mock hotspots)
- `bbox`/`since` UI controls (backend supports, frontend wiring deferred)
- Map clustering (single-marker-per-hotspot is the D4 map scope)
- Tile provider changes (OpenStreetMap default only)
- Map controls beyond zoom (no layers, no scale bar, no fullscreen)
- Keyboard navigation for markers (documented as future)

## §11 Commit message

`feat(detection): add map visualization to detection panel`

## §12 Acceptance (Phase 5 gate)

D4 Map is complete when:
1. Two new frontend tests pass, prior 35 still pass (total 37).
2. `npm run typecheck` clean.
3. `npm run build` produces routes without SSR errors.
4. `git status -uall --short` shows only the 3 files.
5. Manual dev check: map loads, no console hydration warnings.
6. `docs/SPRINT_11D4_MAP_REPORT.md` committed with Audit Readiness
   Status section.

## §13 Deviations

Any deviation requires a plan addendum committed BEFORE
implementation. Deviations captured in Phase 5 report.
