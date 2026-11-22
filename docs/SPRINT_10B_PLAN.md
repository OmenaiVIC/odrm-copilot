# Sprint 10 Plan - Deliverable 0b: Mock NOGIET-Style Adapter

| | |
|---|---|
| Status | **Draft - awaiting CTO approval** |
| Date | 2026-11-22 |
| Scope | Demonstration `DetectionSource` adapter with deterministic Niger Delta fixtures and inclusive `bbox`/`since` filtering |
| Dependency | 0a complete at `75180d2`; Phase 1 constitution approved |
| Approval phrase | `AUTHORIZED: Sprint 10 0b implementation phase` |

> **Planning gate:** this file is the Phase 2 deliverable for 0b. No implementation code, test code, or commits may be created until the CTO approves this plan with the exact phrase above.

> **Plan location decision:** 0b uses a separate plan file, `docs/SPRINT_10B_PLAN.md`. `docs/SPRINT_10_PLAN.md` is the approved 0a artifact and remains unchanged for audit continuity.

> **Phase 1 CTO decisions incorporated:**
>
> - The two implementation files are listed explicitly in section 5.
> - `MockNogietAdapter` is **not** exported from `odrm.detection.__init__`; consumers import it directly from `odrm.detection.mock_nogiet`.
> - Fixtures are a module-level tuple of `Hotspot` instances; the adapter returns `list(self._fixtures)` per call and does **not** re-construct `Hotspot` objects on every call.

---

## 1. Goal

Provide a demonstration detection adapter that conforms to the 0a `DetectionSource` contract and returns deterministic, schema-valid methane hotspot fixtures for the Niger Delta. The adapter exercises the inherited `bbox` and `since` contract end to end, including inclusive spatial and temporal filtering, without integrating with NOGIET, any regulator, or any real data source.

0b is a foundation deliverable for later API and agentic layers. It does not fetch, persist, or render data.

---

## 2. Deliverables

1. **`MockNogietAdapter(DetectionSource)`** in `backend/src/odrm/detection/mock_nogiet.py`.
2. **Six deterministic Niger Delta fixtures** (at least five required) with mixed timestamps and intensities, all attributed to `source == "mock_nogiet"`.
3. **Inclusive `bbox` and `since` filtering** implemented only in `_fetch_hotspots`, using the validated inputs supplied by the 0a template method.
4. **Required disclaimer docstring** identifying the adapter as a demonstration and stating NOGIET's provenance and Valoris's non-involvement.
5. **Unit tests** in `backend/tests/detection/test_mock_nogiet_adapter.py` covering every acceptance criterion.

No `BBox` value object is introduced. No package export is added.

---

## 3. Acceptance criteria

The twelve Phase 1 criteria, restated verbatim in substance and mapped to verification:

| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | `MockNogietAdapter` subclasses `DetectionSource` and implements only `_fetch_hotspots`. `fetch_hotspots` is not overridden; the inherited template method remains the sole public entry point and owns validation. | Subclass test; `__dict__` and function-identity assertions |
| AC-2 | `await MockNogietAdapter().fetch_hotspots()` returns a non-empty `list[Hotspot]` with at least five fixtures. | Default-fetch test; determinism test |
| AC-3 | Every fixture has `source == "mock_nogiet"`. | Source-attribution test |
| AC-4 | Fixtures use plausible real Niger Delta coordinates around latitude 4.8, longitude 7.0, not arbitrary global points. | Coordinate-envelope test |
| AC-5 | Fixtures include at least two distinct `detected_at` timestamps and at least two distinct `intensity_ppb` values. All intensities are finite and non-negative. All timestamps are timezone-aware UTC. | Mixed-data test; schema-conformance test |
| AC-6 | When `bbox=(min_latitude, min_longitude, max_latitude, max_longitude)` is supplied, only fixtures satisfying `min_latitude <= latitude <= max_latitude` and `min_longitude <= longitude <= max_longitude` are returned. Exact-boundary fixtures are included; outside fixtures are excluded. | Inside-box test; exact-boundary test; order-preservation test |
| AC-7 | When `since` is supplied, only fixtures with `detected_at >= since` are returned. Equality is included; older fixtures are excluded. | Since-filter test; exact-boundary timestamp test |
| AC-8 | `bbox` and `since` compose as a logical AND in one call; a fixture must satisfy both filters to be returned. | Combined-filter test |
| AC-9 | A filter matching nothing returns `[]`, not an error and not the full fixture set. | Empty-result test (spatial and temporal) |
| AC-10 | Invalid `bbox` inputs and naive `since` still raise through `MockNogietAdapter.fetch_hotspots`, proving the adapter cannot bypass 0a validation. | Inherited-validation tests |
| AC-11 | The module docstring states: this is a demonstration adapter; it does not integrate with NOGIET; NOGIET is a public platform built by SDN with Global Methane Hub support and transferred to NUPRC and NMDPRA at no cost; Valoris has no role in its development or operation. | Docstring-content test |
| AC-12 | Only the two implementation files in section 5 are created. `base.py`, `Hotspot`, and `detection/__init__.py` are untouched. No network, filesystem, or database I/O. Unit tests are marked `pytest.mark.unit`; the full backend suite remains green. | `git status --short`; full-suite run; code review |

---

## 4. Files to modify

**None.** No existing source, test, config, migration, route, or frontend file is touched. `backend/src/odrm/detection/base.py`, `backend/src/odrm/detection/__init__.py`, and all 0a tests remain unchanged.

---

## 5. Files to create

Implementation files (exactly two):

| File | Purpose |
|---|---|
| `backend/src/odrm/detection/mock_nogiet.py` | `MockNogietAdapter(DetectionSource)`, module-level fixture tuple, `_fetch_hotspots` filtering, required disclaimer docstring |
| `backend/tests/detection/test_mock_nogiet_adapter.py` | Unit tests for inheritance, fixtures, filtering, combination, empty results, inherited validation, and docstring content |

Governance artifact created at this gate (not an implementation file):

| File | Purpose |
|---|---|
| `docs/SPRINT_10B_PLAN.md` | This Phase 2 plan; the only file created before Phase 4 authorization |

**Export decision (CTO):** `MockNogietAdapter` is imported directly as `from odrm.detection.mock_nogiet import MockNogietAdapter`. It is **not** added to `odrm.detection.__init__`. It is a development/test adapter, not public API. `backend/src/odrm/detection/__init__.py` stays exactly as committed in 0a:

```python
from odrm.detection.base import DetectionSource, Hotspot

__all__ = ["DetectionSource", "Hotspot"]
```

This keeps the 0b implementation diff to exactly two files.

---

## 6. Technical design

### 6.1 Module structure

`backend/src/odrm/detection/mock_nogiet.py`:

- Module docstring with the required disclaimer.
- Imports: `datetime` from `datetime`; `DetectionSource` and `Hotspot` from `odrm.detection.base`.
- `_SOURCE = "mock_nogiet"` constant.
- `_FIXTURES: tuple[Hotspot, ...]` — six module-level `Hotspot` instances constructed once at import, so schema violations fail fast.
- `MockNogietAdapter(DetectionSource)` with `_fixtures: tuple[Hotspot, ...] = _FIXTURES` and only `_fetch_hotspots` implemented.

No constructor, no provider settings, no HTTP client, no filesystem access, no clock reads, no randomness.

### 6.2 Fixture data

Six synthetic fixtures at approximate real Niger Delta locations. Coordinates are demonstration values rounded to four decimal places; they are not survey measurements.

| ID | Approx. location | Latitude | Longitude | `intensity_ppb` | `detected_at` (UTC) |
|---|---|---|---|---|---|
| `mock-nogiet-001` | Port Harcourt (Trans-Amadi) | 4.8156 | 7.0498 | 2450.0 | 2026-01-05T09:30:00Z |
| `mock-nogiet-002` | Okrika | 4.7400 | 7.0833 | 3120.0 | 2026-01-12T14:15:00Z |
| `mock-nogiet-003` | Eleme | 4.7833 | 7.1167 | 1920.0 | 2026-01-20T06:45:00Z |
| `mock-nogiet-004` | Onne | 4.7167 | 7.1500 | 4600.0 | 2026-02-02T18:00:00Z |
| `mock-nogiet-005` | Woji | 4.8167 | 7.0333 | 2280.0 | 2026-02-10T11:20:00Z |
| `mock-nogiet-006` | Choba | 4.8833 | 6.9000 | 5210.0 | 2026-02-18T07:05:00Z |

Fixture invariants:

- All six fields populated; no nulls.
- `source == "mock_nogiet"` for every fixture.
- Latitude range `4.7167..4.8833`, longitude range `6.9000..7.1500` — the Port Harcourt / Okrika / Eleme / Onne / Woji / Choba area around 4.8, 7.0.
- Intensities are finite, non-negative, and varied: `1920.0`, `2280.0`, `2450.0`, `3120.0`, `4600.0`, `5210.0`.
- Timestamps are timezone-aware UTC and span 2026-01-05 through 2026-02-18, with no duplicate dates.
- IDs are unique and stable.

The fixture spread is deliberate: it supports strict-subset `bbox` tests, strict-subset `since` tests, exact-boundary tests, a combined-filter test, and empty-result tests without inventing extra fixtures.

### 6.3 Determinism (CTO decision)

- `_FIXTURES` is a module-level tuple of already-validated `Hotspot` instances.
- `MockNogietAdapter._fixtures` references that tuple.
- `_fetch_hotspots` returns `list(self._fixtures)` (or a filtered `list(...)` of the same instances) per call.
- `Hotspot` is **not** re-constructed on each call. No deep copies, no random generation, no `datetime.now()`.
- The tuple and its members are treated as read-only. Tests must not mutate returned `Hotspot` objects. This is an accepted trade-off for a test adapter; a production adapter would need a stronger immutability policy.
- Repeated calls return equal data in the same order, while each call returns a distinct list object.

### 6.4 Filtering logic

`_fetch_hotspots` receives inputs already validated by `DetectionSource.fetch_hotspots` at `backend/src/odrm/detection/base.py:55-63`. It does not re-validate `bbox` or `since`; it only applies inclusive comparisons.

Design sketch (not implementation):

```python
class MockNogietAdapter(DetectionSource):
    _fixtures: tuple[Hotspot, ...] = _FIXTURES

    async def _fetch_hotspots(
        self,
        *,
        bbox: tuple[float, float, float, float] | None = None,
        since: datetime | None = None,
    ) -> list[Hotspot]:
        hotspots = self._fixtures
        if bbox is not None:
            min_latitude, min_longitude, max_latitude, max_longitude = bbox
            hotspots = tuple(
                hotspot
                for hotspot in hotspots
                if min_latitude <= hotspot.latitude <= max_latitude
                and min_longitude <= hotspot.longitude <= max_longitude
            )
        if since is not None:
            hotspots = tuple(
                hotspot for hotspot in hotspots if hotspot.detected_at >= since
            )
        return list(hotspots)
```

Semantics:

- No filters: all six fixtures, in declaration order.
- `bbox` only: inclusive latitude and longitude bounds; exact edges included.
- `since` only: inclusive lower bound; equality included.
- Both: sequential AND filtering; order preserved.
- No match: empty list.
- `bbox` tuple order is the 0a contract: `(min_latitude, min_longitude, max_latitude, max_longitude)`.
- The adapter assumes the 0a validator has already rejected wrong lengths, non-finite values, out-of-range coordinates, inverted bounds, and naive `since`.

### 6.5 Required module docstring

Draft content (must include every required statement):

```python
"""Demonstration NOGIET-style detection adapter with synthetic fixtures.

This is a demonstration adapter. It does not integrate with NOGIET and performs
no network, filesystem, or database I/O. NOGIET is a public methane tracking
platform built by the Stakeholder Democracy Network (SDN) with Global Methane
Hub support and transferred to NUPRC and NMDPRA at no cost. Valoris has no role
in NOGIET's development or operation.

The fixture hotspots are synthetic, schema-conformant demonstration data. They
are not real observations and must not be represented as regulatory or
scientific measurements.
"""
```

Required phrases verified by test: "demonstration adapter", "does not integrate with NOGIET", "NUPRC", "NMDPRA", "SDN", "at no cost", "Valoris has no role".

### 6.6 No `BBox`

Confirmed: 0b does not define, import, or export `BBox`. `_require_bbox_valid` at `backend/src/odrm/detection/base.py:21-46` already guarantees tuple length, finite values, coordinate ranges, and `min <= max` ordering before the hook is called. Inline `min <= value <= max` comparisons are sufficient. A future real-data adapter that needs polygons or richer geometry adds `BBox` in its own deliverable with its own review gate.

### 6.7 Inherited validation, no override

`MockNogietAdapter` defines `_fetch_hotspots` only. `fetch_hotspots` remains `DetectionSource.fetch_hotspots`, so invalid `bbox` and naive `since` fail before the adapter's filtering code runs. Tests assert both the absence of an override and the preserved error behavior.

### 6.8 Conventions

- Python 3.11+, Pydantic v2.
- Typed signatures; `mypy` strict-compatible.
- `pytestmark = pytest.mark.unit`; async tests use the repo's `asyncio_mode = "auto"`.
- No new dependencies.
- Ruff line length 100; import sorting per repo config.

---

## 7. TDD test plan

Test module: `backend/tests/detection/test_mock_nogiet_adapter.py`.

Test constants (module level):

- `BBOX_PH_WOJI = (4.80, 7.02, 4.82, 7.06)` — expected IDs `mock-nogiet-001`, `mock-nogiet-005`.
- `BBOX_BOUNDARY = (4.8156, 7.0498, 4.8156, 7.0498)` — point box around fixture 001.
- `BBOX_COMBINED = (4.70, 7.10, 4.90, 7.20)` — expected IDs `mock-nogiet-003`, `mock-nogiet-004`.
- `SINCE_MID = datetime(2026, 1, 15, tzinfo=UTC)` — expected IDs `003`, `004`, `005`, `006`.
- `SINCE_EQUAL_004 = datetime(2026, 2, 2, 18, 0, tzinfo=UTC)` — expected IDs `004`, `005`, `006`.
- `SINCE_COMBINED = datetime(2026, 2, 1, tzinfo=UTC)` — combined with `BBOX_COMBINED`, expected ID `004` only.
- `EMPTY_BBOX = (0.0, 0.0, 1.0, 1.0)` and `FUTURE_SINCE = datetime(2027, 1, 1, tzinfo=UTC)`.

| Test | AC | Assertion |
|---|---|---|
| `test_adapter_is_detection_source_subclass` | AC-1 | `issubclass(MockNogietAdapter, DetectionSource)` |
| `test_adapter_does_not_override_fetch_hotspots` | AC-1 | `"fetch_hotspots" not in MockNogietAdapter.__dict__`; `MockNogietAdapter.fetch_hotspots is DetectionSource.fetch_hotspots`; `"_fetch_hotspots" in MockNogietAdapter.__dict__`; hook is a coroutine function |
| `test_default_fetch_returns_at_least_five_hotspots` | AC-2 | Awaited default result is a `list`, length `>= 5`, every item is `Hotspot` |
| `test_every_fixture_has_mock_nogiet_source` | AC-3 | Every fixture `source == "mock_nogiet"` |
| `test_fixtures_use_niger_delta_coordinates` | AC-4 | Every fixture within `4.0 <= latitude <= 5.5` and `6.5 <= longitude <= 7.5`; at least one within 0.1 degrees of `(4.8, 7.0)` |
| `test_fixtures_have_mixed_timestamps_and_intensities` | AC-5 | At least two distinct timestamps and two distinct intensities; all finite, non-negative; all timestamps timezone-aware |
| `test_fixtures_are_schema_conformant_with_no_nulls` | AC-5 | Every fixture is `Hotspot`; `set(model_dump())` is exactly the six fields; no field is `None`; IDs unique; `Hotspot.model_validate(h.model_dump()) == h` |
| `test_bbox_filter_returns_only_hotspots_inside_box` | AC-6 | `fetch_hotspots(bbox=BBOX_PH_WOJI)` returns exactly IDs `001`, `005` |
| `test_bbox_filter_includes_exact_boundary_hotspots` | AC-6 | Point box at fixture 001's coordinates returns exactly `001` |
| `test_since_filter_returns_only_hotspots_at_or_after_since` | AC-7 | `fetch_hotspots(since=SINCE_MID)` returns exactly IDs `003`, `004`, `005`, `006` |
| `test_since_filter_includes_exact_boundary_timestamp` | AC-7 | `fetch_hotspots(since=SINCE_EQUAL_004)` includes fixture `004` plus later fixtures; excludes earlier ones |
| `test_bbox_and_since_filters_combine` | AC-8 | `fetch_hotspots(bbox=BBOX_COMBINED, since=SINCE_COMBINED)` returns exactly ID `004` |
| `test_filters_can_return_empty_list` | AC-9 | Far-away bbox returns `[]`; future `since` returns `[]`; combined non-match returns `[]` |
| `test_invalid_bbox_is_rejected_by_inherited_validation` | AC-10 | Parametrized wrong-length, inverted, and out-of-range bboxes raise `ValueError` through the adapter |
| `test_naive_since_is_rejected_by_inherited_validation` | AC-10 | Naive `since` raises `ValueError` with exact message `"since must be timezone-aware"` |
| `test_module_docstring_contains_required_disclaimers` | AC-11 | Lowercased module docstring contains all required phrases listed in section 6.5 |
| `test_repeated_calls_are_deterministic_and_return_new_lists` | AC-2, design | Two default calls compare equal, preserve order, and are distinct list objects |
| `test_filtered_results_preserve_fixture_order` | AC-6, AC-7 | Filtered IDs follow declaration order |

Every acceptance criterion has at least one test. AC-12 is verified by `git status --short`, code review, and the full-suite run rather than by a unit test.

### Commands

Failing-first (after writing the test, before the adapter exists):

```powershell
pytest backend/tests/detection/test_mock_nogiet_adapter.py -q
```

Expected failure: `ModuleNotFoundError` for `odrm.detection.mock_nogiet` (a real import failure, not a syntax error).

Passing and regression:

```powershell
pytest backend/tests/detection/test_mock_nogiet_adapter.py -q
pytest backend/tests -q
ruff check backend/src/odrm/detection/mock_nogiet.py backend/tests/detection/test_mock_nogiet_adapter.py
mypy backend/src/odrm/detection/mock_nogiet.py
```

Phase 4 evidence must include the real failing output, the passing output, the tail of the full-suite run, and the lint/typecheck results.

---

## 8. Commit message

```
feat(detection): add mock NOGIET-style detection adapter

- Add MockNogietAdapter with deterministic Niger Delta fixture hotspots
- Filter fixtures by inclusive bbox and since bounds via the inherited template
- Document that the adapter is a demonstration and is not affiliated with NOGIET
- Add unit tests for fixtures, filtering, combination, and inherited validation
```

Commit protocol:

- This Phase 2 plan is committed separately after CTO approval as `docs(sprint-10): add 0b implementation plan`.
- The 0b implementation commit contains only the two files listed in section 5 and uses the message above.
- One implementation commit per deliverable; no batching across deliverables.
- Before the implementation commit, `git status --short` must show only the two allowed implementation files (the plan is already committed).
- The implementation commit hash is reported for the Sprint 10 report.

---

## 9. Audit protocol

### Phase 2 gate

- This plan exists at `docs/SPRINT_10B_PLAN.md` and is the only new file at this gate.
- All required sections are present: goal, deliverables, twelve acceptance criteria, files to create, files to modify, technical design, TDD test plan, commit message, audit protocol, out-of-scope list.
- The two implementation files are named explicitly.
- The export decision and fixture-determinism decision are recorded.
- No implementation code, test code, or test run exists.

### Phase 3 review gate

- The CTO reviews this plan and approves it with the exact phrase `AUTHORIZED: Sprint 10 0b implementation phase`.
- Every AC has at least one test.
- The plan matches the approved Phase 1 constitution: no `BBox`, no `__init__.py` export, no `base.py` or `Hotspot` changes, no real-data integration.

### Phase 4 implementation audit

- Failing-first output is a real import failure.
- Adapter tests pass.
- Full backend suite passes with no regressions.
- Ruff and mypy pass for the new files.
- `git status --short` shows only the two allowed implementation files before the implementation commit.
- The implementation commit message matches section 8.
- The commit hash is reported for the Sprint 10 report.

### Phase 5

Deferred until all Sprint 10 deliverables pass; `docs/SPRINT_10_REPORT.md` will cite this deliverable's commit hash and test counts.

---

## 10. Out of scope

- FastAPI routes, response schemas, dependency injection, auth, or rate limiting
- Database models, migrations, or role changes
- Frontend, dashboard, or map rendering
- Public-good whitelist, Merkle audit trail, benchmark publication, or regulatory dashboard wiring
- The `BBox` value object and richer geometry validation
- Real-data integration, NOGIET API access, satellite ingestion, or any HTTP client
- Provider configuration: environment variables, API keys, URLs, caching, retries, or polling
- Changes to `backend/src/odrm/detection/base.py` or the `Hotspot` schema
- Changes to `backend/src/odrm/detection/__init__.py`
- ML training/inference, LangChain tools, LLM calls, or agent wiring
- CLI commands, scripts, Parquet generation, or dataset pipelines
- Sprint 10 report or Phase 5 activities

---

## 11. Definition of done

- [ ] `MockNogietAdapter` subclasses `DetectionSource` and implements only `_fetch_hotspots`.
- [ ] `fetch_hotspots` is not overridden.
- [ ] Default `fetch_hotspots()` returns at least five `Hotspot` fixtures.
- [ ] Every fixture has `source == "mock_nogiet"`.
- [ ] Fixtures use Niger Delta coordinates around 4.8, 7.0.
- [ ] Fixtures have mixed timestamps and intensities, no nulls, and valid types.
- [ ] `bbox` filtering is inclusive and works alone and with `since`.
- [ ] `since` filtering is inclusive and works alone and with `bbox`.
- [ ] Empty filters return `[]`.
- [ ] Inherited `bbox` and naive-`since` validation still raises through the adapter.
- [ ] The module docstring contains all required disclaimer statements.
- [ ] `MockNogietAdapter` is not exported from `odrm.detection.__init__`.
- [ ] Only the two implementation files are created; no existing file is modified.
- [ ] Adapter tests, full backend suite, ruff, and mypy pass.
- [ ] Implementation commit created with the message in section 8.
- [ ] Commit hash recorded for the Sprint 10 report.

---

## 12. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Shared mutable `Hotspot` fixtures could be mutated by a caller | Accepted CTO trade-off for a test adapter; fixtures are treated as read-only, no production caller exists, and tests must not mutate results |
| Fixture coordinates could be mistaken for real observations | Module docstring and fixture comments state the data is synthetic demonstration data; coordinates are approximate real locations, not survey measurements |
| Inclusive-boundary behavior could drift | Exact-boundary `bbox` and `since` tests pin `<=` and `>=` semantics |
| Naive fixture timestamps would break `since` comparison | All fixtures use timezone-aware UTC timestamps; a schema-conformance test asserts awareness |
| Adapter could accidentally override `fetch_hotspots` | Test asserts absence from `__dict__` and function identity with the base method |
| Fixture changes could silently break filter tests | Tests assert exact expected IDs for fixed boxes and cutoffs; fixture changes require deliberate test updates |

---

## 13. Skill compliance

- `cto-architect/SKILL.md`: this plan is a written file, no code is produced before approval, and every decision cites the 0a contract or the CTO's Phase 1 direction.
- `agentic-architect/SKILL.md`: fixtures are constructed through `Hotspot`, so they are valid JSON-schema outputs for a future `fetch_detection_hotspots` tool; no LLM or physics claims are introduced.
- `data-engineer/SKILL.md`: strict schema validation, no nulls, correct types, finite non-negative intensities, timezone-aware timestamps, deterministic fixture generation.
- `ml-scientist/SKILL.md`: not applicable; 0b contains no model training, inference, OOD handling, or serialized models.
- FastAPI library skill: not applicable; 0b contains no API surface.

---

## 14. Roadmap alignment

**Goal:** Provide the first concrete `DetectionSource` implementation so later API and agentic layers can be built against a stable, tested adapter contract without touching real provider data.

**Deliverables:** `MockNogietAdapter`, six deterministic Niger Delta fixtures, inclusive `bbox`/`since` filtering, disclaimer docstring, unit tests.

**Gate:** 0b is complete when every acceptance criterion has a passing test, the full backend suite is green, lint and typecheck pass, only the two allowed implementation files are committed, and the CTO approves the result. Real-data ingestion remains out of scope for Sprint 10.
