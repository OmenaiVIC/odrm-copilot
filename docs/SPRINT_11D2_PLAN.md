# Sprint 11 D2 Plan - Merkle-Tree ESG Audit Trail

| | |
|---|---|
| Status | Draft - awaiting CTO Phase 2 approval |
| Date | 2026-11-24 |
| Deliverable | D2 (Merkle-tree evidence chain + Stellar integration design) |
| Baseline | `e39a850` (Sprint 11 plan), parent `06d969b` (Sprint 10 complete) |
| Authorization | `AUTHORIZED: Sprint 11 D2 implementation phase` (Phase 4 only) |
| Resolutions incorporated | Q1 canonical JSON, Q2 on-demand batching, Q3 service-minted `screening_id`, Q4 authenticated verify route, Q5 verify against owning batch |

No implementation code, test code, or file creation beyond this plan until the CTO
approves this document.

---

## 1. Goal

Make every TEA screening cryptographically tamper-evident before any chain exists.
Each successful `/api/v1/tea` and `/api/v1/report` screening is canonically hashed,
appended to an automatically rolled batch, and committed to a SHA-256 Merkle tree whose
root is stored off-chain with `anchor_status='pending'`. A verification endpoint returns
the sibling proof path for any recorded screening hash and confirms it against the root of
the batch that actually owns that leaf. D2 deliberately stops before Stellar: the Merkle
convention defined here is the byte-exact contract that D5's Soroban `store_root` and
`verify_hash` must reproduce.

---

## 2. Deliverables (restated from `docs/SPRINT_11_PLAN.md` section 2)

1. **Evidence row per screening.** Every successful `/api/v1/tea` call inserts one
   `screening_evidence` row containing `input_hash`, `output_hash`, `screening_hash`,
   `screening_id`, `batch_id`, `created_at`. Input and output are canonically serialized
   before hashing.
2. **Evidence row per report.** Every successful `/api/v1/report` screening inserts one
   row under the same schema. The report's volatile envelope (`report_id`,
   `generated_at`) is never hashed, so an identical screening hashes identically through
   both endpoints.
3. **Automatic batching.** A new `evidence_batches` row is created on demand when no
   batch exists, when the open batch reaches 100 leaves, or on the first leaf of a new
   UTC day. `merkle_root` is recomputed from the ordered leaves on every append;
   `anchor_status` defaults to `pending`.
4. **Verification endpoint.** `GET /api/v1/evidence/verify/{screening_hash}` returns the
   owning batch id, its root, the bottom-up sibling proof path, and a server-computed
   `verified` flag. Unknown hashes return a defined 404 envelope, never a 500.
5. **No on-chain anchoring.** D2 makes zero Stellar calls. All batches remain `pending`;
   the Soroban anchor job is D5.

---

## 3. Acceptance criteria mapped to tests

| ID | Criterion | Primary test(s) |
|---|---|---|
| D2-1 | A successful `/api/v1/tea` persists exactly one `screening_evidence` row with valid 64-hex SHA-256 values and `screening_hash = SHA-256(input_hash || output_hash)` (raw 32-byte concatenation). | `test_screening_produces_evidence_row`, `test_tea_creates_evidence_row` |
| D2-2 | A successful `/api/v1/report` persists one row under the same schema, with a service-minted `screening_id`; volatile report fields do not affect the hash. | `test_report_creates_evidence_row`, `test_canonical_hash_ignores_report_envelope` |
| D2-3 | Batches open and close on demand at 100 leaves or the first leaf of a new UTC day; `leaf_count` and `merkle_root` are correct and exactly one batch is open. | `test_batch_root_computation`, `test_batch_rollover_at_100_leaves`, `test_batch_rollover_on_new_utc_day` |
| D2-4 | The verify endpoint returns a valid proof for a known hash and a 404 `EVIDENCE_NOT_FOUND` envelope for an unknown hash; it verifies against the leaf's owning batch, not the newest batch; unauthenticated calls get 401. | `test_verify_valid_hash`, `test_verify_invalid_hash`, `test_evidence_api_verify_endpoint` |
| D2-5 | No anchoring occurs in D2; every batch stays `pending` and no service path writes `anchored_on_soroban` or `verified`. | `test_batch_anchoring_status_transitions` |
| AC-10 | Full backend suite, `ruff`, and `mypy` are clean; frontend gates unaffected by D2 but run at sprint level. | Phase 4 gate |

Supporting test: `test_evidence_chain_migration_upgrade_and_downgrade` (schema shape and
reversibility for migration `0004`).

---

## 4. Files to create (13)

```
backend/src/odrm/evidence/__init__.py
backend/src/odrm/evidence/models.py            # ScreeningEvidence, EvidenceBatch
backend/src/odrm/evidence/schemas.py           # EvidenceVerifyResponse
backend/src/odrm/evidence/repository.py        # EvidenceRepository, EvidenceBatchRepository
backend/src/odrm/evidence/service.py           # canonical hashing, Merkle tree, proof, rollover
backend/src/odrm/api/evidence.py               # verify router
backend/migrations/versions/0004_evidence_chain.py
backend/tests/evidence/__init__.py
backend/tests/evidence/test_merkle_service.py
backend/tests/evidence/test_evidence_api.py
backend/tests/db/test_evidence_chain_migration.py
docs/STELLAR_INTEGRATION.md
docs/SCF_MILESTONE_PLAN.md
```

## 5. Files to modify (4, plus one proposed test-harness deviation)

```
backend/src/odrm/api/routes.py        # call evidence service after successful /tea screening
backend/src/odrm/api/report.py        # call evidence service after successful /report screening
backend/src/odrm/main.py              # build EvidenceService, include evidence router, injectable repo
backend/migrations/env.py             # import odrm.evidence.models for metadata discovery
```

**Deviation requested (approval required): `backend/tests/conftest.py`.**
`test_settings` currently leaves `database_url` at the default `sqlite:///./odrm.db`, and
`create_app` does not create tables. The repo-root `odrm.db` exists but is 0 bytes, so the
first `/tea` evidence write would raise "no such table". Existing tests that call
`/tea` or `/report` (`test_tea_api.py`, `test_report_api.py`, `test_tea_flow.py`, etc.)
build apps from the shared `test_settings` fixture and would break through no fault of
their own. The minimal fix is confined to the harness:
- point `test_settings.database_url` at a session-scoped temp SQLite file;
- add a session-scoped autouse fixture that imports `odrm.evidence.models` and runs
  `Base.metadata.create_all(...)` once before any app is built.
No production module gains auto-DDL, and no existing assertion changes. If the CTO
rejects this deviation, D2 cannot keep the existing suite green without editing every
`create_app` call site.

---

## 6. Technical design

### 6.1 Database schema

`evidence_batches`:

| Column | Type | Constraints |
|---|---|---|
| `id` | `String(36)` | PK, default `uuid4` |
| `merkle_root` | `String(64)` | NOT NULL, `length(merkle_root) = 64` |
| `leaf_count` | `Integer` | NOT NULL, `leaf_count >= 1` |
| `created_at` | `DateTime(timezone=True)` | NOT NULL, app default `datetime.now(UTC)`, server default `CURRENT_TIMESTAMP` |
| `anchor_status` | `String(32)` | NOT NULL, default `pending`, CHECK in (`pending`, `anchored_on_soroban`, `verified`) |

Index: `ix_evidence_batches_created_at_id` on `(created_at, id)` for the latest-batch
lookup. There is no `closed_at` column in D2: the open batch is the newest batch, and a
batch is closed implicitly when a newer one opens. All batches remain `pending` until D5.

`screening_evidence`:

| Column | Type | Constraints |
|---|---|---|
| `id` | `String(36)` | PK, default `uuid4` |
| `screening_id` | `String(36)` | NOT NULL, indexed |
| `input_hash` | `String(64)` | NOT NULL, `length(input_hash) = 64` |
| `output_hash` | `String(64)` | NOT NULL, `length(output_hash) = 64` |
| `screening_hash` | `String(64)` | NOT NULL, `length(screening_hash) = 64`, non-unique index |
| `batch_id` | `String(36)` | NOT NULL, FK `evidence_batches.id` `ON DELETE RESTRICT`, indexed |
| `created_at` | `DateTime(timezone=True)` | NOT NULL, app default `datetime.now(UTC)`, server default `CURRENT_TIMESTAMP` |

Composite index `ix_screening_evidence_batch_leaf_order` on `(batch_id, created_at, id)`
for deterministic leaf ordering. `screening_hash` is intentionally **not unique**: the
same deterministic screening submitted twice must produce two rows (D2-1). Verification
resolves the earliest row by `(created_at, id)`; duplicated screening hashes are
interchangeable leaves and each has its own valid proof.

SQLite note: `length()` and CHECK constraints are supported. The migration must be
downgrade-safe on SQLite by dropping `screening_evidence` before `evidence_batches`.

### 6.2 Canonical hashing

```python
import hashlib
import json
from collections.abc import Mapping
from typing import Any

from odrm.api.schemas import TeaRequest, TeaResponse

CANONICAL_SEPARATORS = (",", ":")
VOLATILE_FIELDS = frozenset({"report_id", "generated_at", "timestamp"})


def canonical_json(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=CANONICAL_SEPARATORS,
        ensure_ascii=True,
    ).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compute_hashes(request: TeaRequest, response: TeaResponse) -> tuple[str, str, str]:
    input_payload = request.model_dump(mode="json")
    output_payload = response.model_dump(mode="json")

    if VOLATILE_FIELDS.intersection(input_payload) or VOLATILE_FIELDS.intersection(
        output_payload
    ):
        raise ValueError("Volatile envelope fields must never enter the evidence hash.")

    input_hash = sha256_hex(canonical_json(input_payload))
    output_hash = sha256_hex(canonical_json(output_payload))
    screening_hash = sha256_hex(bytes.fromhex(input_hash) + bytes.fromhex(output_hash))
    return input_hash, output_hash, screening_hash
```

This matches the existing canonical form in `backend/src/odrm/reporting/content.py:88-94`.
The `/report` hook hashes the `TeaRequest` and the `TeaResponse` returned by
`run_screening`, never `ReportData`; `report_id` and `generated_at` therefore cannot
affect `screening_hash`. No `orjson` dependency is introduced.

### 6.3 Merkle tree

Module-level constants (D5 must mirror these byte-for-byte):

```python
LEAF_PREFIX = b"\x00"
NODE_PREFIX = b"\x01"
```

- Leaf ordering: `ORDER BY created_at ASC, id ASC` within the batch. This is a total,
  reproducible order; a later leaf may sort before an earlier one, which is harmless
  because the root is recomputed on every append and proofs are derived on demand.
- Leaf node: `H(0x00 || screening_hash_bytes)`.
- Parent node: `H(0x01 || left || right)`.
- Odd node: promoted unchanged to the next level (no duplication of the last leaf).
- Root of a single leaf: its leaf node (not the raw `screening_hash`).
- `merkle_root` is stored as lowercase hex of the 32-byte root.
- Proof generation returns sibling nodes bottom-up, each lowercase hex; when a level has
  an odd trailing node and the target is that node, no sibling is emitted for that level.
- Verification recomputes `leaf_node`, folds the proof using index parity at each level,
  and compares the result to the stored root.

Reference implementation shape:

```python
def leaf_node(screening_hash: str) -> bytes:
    return hashlib.sha256(LEAF_PREFIX + bytes.fromhex(screening_hash)).digest()


def parent(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(NODE_PREFIX + left + right).digest()


def merkle_root(screening_hashes: Sequence[str]) -> str:
    if not screening_hashes:
        raise ValueError("cannot build a Merkle root for an empty batch")
    level = [leaf_node(h) for h in screening_hashes]
    while len(level) > 1:
        next_level = [
            parent(level[i], level[i + 1]) for i in range(0, len(level) - 1, 2)
        ]
        if len(level) % 2:
            next_level.append(level[-1])
        level = next_level
    return level[0].hex()
```

Domain separation prevents an internal node value from being presented as a leaf.
The D5 contract must use the same two prefixes; this is recorded in
`docs/STELLAR_INTEGRATION.md`.

### 6.4 Batch rollover and transaction boundary

`EvidenceService.record_screening(request, response, *, now=None)`:

1. `now = now or datetime.now(UTC)`; compute the three hashes.
2. Open one unit of work (single SQLAlchemy `Session`/transaction).
3. On PostgreSQL, take `pg_advisory_xact_lock(<fixed key>)` before the latest-batch
   query. This closes the "no batch exists yet" race that `FOR UPDATE` cannot cover
   because there is no row to lock. On SQLite the call is skipped.
4. `SELECT ... ORDER BY created_at DESC, id DESC LIMIT 1 FOR UPDATE` the latest batch.
5. Roll over if any of: no batch, `leaf_count >= 100`, or
   `now.date() > latest.created_at.astimezone(UTC).date()`.
6. If rolling over, create the new batch with a provisional root of the incoming leaf
   (satisfies `merkle_root NOT NULL`) and insert the evidence row. Otherwise insert the
   evidence row against the existing batch.
7. Re-read all leaf hashes for the batch in canonical order, compute the root and count,
   and update `evidence_batches.merkle_root` / `leaf_count`.
8. Commit. Return a record containing `screening_id`, `screening_hash`, `batch_id`.

Every append recomputes the full root. With a 100-leaf cap this is at most 100 SHA-256
operations per write: negligible and avoids incremental-tree state drift.

`FOR UPDATE` and the advisory lock are no-ops on SQLite; tests are single-threaded, so
serialization is inherent. This behavior is documented in the repository docstring and
in `docs/STELLAR_INTEGRATION.md`.

### 6.5 Verify endpoint

Router: `backend/src/odrm/api/evidence.py`

```python
router = APIRouter(dependencies=[Depends(get_current_user)])
```

`GET /api/v1/evidence/verify/{screening_hash}` with `screening_hash` constrained to
`^[0-9a-f]{64}$` (invalid shapes get FastAPI's 422).

Response model:

```python
class EvidenceVerifyResponse(BaseModel):
    screening_hash: str
    batch_id: str
    merkle_root: str
    proof_path: list[str]
    verified: bool
```

Behavior:

- Look up the earliest `screening_evidence` row by `(created_at, id)`.
- Unknown hash: HTTP 404 with body
  `{"detail": {"code": "EVIDENCE_NOT_FOUND", "message": "No evidence exists for this screening hash."}}`.
  The `detail` wrapper is FastAPI's standard envelope; the code/message pair is stable
  for the workbook and future clients.
- Row without a batch (structurally impossible under the NOT NULL FK, handled
  defensively): HTTP 409 `{"detail": {"code": "EVIDENCE_NOT_BATCHED", ...}}`.
- Known row: load the owning batch's ordered leaves, locate the row by `id` (not by hash,
  because duplicates are legal), build the proof, recompute the root, and return 200.
  `verified` is true only if both the recomputed root equals the stored root and the
  proof folds to that root. A mismatch logs at ERROR and returns `verified: false`, not a
  500: the endpoint's job is to report verification, and silent success is the only
  unacceptable outcome.
- No anchoring, no Stellar calls: D2 reads only local tables.
- Verification is fail-closed (unknown hash = 404), unlike the write path: the
  `X-Evidence-Status` header contract applies only to `/tea` and `/report` (section 6.6).

**Additive-fields proposal (approval requested):** include `leaf_index: int` and
`leaf_count: int` alongside the five required fields. A flat `proof_path` of sibling
hashes is not independently verifiable without the leaf position and batch width. If the
CTO requires strict five-field parity, the server-side `verified` flag remains
authoritative and the two additive fields are dropped; the D5 `verify_hash` signature
will then need its own direction encoding.

### 6.6 `/tea` and `/report` hooks

`backend/src/odrm/api/routes.py`, in `tea()`: replace the direct `return run_screening(...)`
with an assignment inside the existing `try`, then call
`req.app.state.evidence_service.record_screening(request, response)` after the
error-mapping block and before `return response`. Only successful screenings are
recorded; a model or TEA failure produces no evidence row, consistent with "screening
evidence" meaning a completed screening. Evidence persistence is **fail-open**: the
call is wrapped in `try/except Exception`, a failure is logged at WARNING, and the
screening response is still returned. The response carries `X-Evidence-Status:
recorded` on success and `X-Evidence-Status: failed` on failure. No 503 is raised: the
TEA result is the user's primary artifact, and D5's anchor job can retry failed
evidence writes but cannot reconstruct a lost screening.

`backend/src/odrm/api/report.py`, in `report()`: after the existing `run_screening`
`try/except` and **before** `generated_at` and PDF rendering, call
`req.app.state.evidence_service.record_screening(request, screening)` under the same
fail-open wrapper, and add `X-Evidence-Status` (`recorded` or `failed`) to the PDF
response headers. The screening is real even if PDF rendering later fails, and AC-2 is
about the screening, not the PDF artifact.

`backend/src/odrm/main.py`:

- `create_app(..., evidence_repository: EvidenceRepository | None = None)`.
- Build `SqlAlchemyEvidenceRepository(session_factory)` unless injected, store it and
  `EvidenceService(repository)` on `app.state`.
- `app.include_router(evidence_router, prefix="/api/v1", tags=["evidence"])`.

This follows the existing whitelist wiring in `main.py:53-57`. Injection keeps the
evidence API tests isolated from the session app.

### 6.7 Repository and service shape

- `repository.py` defines `EvidenceRepository` / `EvidenceBatchRepository` protocols and
  SQLAlchemy implementations. The write path exposes one unit-of-work context manager so
  batch lock, leaf insert, and root update share a transaction. Read helpers return
  dataclass records, not ORM objects, matching `whitelist/repository.py`.
- `service.py` owns canonicalization, hashing, Merkle construction, proof generation,
  rollover policy, and the `now` injection seam. It depends on repository protocols only.
- `schemas.py` holds `EvidenceVerifyResponse`; models hold no Pydantic logic.
- `EvidenceLedgerUnavailable` and `EvidenceNotFoundError` are defined in the module that
  raises them (service/repository) and mapped in the routers.

### 6.8 Risks and edge cases

- Duplicate screening hashes: allowed by design; proof lookup is by row identity.
- Clock skew: rollover uses `>` on UTC dates, so a backwards clock never reopens a closed
  day; a forwards jump rolls over once.
- Empty batch: impossible (`leaf_count >= 1`); `merkle_root` on empty input raises.
- SQLite lacks `FOR UPDATE`; concurrency safety is Postgres-only and documented.
- Evidence write failure is fail-open: the screening result is returned with
  `X-Evidence-Status: failed` and a WARNING log. D5's anchoring job reconciles failed
  writes; a lost screening result cannot be reconstructed.
- D5 must mirror the prefix constants and decide how proof direction is conveyed; this is
  flagged in the integration document rather than silently deferred.

---

## 7. TDD test plan

The six required D2 test names, mapped to ACs:

| Test | File | AC | What it proves |
|---|---|---|---|
| `test_screening_produces_evidence_row` | `test_merkle_service.py` | D2-1 | One row per screening; all hashes 64-hex; `screening_hash` equals the explicit recomputation over raw bytes. |
| `test_batch_root_computation` | `test_merkle_service.py` | D2-3 | Root for 1, 2, 3, and 4 leaves matches an independent reference implementation in the test; odd promotion is covered. |
| `test_verify_valid_hash` | `test_merkle_service.py` | D2-4 | Proof for each leaf in a 5-leaf batch folds to the stored root. |
| `test_verify_invalid_hash` | `test_merkle_service.py` | D2-4 | Unknown hash raises `EvidenceNotFoundError`; tampered proof or root yields `verified = false`. |
| `test_batch_anchoring_status_transitions` | `test_merkle_service.py` | D2-5 | New and rolled batches are `pending`; no service path writes an anchored status. |
| `test_evidence_api_verify_endpoint` | `test_evidence_api.py` | D2-4 | 200 shape and proof for a real screening; 404 envelope for unknown; 401 unauthenticated; invalid hash shape 422. |

Additional coverage required by the AC table:

| Test | File | AC |
|---|---|---|
| `test_tea_creates_evidence_row` | `test_evidence_api.py` | D2-1 (HTTP integration) |
| `test_report_creates_evidence_row` | `test_evidence_api.py` | D2-2 |
| `test_canonical_hash_ignores_report_envelope` | `test_merkle_service.py` | D2-2 |
| `test_batch_rollover_at_100_leaves` | `test_merkle_service.py` | D2-3 |
| `test_batch_rollover_on_new_utc_day` | `test_merkle_service.py` | D2-3 |
| `test_evidence_chain_migration_upgrade_and_downgrade` | `test_evidence_chain_migration.py` | Schema + AC-10 |

Test order (red-green per test, no batch implementation):

1. Pure Merkle/canonicalization tests (no DB): `test_batch_root_computation`,
   `test_verify_valid_hash`, `test_verify_invalid_hash`,
   `test_canonical_hash_ignores_report_envelope`.
2. Repository/service with a per-test temp SQLite database: `test_screening_produces_evidence_row`,
   `test_batch_anchoring_status_transitions`, rollover tests.
3. HTTP hooks and verify route with an app whose evidence repository is injected:
   `test_tea_creates_evidence_row`, `test_report_creates_evidence_row`,
   `test_evidence_api_verify_endpoint`.
4. Migration test last: upgrade `0003 -> 0004`, inspect tables/columns/FKs/indexes/checks,
   downgrade `0004 -> 0003`.

Fixtures for 2 and 3 create the schema explicitly with `Base.metadata.create_all` on a
temp file URL; they never touch `./odrm.db` and never depend on the shared session app.

---

## 8. Commit message

```
feat(evidence): add Merkle-tree screening evidence chain and Stellar integration design
```

One commit after all D2 gates pass. It includes the two docs from D2, since the sprint
plan scopes them to this deliverable. No push until the CTO Phase 4 audit is requested;
per sprint protocol, commit then push then stop for CTO audit.

---

## 9. Audit protocol (Phases 3 and 4)

**Phase 3 - Review gate (no disk writes).**
For each file, show the exact proposed contents in chat, in this order: models,
repository, service, schemas, router, migration, `main.py` delta, route deltas, tests,
docs. The CTO audits and requests revisions. Nothing is written to disk and no tests run.
Phase 3 ends when the CTO explicitly authorizes Phase 4.

**Phase 4 - Implementation (TDD).**
Per test, in the order in section 7:

1. Write the failing test only.
2. Run the focused command and paste the failure:
   `.\.venv\Scripts\python.exe -m pytest backend/tests/evidence/test_merkle_service.py::<test> -q`
3. Implement the minimum production code.
4. Re-run and paste the pass.
5. Move to the next test. No implementation ahead of a failing test.

Evidence-write failure tests must assert the primary response still succeeds with
`X-Evidence-Status: failed` and a WARNING log. There is no 503 path for evidence writes.

After all D2 tests pass, run the full gates and paste each result:

```
.\.venv\Scripts\python.exe -m pytest backend/tests -q
.\.venv\Scripts\python.exe -m pytest backend/tests/evidence backend/tests/db/test_evidence_chain_migration.py -q
.\.venv\Scripts\python.exe -m ruff check backend/src backend/tests
.\.venv\Scripts\python.exe -m mypy
```

Frontend is untouched by D2; `npm run typecheck`, `npm run lint`, and `npm run build`
remain sprint-level gates (AC-10) and are not re-run per D2 commit unless the CTO asks.

Then: commit with the section 8 message, push, and stop for the CTO audit. Do not begin
D2a, D3, D4, or D5.

---

## 10. Out of scope for D2

- Soroban contract, Testnet deployment, and the anchor job (D5)
- Stellar asset issuance, SAC mint/transfer, freeze/clawback flows (D5 and post-SCF)
- Mainnet deployment (post-SCF)
- Excel workbook and export script (D2a)
- Benchmark release and reproduction guide (D3)
- Detection hotspot panel and dashboard wiring (D4)
- Any change to Sprint 10 deliverables 0a, 0b, 0c, or D1
- RWA marketplace, secondary trading, or credit pricing logic
- NUPRC/NOGIET live integration or satellite ingestion
- Unauthenticated public verification (future deliverable per Q4)
- Power BI, hosted deployment, and multi-tenant scoping
