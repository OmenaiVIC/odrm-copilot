# Sprint 10 Plan - Deliverable 0a: `DetectionSource` Interface & `Hotspot` Schema

| | |
|---|---|
| Status | **Draft - awaiting CTO advisor approval** |
| Date | 2026-11-21 |
| Scope | Regulator-agnostic detection contract: six-field `Hotspot` schema, async `DetectionSource` interface, inline `bbox`/`since` validation |
| Dependency | Phase 1 Constitution approved |
| Approval phrase | `AUTHORIZED: Sprint 10 0a implementation phase` |

> **Planning gate:** this file is the Phase 2 deliverable for 0a. No implementation code, test code, or commits may be created until the CTO approves this plan with the exact phrase above.

> **Phase 2 correction record**
>
> - **Finding 1:** the plan now lives in `docs/SPRINT_10_PLAN.md`, not only in chat.
> - **Finding 2:** **Option A selected.** `BBox` is removed from 0a. `fetch_hotspots` accepts `bbox: tuple[float, float, float, float] | None` and validates it inline through `_require_bbox_valid`. The `BBox` value object and richer geometry validation move to 0b, where the need is evidenced.
> - **Minor 1:** the template-method pattern is documented in section 4.4 as a design decision and as one private method beyond the approved single-abstract-method contract.
> - **Minor 2:** the `allow_inf_nan=False` statement now describes behavior only; it no longer claims an unverified repo convention.
> - **Phase 3 note:** the naive-`since` test will assert the exact `ValueError` message `"since must be timezone-aware"`.

---

## 1. Goal

Establish the foundation for regulator-agnostic methane hotspot detection: a validated six-field `Hotspot` schema and an async `DetectionSource` abstraction that later adapters (starting with 0b's mock NOGIET-style adapter) can implement without any caller depending on a specific provider.

0a is foundation-only. It does not fetch data, define routes, touch the database, or render anything.

---

## 2. Deliverables

1. **`Hotspot` Pydantic model** with exactly six fields: `id`, `latitude`, `longitude`, `intensity_ppb`, `detected_at`, `source`.
2. **`DetectionSource` ABC** with an async `fetch_hotspots(*, bbox=None, since=None)` contract, inline `bbox` validation, a timezone-aware `since` rule, and an adapter hook for concrete sources.
3. **Package exports** from `odrm.detection`.
4. **Unit tests** covering the interface, schema, query validation, and boundary conditions.

The `BBox` value object is explicitly **not** part of 0a. It moves to 0b.

---

## 3. Acceptance criteria

| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | `DetectionSource` and `Hotspot` exist in `odrm.detection` | import + interface test |
| AC-2 | Any conforming subclass can be substituted without provider-specific caller logic | stub-subclass test |
| AC-3 | `fetch_hotspots` is asynchronous | `inspect.iscoroutinefunction` + awaited stub test |
| AC-4 | No NOGIET/NUPRC/NGFCP-specific fields, methods, or naming | code review; schema field test |
| AC-5 | The interface accepts optional `bbox: tuple[float, float, float, float] \| None` and `since: datetime \| None` parameters | signature test + stub-capture test |
| AC-6 | `Hotspot` declares exactly six fields; no confidence field | `model_fields` test + extra-field rejection test |
| AC-7 | Latitude, longitude, and intensity are range-validated; `bbox` tuple length, coordinate ranges, and ordering are validated inline; `since` is timezone-aware | parametrized validation tests |
| AC-8 | Abstract interface cannot be instantiated; concrete async subclass can be awaited | instantiation + await tests |
| AC-9 | Repo conventions honored: Pydantic v2, typed tests, `pytest.mark.unit`, no network | lint/test run |
| AC-10 | Only the four original code/test files plus this Phase 2 plan file are created or modified | `git status --short` |
| AC-11 | Full backend suite remains green | `pytest backend/tests -q` |

---

## 4. Technical design

### 4.1 Package layout

```
backend/src/odrm/detection/
    __init__.py      # public exports
    base.py          # Hotspot, DetectionSource, validation helpers

backend/tests/detection/
    __init__.py      # empty package marker
    test_source_interface.py
```

No existing module is imported or modified. `odrm.detection` is a new leaf package.

### 4.2 `Hotspot`

```python
class Hotspot(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    id: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    intensity_ppb: float = Field(ge=0)
    detected_at: datetime
    source: str
```

Contract notes:

- Exactly six fields. No `confidence`, no defaults, no optional fields.
- `extra="forbid"` enforces the six-field contract at parse time.
- `allow_inf_nan=False` prevents non-finite intensities from passing `ge=0`.
- `detected_at` remains a plain `datetime` in 0a, as approved. The timezone-aware rule applies to the query parameter `since`, not to this field.
- `source` is free-form attribution (for example, an adapter identifier); 0a does not constrain it to an enum.

### 4.3 Query contract: `bbox` tuple and `since`

`fetch_hotspots` accepts:

```python
bbox: tuple[float, float, float, float] | None = None
since: datetime | None = None
```

`bbox` tuple order is fixed and documented as:

```text
(min_latitude, min_longitude, max_latitude, max_longitude)
```

`_require_bbox_valid` validates the tuple inline:

```python
def _require_bbox_valid(
    bbox: tuple[float, float, float, float] | None,
) -> None:
    if bbox is None:
        return
    if len(bbox) != 4:
        raise ValueError(
            "bbox must contain exactly four values: "
            "(min_latitude, min_longitude, max_latitude, max_longitude)"
        )
    min_latitude, min_longitude, max_latitude, max_longitude = bbox
    for value in bbox:
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise ValueError("bbox values must be finite numbers")
    if not -90 <= min_latitude <= 90 or not -90 <= max_latitude <= 90:
        raise ValueError("bbox latitude must be between -90 and 90")
    if not -180 <= min_longitude <= 180 or not -180 <= max_longitude <= 180:
        raise ValueError("bbox longitude must be between -180 and 180")
    if min_latitude > max_latitude:
        raise ValueError("bbox min_latitude must be <= max_latitude")
    if min_longitude > max_longitude:
        raise ValueError("bbox min_longitude must be <= max_longitude")
```

`_require_timezone_aware` validates `since`:

```python
def _require_timezone_aware(value: datetime | None, *, field: str) -> None:
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        raise ValueError(f"{field} must be timezone-aware")
```

0a does not implement spatial or temporal filtering. It validates the query inputs and passes them to the adapter hook. 0b implements the filtering against fixture hotspots.

No `BBox` class is introduced in 0a.

### 4.4 `DetectionSource`

```python
class DetectionSource(ABC):
    async def fetch_hotspots(
        self,
        *,
        bbox: tuple[float, float, float, float] | None = None,
        since: datetime | None = None,
    ) -> list[Hotspot]:
        _require_bbox_valid(bbox)
        _require_timezone_aware(since, field="since")
        return await self._fetch_hotspots(bbox=bbox, since=since)

    @abstractmethod
    async def _fetch_hotspots(
        self,
        *,
        bbox: tuple[float, float, float, float] | None = None,
        since: datetime | None = None,
    ) -> list[Hotspot]:
        ...
```

**Design decision - template-method pattern:** `fetch_hotspots` is the public entry point; `_fetch_hotspots` is the abstract adapter hook. This adds one private method not in the approved contract. The benefit is that every adapter inherits the same `bbox` and `since` validation; the cost is one extra method in the interface. Concrete adapters implement `_fetch_hotspots`; callers use only `fetch_hotspots`.

Additional rationale:

- **Public method owns query validation.** `fetch_hotspots` enforces the approved `bbox` and `since` rules before delegating.
- **Adapter hook stays pure.** Concrete sources implement `_fetch_hotspots`; 0b will implement this hook to return filtered fixtures.
- **Keyword-only filters.** `bbox` and `since` are keyword-only, preventing positional-argument ambiguity across adapters.
- **Abstractness.** `_fetch_hotspots` is abstract, so `DetectionSource()` raises `TypeError` and every concrete source must implement the fetch behavior.
- **No provider-specific surface.** No NOGIET, NUPRC, NGFCP, API-key, URL, or fixture fields appear in the interface.

### 4.5 Exports

`backend/src/odrm/detection/__init__.py`:

```python
from odrm.detection.base import DetectionSource, Hotspot

__all__ = ["DetectionSource", "Hotspot"]
```

### 4.6 Validation behavior matrix

| Input | Result |
|---|---|
| Valid six-field hotspot | Accepted |
| `latitude = -90.01` or `90.01` | `ValidationError` |
| `longitude = -180.01` or `180.01` | `ValidationError` |
| `intensity_ppb = -0.01` | `ValidationError` |
| `intensity_ppb = inf` / `nan` | `ValidationError` |
| Extra `confidence` field | `ValidationError` |
| `bbox` with wrong length | `ValueError` |
| `bbox` with out-of-range latitude | `ValueError` |
| `bbox` with out-of-range longitude | `ValueError` |
| `bbox` with inverted latitude or longitude bounds | `ValueError` |
| `bbox` with non-finite values | `ValueError` |
| `fetch_hotspots(since=naive_datetime)` | `ValueError("since must be timezone-aware")` |
| `fetch_hotspots(since=aware_datetime)` | Delegates to hook |

---

## 5. Files to create

| File | Purpose |
|---|---|
| `docs/SPRINT_10_PLAN.md` | This Phase 2 plan; the only addition to the original 0a allowed list, mandated by CTO Finding 1 |
| `backend/src/odrm/detection/__init__.py` | Public exports for `DetectionSource` and `Hotspot` |
| `backend/src/odrm/detection/base.py` | Schema, interface, bbox validation, timezone validation |
| `backend/tests/detection/__init__.py` | Test package marker |
| `backend/tests/detection/test_source_interface.py` | Unit tests for all 0a criteria |

## 6. Files to modify

**None.** No existing source, test, config, migration, route, or frontend file is touched.

---

## 7. TDD test plan

Test module marker: `pytestmark = pytest.mark.unit`.

| Test | Criterion | Assertion |
|---|---|---|
| `test_hotspot_accepts_valid_six_field_payload` | AC-1, AC-6 | Constructs a valid hotspot and checks all six values |
| `test_hotspot_declares_exactly_six_fields` | AC-6 | `set(Hotspot.model_fields) == {...}` |
| `test_hotspot_rejects_extra_confidence_field` | AC-6 | `confidence=0.9` raises `ValidationError` |
| `test_hotspot_rejects_out_of_range_latitude` | AC-7 | Parametrized `-90.01`, `90.01` raise |
| `test_hotspot_rejects_out_of_range_longitude` | AC-7 | Parametrized `-180.01`, `180.01` raise |
| `test_hotspot_rejects_negative_intensity` | AC-7 | `-0.01` raises |
| `test_hotspot_rejects_non_finite_intensity` | AC-7 | `inf`, `-inf`, `nan` raise |
| `test_detection_source_cannot_be_instantiated` | AC-8 | `DetectionSource()` raises `TypeError` |
| `test_fetch_hotspots_is_async_and_exposes_filters` | AC-3, AC-5 | Coroutine function; signature has keyword-only `bbox`, `since` |
| `test_concrete_source_can_be_awaited` | AC-2, AC-8 | Stub subclass implements `_fetch_hotspots`; awaited result matches |
| `test_concrete_source_receives_filters` | AC-5 | Stub records the exact `bbox` tuple and `since` passed through |
| `test_fetch_hotspots_accepts_valid_bbox` | AC-5, AC-7 | Valid four-value tuple delegates successfully |
| `test_fetch_hotspots_rejects_bbox_with_wrong_length` | AC-7 | Three-value and five-value tuples raise `ValueError` |
| `test_fetch_hotspots_rejects_out_of_range_bbox_latitude` | AC-7 | Latitude values outside `[-90, 90]` raise `ValueError` |
| `test_fetch_hotspots_rejects_out_of_range_bbox_longitude` | AC-7 | Longitude values outside `[-180, 180]` raise `ValueError` |
| `test_fetch_hotspots_rejects_inverted_bbox_bounds` | AC-7 | `min > max` for latitude or longitude raises `ValueError` |
| `test_fetch_hotspots_rejects_non_finite_bbox_values` | AC-7 | `inf`, `-inf`, `nan` in the tuple raise `ValueError` |
| `test_fetch_hotspots_rejects_naive_since` | AC-7 | Exact message assertion: `str(exc_info.value) == "since must be timezone-aware"` |
| `test_fetch_hotspots_accepts_aware_since` | AC-7 | UTC-aware `datetime` delegates successfully |

The naive-`since` test must use `pytest.raises(ValueError) as exc_info` and assert the exact message, not merely that some `ValueError` was raised:

```python
with pytest.raises(ValueError) as exc_info:
    await StubSource().fetch_hotspots(since=datetime(2026, 1, 1))
assert str(exc_info.value) == "since must be timezone-aware"
```

### Commands

Failing-first:

```powershell
pytest backend/tests/detection/test_source_interface.py -q
```

Passing:

```powershell
pytest backend/tests/detection/test_source_interface.py -q
pytest backend/tests -q
```

Phase 4 evidence must include the real failing output (expected: `ModuleNotFoundError` for `odrm.detection`), the passing output, and the tail of the full-suite run.

---

## 8. Commit message

```
feat(detection): add DetectionSource interface and Hotspot schema

- Add regulator-agnostic async DetectionSource ABC with bbox/since contract
- Add six-field Hotspot model with coordinate and intensity validation
- Validate bbox tuples and timezone-aware since values at the interface
- Add unit tests for the interface, schema, and query validation
```

Commit protocol:

- The Phase 2 plan file is committed separately after CTO approval as `docs(sprint-10): add 0a implementation plan`.
- The 0a implementation commit contains only the four code/test files listed in section 5 and uses the message above.
- One implementation commit per deliverable; no batching across deliverables.
- Before the implementation commit, `git status --short` must show only the four allowed code/test files.

---

## 9. Audit protocol

### Phase 2 gate

- This plan file exists at `docs/SPRINT_10_PLAN.md`.
- Both blocking findings are resolved: the plan is a file, and `BBox` is removed in favor of the approved tuple contract.
- Both minor notes are addressed: the template-method decision is documented, and the `allow_inf_nan` claim is behavioral only.
- All required sections are present: goal, deliverables, acceptance criteria, files to create, files to modify, commit message, audit protocol.
- Commit messages are specific and scoped to 0a.

### Phase 3 review gate

- Exact test file and exact implementation file are presented.
- Every AC has at least one test.
- The naive-`since` test asserts the exact message.
- Implementation matches the approved contract exactly; no confidence field, no `BBox`, no API, no adapter.
- Only the allowed files are touched.

### Phase 4 implementation audit

- Failing output is a real import/assertion failure, not a syntax error.
- Passing output is fully green.
- Full-suite tail shows no regressions.
- `git status --short` shows only the four allowed code/test files before the implementation commit.
- Implementation commit message matches section 8.
- Commit hash is reported for the Sprint 10 report.

### Phase 5

Deferred until all seven Sprint 10 deliverables pass; `docs/SPRINT_10_REPORT.md` will cite this deliverable's commit hash and test counts.

---

## 10. Out of scope

- Mock NOGIET-style adapter and fixture data (0b)
- `BBox` value object and richer geometry validation (0b)
- FastAPI routes, response schemas, or dependency wiring
- Database models, migrations, or role changes (0c)
- Whitelist flow, Merkle audit trail, benchmark publication, dashboard wiring
- Real satellite/regulator data ingestion
- Confidence scoring or confidence fields
- Provider configuration, API keys, HTTP clients, caching, or retries
- Frontend or dashboard changes

---

## 11. Definition of done

- [ ] `Hotspot` has exactly six fields and no confidence field.
- [ ] `bbox` is accepted as a four-value tuple and validated inline.
- [ ] `DetectionSource` is abstract, async, pluggable, and regulator-agnostic.
- [ ] `since` is rejected when naive and accepted when timezone-aware.
- [ ] All 0a tests pass.
- [ ] `pytest backend/tests -q` passes with no regressions.
- [ ] Only the four code/test files plus the Phase 2 plan file are modified.
- [ ] Implementation commit created with the message in section 8.
- [ ] Commit hash recorded for the Sprint 10 report.

---

## 12. Risks and mitigations

| Risk | Mitigation |
|---|---|
| `bbox` tuple order is ambiguous | Order is fixed as `(min_latitude, min_longitude, max_latitude, max_longitude)` and pinned by tests |
| Template method adds a private adapter hook | Documented as a design decision; callers use only `fetch_hotspots`; 0b implements `_fetch_hotspots` |
| An adapter could override `fetch_hotspots` and bypass validation | Documented as the public entry point; 0b implements only the hook. Static enforcement is out of scope for 0a |
| `allow_inf_nan=False` is stricter than the minimal contract | Stated as behavior, not as an unverified convention; it prevents non-finite intensities from passing `ge=0` |
| Plan file commit boundary could be read as an extra commit | Proposed explicitly in section 8; CTO may revise before Phase 4 |

---

## 13. Roadmap alignment

**Goal:** Build the regulator-agnostic detection contract that later adapters and the public dashboard depend on, without integrating real data.

**Deliverables:** `DetectionSource` interface (pluggable, async), six-field `Hotspot` schema, inline `bbox`/`since` validation, unit tests.

**Gate:** 0a is complete when the interface, schema, and query validation have passing tests, the full suite is green, and only the allowed files are committed. Real-data ingestion remains out of scope.

**Agentic-layer connection:** `Hotspot` will become the JSON output schema for a future agent tool (`fetch_detection_hotspots`) in the agentic layer; the strict `extra="forbid"` is deliberate to prevent tool-call drift when that adapter is built.

---

## 14. Skill Compliance

0a was audited against the three applicable project skill files. `cto-architect/SKILL.md` is compliant: the plan is a written file, no code was produced before approval, and design decisions are evidence-based. `agentic-architect/SKILL.md` is compliant: 0a uses no LangChain, no LLM, and no tool calling; the skill applies to later sprints. `data-engineer/SKILL.md` is compliant: `Hotspot` is a strict schema with `extra="forbid"` and `allow_inf_nan=False`, with no nulls and no optional fields. The `ml-scientist` and FastAPI library skills are out of scope for 0a because 0a contains no ML and no API surface.
