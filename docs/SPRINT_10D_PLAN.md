# Sprint 10 Plan - Deliverable 1: Public-Good Whitelist

| | |
|---|---|
| Status | **Draft - awaiting Phase 3 CTO review** |
| Date | 2026-11-23 |
| Scope | Add the `public_good` role, a reversible `whitelist_applications` migration, authenticated apply/status endpoints, admin review endpoints, and the two requested frontend pages |
| Dependency | Sprint 10 D1 Phase 1 approved by the CTO; Phase 1 base commit `85ad77f`; Phase 0a/0b/0c complete |
| Approval phrase | `AUTHORIZED: Sprint 10 D1 implementation phase` |

> **Planning gate:** this file is the Phase 2 deliverable for D1. No implementation code, test code, migration code, frontend code, or test run may be created until the CTO approves this plan with the exact phrase above.

> **Phase 1 decisions incorporated:** D-1 module boundary approved; D-2 one current-state row per user with reopen-on-reapply approved; D-3 `decision_reason` column approved; D-4 own-status endpoint approved; D-5 admin ineligibility approved.

> **Phase 2 file boundary:** `docs/SPRINT_10D_PLAN.md` is the only file created or modified in Phase 2. The working tree must be clean of other changes before Phase 4 authorization.

---

## 1. Goal

Implement the Public-Good Whitelist flow so an authenticated `commercial` or `viewer` user can apply for the `public_good` role, an `admin` can review applications, and approval atomically changes the applicant's role to `public_good`.

The flow covers the role vocabulary, one reversible migration, five whitelist endpoints, backend service/repository logic, the user application page, the admin review page, and their tests. It does not change the existing prediction, chat, report, detection, or sprint-0a/0b/0c behavior.

---

## 2. Deliverables

1. **Expanded role vocabulary** `{"admin", "commercial", "public_good", "viewer"}` in `UserRole`, `USER_ROLES`, repository validation, and the CLI `create-user --role` choices. The default remains `"commercial"`.
2. **Migration `0003_public_good_whitelist`** creating `whitelist_applications` with a FK to `users`, a status CHECK constraint, a unique `user_id`, required applicant reason, optional decision reason, and a reversible downgrade. No `users` table alteration.
3. **`odrm.whitelist` backend package** containing the SQLAlchemy model, strict Pydantic schemas, repository protocol plus SQLAlchemy implementation, and the `WhitelistService` transition rules.
4. **API endpoints** in `backend/src/odrm/api/whitelist.py`: apply, own status, admin list, approve, and reject, all under `/api/v1/whitelist`.
5. **Frontend pages** `/dashboard/whitelist` and `/dashboard/admin/whitelist` with API-client functions, TanStack Query hooks, and component tests.
6. **Backend tests** for the migration, schemas, service rules, API RBAC, and SQLite-backed atomic approval.
7. **Updated auth tests** proving `public_good` is accepted by the repository and CLI and that admin authorization is enforced.

No new dependency, no global navigation change, and no modification to existing sprint artifacts are included.

---

## 3. Acceptance criteria

| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | `UserRole` is `Literal["admin", "commercial", "public_good", "viewer"]`; `USER_ROLES` is `frozenset({"admin", "commercial", "public_good", "viewer"})`; `SqlAlchemyUserRepository.create` accepts `public_good`; the CLI `--role` choices include `public_good`; the default role remains `commercial`; `engineer` remains invalid. | `test_user_repository.py`, `test_cli.py`, and the model change |
| AC-2 | Alembic head becomes `0003_public_good_whitelist`. The migration creates `whitelist_applications` with `id`, `user_id`, `status`, `reason`, `decision_reason`, and `created_at`; `user_id` is unique and FK-constrained to `users.id`; status is constrained to `pending`, `approved`, `rejected`; upgrade and downgrade both succeed on SQLite; `users` is not altered. | `test_public_good_whitelist_migration.py`; code review of the migration |
| AC-3 | `POST /api/v1/whitelist/apply`, `GET /api/v1/whitelist/application`, `GET /api/v1/whitelist/applications`, `POST /api/v1/whitelist/applications/{id}/approve`, and `POST /api/v1/whitelist/applications/{id}/reject` behave per the contract. Unauthenticated calls return 401; non-admin calls to admin endpoints return 403; approval changes the applicant's role to `public_good` in the same transaction as the status change; rejection leaves the role unchanged. | `test_whitelist_api.py`; SQLite-backed API test; service tests |
| AC-4 | `/dashboard/whitelist` lets an eligible authenticated user submit a reason and shows the current application status. `/dashboard/admin/whitelist` lists applications and performs approve/reject. A non-admin sees an access-denied state on the admin page. The backend remains authoritative. | `whitelist-page.test.tsx`, `admin-whitelist-page.test.tsx`, `api.test.ts` |
| AC-5 | A `public_good` or `admin` applicant receives 400 `ROLE_NOT_ELIGIBLE`. A second application while one is pending returns 409 `APPLICATION_EXISTS`; an approved application returns 409 `APPLICATION_ALREADY_APPROVED`; a rejected applicant can reapply and reopen the row; decisions on non-pending applications return 409 `APPLICATION_NOT_PENDING`; unknown application IDs return 404 `APPLICATION_NOT_FOUND`. | `test_whitelist_service.py`, `test_whitelist_api.py` |
| AC-6 | The full backend suite passes; the full frontend test suite, lint, typecheck, and build pass; Ruff and mypy pass. Only the files listed in sections 4 and 5 are created or modified. | `.venv` pytest/Ruff/mypy commands; `npm --prefix frontend test/lint/typecheck/build`; `git status --short` |

---

## 4. Files to create

| File | Purpose |
|---|---|
| `docs/SPRINT_10D_PLAN.md` | This Phase 2 plan; the only file created before Phase 4 authorization |
| `backend/src/odrm/whitelist/__init__.py` | Package marker |
| `backend/src/odrm/whitelist/models.py` | `WhitelistStatus`, `WHITELIST_STATUSES`, and the `WhitelistApplication` SQLAlchemy model |
| `backend/src/odrm/whitelist/schemas.py` | Strict apply/reject requests, public application response, and list response |
| `backend/src/odrm/whitelist/repository.py` | `WhitelistRepository` protocol, `WhitelistApplicationRecord`, `ApplyOutcome`, repository exceptions, and `SqlAlchemyWhitelistRepository` |
| `backend/src/odrm/whitelist/service.py` | `WhitelistService`, `RoleNotEligibleError`, `AdminRequiredError`, and transition orchestration |
| `backend/src/odrm/api/whitelist.py` | FastAPI router for the five endpoints and HTTP error mapping |
| `backend/migrations/versions/0003_public_good_whitelist.py` | Reversible table-creation migration |
| `backend/tests/whitelist/__init__.py` | Test package marker |
| `backend/tests/whitelist/fakes.py` | `InMemoryWhitelistRepository` sharing the in-memory user store |
| `backend/tests/whitelist/test_whitelist_schemas.py` | Strict request/response schema tests |
| `backend/tests/whitelist/test_whitelist_service.py` | Eligibility, transition, and reopen tests using the fake repository |
| `backend/tests/whitelist/test_whitelist_api.py` | HTTP, RBAC, and SQLite-backed atomic-approval tests |
| `backend/tests/db/test_public_good_whitelist_migration.py` | Upgrade, downgrade, schema, FK, uniqueness, and CHECK tests |
| `frontend/src/app/dashboard/whitelist/page.tsx` | App Router page for the applicant flow |
| `frontend/src/app/dashboard/admin/whitelist/page.tsx` | App Router page for admin review |
| `frontend/src/components/whitelist/whitelist-page.tsx` | Client component for apply/status states |
| `frontend/src/components/whitelist/admin-whitelist-page.tsx` | Client component for the review table and decisions |
| `frontend/src/hooks/use-whitelist.ts` | TanStack Query queries and mutations |
| `frontend/src/components/whitelist/whitelist-page.test.tsx` | Applicant page tests |
| `frontend/src/components/whitelist/admin-whitelist-page.test.tsx` | Admin page tests |

No other file may be created in Phase 4.

---

## 5. Files to modify

| File | Change |
|---|---|
| `backend/src/odrm/auth/models.py` | Add `public_good` to `UserRole` and `USER_ROLES`; leave `User.role` as `String(32)` with default `commercial` |
| `backend/src/odrm/auth/dependencies.py` | Add `require_admin`, returning 403 `{"code": "FORBIDDEN", "message": "Admin role required."}` for any non-admin |
| `backend/src/odrm/cli.py` | Add `public_good` to `--role` choices; keep `commercial` as the default |
| `backend/src/odrm/main.py` | Create one shared session factory; accept an optional `whitelist_repository`; build `WhitelistService`; store it on `app.state`; include the whitelist router under `/api/v1` |
| `backend/migrations/env.py` | Import `odrm.whitelist.models` so `whitelist_applications` is registered in `Base.metadata` |
| `backend/tests/auth/test_user_repository.py` | Add a `public_good` creation case; keep `engineer` in the invalid-role parametrization |
| `backend/tests/auth/test_cli.py` | Add a CLI `public_good` creation case |
| `backend/tests/auth/test_dependencies.py` | Add `require_admin` allow and deny cases |
| `frontend/src/lib/api.ts` | Add the five whitelist client functions using `apiFetch` |
| `frontend/src/lib/types.ts` | Add `WhitelistStatus`, `WhitelistApplication`, list, apply, and reject types |
| `frontend/src/lib/api.test.ts` | Add endpoint path/method and 404-to-null assertions |

No other file may be modified in Phase 4. In particular, `backend/tests/conftest.py`, `frontend/src/app/page.tsx`, `frontend/src/app/providers.tsx`, and `frontend/src/components/auth/*` remain unchanged.

---

## 6. Technical design

### 6.1 Role vocabulary

- `UserRole = Literal["admin", "commercial", "public_good", "viewer"]`.
- `USER_ROLES: frozenset[str] = frozenset({"admin", "commercial", "public_good", "viewer"})`.
- `SqlAlchemyUserRepository.create` already validates against `USER_ROLES`, so no repository logic change is needed.
- CLI choices become `("admin", "commercial", "public_good", "viewer")`; default stays `"commercial"`.
- No DB change is required because `users.role` is `String(32)`. Existing rows and JWTs remain valid.

### 6.2 SQLAlchemy model and migration

`WhitelistApplication` in `backend/src/odrm/whitelist/models.py`:

| Column | Definition |
|---|---|
| `id` | `String(36)`, primary key, `default=lambda: str(uuid4())` |
| `user_id` | `String(36)`, `ForeignKey("users.id", ondelete="CASCADE")`, non-null |
| `status` | `String(16)`, non-null, `default="pending"`, `server_default="pending"` |
| `reason` | `Text`, non-null, applicant text |
| `decision_reason` | `Text`, nullable, reviewer text |
| `created_at` | `DateTime(timezone=True)`, non-null, `server_default=func.now()`, Python default `datetime.now(UTC)` |

Table arguments:

- `UniqueConstraint("user_id", name="uq_whitelist_applications_user_id")`.
- `CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="ck_whitelist_applications_status")`.
- `relationship("User", lazy="joined")` for the `user_email` projection; this is a same-registry relationship and does not create an import cycle.

`WhitelistStatus = Literal["pending", "approved", "rejected"]`; `WHITELIST_STATUSES` is the matching frozenset.

Migration `0003_public_good_whitelist.py`:

- `revision = "0003_public_good_whitelist"` (27 characters, within Alembic's `VARCHAR(32)`).
- `down_revision = "0002_rename_engineer_commercial"`.
- `upgrade()` calls `op.create_table` with the columns and named constraints above.
- `downgrade()` calls `op.drop_table("whitelist_applications")`.
- No data backfill and no `users` alteration.
- `backend/migrations/env.py` imports `odrm.whitelist.models` before assigning `target_metadata` so future autogenerate and metadata checks see the table.

### 6.3 Repository contract and atomic transitions

`backend/src/odrm/whitelist/repository.py` defines:

- `WhitelistApplicationRecord` (frozen dataclass): `id`, `user_id`, `user_email`, `status`, `reason`, `decision_reason`, `created_at`.
- `ApplyOutcome` (frozen dataclass): `application: WhitelistApplicationRecord`, `created: bool`.
- Repository exceptions: `WhitelistApplicationNotFoundError`, `WhitelistApplicationNotPendingError`, `WhitelistApplicationExistsError`, `WhitelistApplicationAlreadyApprovedError`.
- `WhitelistRepository` protocol:
  - `get_for_user(user_id) -> WhitelistApplicationRecord | None`
  - `get_by_id(application_id) -> WhitelistApplicationRecord | None`
  - `list_all(status: WhitelistStatus | None = None) -> list[WhitelistApplicationRecord]`
  - `apply(user_id, reason) -> ApplyOutcome`
  - `approve(application_id) -> WhitelistApplicationRecord`
  - `reject(application_id, decision_reason) -> WhitelistApplicationRecord`

`SqlAlchemyWhitelistRepository` uses one session per operation and the shared session factory from `create_app`:

- `get_for_user`, `get_by_id`, `list_all` join `User` and map rows to `WhitelistApplicationRecord`; `list_all` orders by `created_at DESC, id ASC` and filters by status when provided.
- `apply` runs in one transaction:
  - Select the row by `user_id` with `with_for_update()`.
  - No row: insert `pending`, commit, return `created=True`.
  - `pending`: raise `WhitelistApplicationExistsError`.
  - `approved`: raise `WhitelistApplicationAlreadyApprovedError`.
  - `rejected`: set `status="pending"`, replace `reason`, clear `decision_reason`, commit, return `created=False`.
  - Catch `IntegrityError` on the unique constraint, roll back, and map to `WhitelistApplicationExistsError` for the concurrent-insert race.
- `approve` runs in one transaction:
  - Select the application with `with_for_update()`; missing raises `WhitelistApplicationNotFoundError`.
  - Non-`pending` raises `WhitelistApplicationNotPendingError`.
  - Load the related `User`; set `status="approved"` and `user.role="public_good"`.
  - Commit once; return the refreshed record. A failure rolls back both writes.
- `reject` runs in one transaction:
  - Same existence and `pending` checks.
  - Set `status="rejected"` and `decision_reason`.
  - Do not touch `user.role`; commit and return the record.

PostgreSQL uses row locks via `with_for_update()`; SQLite serializes writes. No cross-repository transaction is introduced.

### 6.4 `WhitelistService`

`backend/src/odrm/whitelist/service.py` owns business rules independent of HTTP:

- `RoleNotEligibleError`: raised when `user.role` is `public_good` or `admin` on apply.
- `AdminRequiredError`: defense-in-depth for service callers; the API normally enforces this first with `require_admin`.
- `apply(user, reason) -> ApplyOutcome`:
  - Reject `public_good` and `admin` with `RoleNotEligibleError`.
  - Delegate to `repository.apply(user.id, reason)`.
- `get_for_user(user) -> WhitelistApplicationRecord`:
  - Return the row or raise `WhitelistApplicationNotFoundError`.
- `list_applications(actor, status) -> list[WhitelistApplicationRecord]`:
  - Require `actor.role == "admin"`; otherwise `AdminRequiredError`.
  - Delegate the optional status filter.
- `approve(actor, application_id) -> WhitelistApplicationRecord`:
  - Require admin; delegate the atomic repository approval.
- `reject(actor, application_id, decision_reason) -> WhitelistApplicationRecord`:
  - Require admin; delegate the atomic repository rejection.

The service does not generate IDs, format JSON, or know HTTP status codes.

### 6.5 API router

`backend/src/odrm/api/whitelist.py` creates `router = APIRouter(prefix="/whitelist", tags=["whitelist"], dependencies=[Depends(get_current_user)])`.

| Route | Actor dependency | Behavior |
|---|---|---|
| `POST /apply` | `get_current_user` | Accept `WhitelistApplyRequest`; call service; set 201 when `created`, 200 when reopened; return `WhitelistApplicationPublic` |
| `GET /application` | `get_current_user` | Return the caller's row or 404 `APPLICATION_NOT_FOUND` |
| `GET /applications` | `require_admin` | Optional `status` query validated by `WhitelistStatus`; return `WhitelistApplicationListResponse` |
| `POST /applications/{application_id}/approve` | `require_admin` | Return the updated row |
| `POST /applications/{application_id}/reject` | `require_admin` | Accept `WhitelistRejectRequest`; return the updated row |

Schemas:

- `WhitelistApplyRequest`: `reason: str = Field(min_length=1, max_length=2000)`, `extra="forbid"`.
- `WhitelistRejectRequest`: same `reason` constraints, `extra="forbid"`.
- `WhitelistApplicationPublic`: `id`, `user_id`, `user_email: EmailStr`, `status`, `reason`, `decision_reason: str | None`, `created_at: datetime`.
- `WhitelistApplicationListResponse`: `items: list[WhitelistApplicationPublic]`, `total: int` (`ge=0`).

HTTP error mapping in the router:

| Exception | Status | Code |
|---|---|---|
| `RoleNotEligibleError` | 400 | `ROLE_NOT_ELIGIBLE` |
| `WhitelistApplicationExistsError` | 409 | `APPLICATION_EXISTS` |
| `WhitelistApplicationAlreadyApprovedError` | 409 | `APPLICATION_ALREADY_APPROVED` |
| `WhitelistApplicationNotFoundError` | 404 | `APPLICATION_NOT_FOUND` |
| `WhitelistApplicationNotPendingError` | 409 | `APPLICATION_NOT_PENDING` |
| `AdminRequiredError` | 403 | `FORBIDDEN` |

Every error uses the existing `{"code": ..., "message": ...}` detail shape. `require_admin` in `auth/dependencies.py` resolves `get_current_user` and returns the admin user or raises 403.

### 6.6 Application wiring

`create_app` changes:

- Build `session_factory = create_session_factory(settings.database_url)` once.
- Use it for the default `SqlAlchemyUserRepository` and the default `SqlAlchemyWhitelistRepository`.
- Add optional keyword `whitelist_repository: WhitelistRepository | None = None` alongside the existing injection points.
- Store `app.state.whitelist_service = WhitelistService(whitelist_repository)`.
- Include the whitelist router with `prefix="/api/v1"`.
- Existing callers remain source-compatible because the new argument is optional.

Tests that need an isolated whitelist store build their own app with in-memory or temporary-SQLite repositories; `backend/tests/conftest.py` stays unchanged.

### 6.7 Frontend design

Types in `frontend/src/lib/types.ts`:

- `WhitelistStatus = 'pending' | 'approved' | 'rejected'`.
- `WhitelistApplication`: `id`, `user_id`, `user_email`, `status`, `reason`, `decision_reason: string | null`, `created_at`.
- `WhitelistApplicationList`: `items: WhitelistApplication[]`, `total: number`.

Client functions in `frontend/src/lib/api.ts`:

- `getMyWhitelistApplication(): Promise<WhitelistApplication | null>`: catch `ApiError` with `status === 404` and return `null`; rethrow all others.
- `postWhitelistApplication(reason: string)`.
- `getWhitelistApplications(status?: WhitelistStatus)`.
- `postWhitelistApplicationApproval(id: string)`.
- `postWhitelistApplicationRejection(id: string, reason: string)`.

Hooks in `frontend/src/hooks/use-whitelist.ts`:

- `useMyWhitelistApplication()`: query key `["whitelist", "me", user.id]`, `retry: false`, enabled once auth is authenticated.
- `useWhitelistApplications(status)`: query key `["whitelist", "applications", status]`, enabled only when `user.role === "admin"`.
- `useApplyForWhitelist()`, `useApproveWhitelistApplication()`, `useRejectWhitelistApplication()`: mutations invalidate `["whitelist"]`; approval/rejection also invalidate the admin list.

`WhitelistPage` state and rendering:

- `useAuth()` for the current role.
- `useMyWhitelistApplication()` for the current row.
- Local `reason` and `error` state plus `useApplyForWhitelist()`.
- Render states: loading spinner; ineligible notice for `admin`/`public_good`; application form for eligible users with no row; pending card; approved card; rejected card with `decision_reason` and a reopen form.
- On successful apply, clear `reason`, surface API errors by code/message, and rely on query invalidation.

`AdminWhitelistPage` state and rendering:

- `useAuth()` guard: if `role !== "admin"`, render an access-denied message and do not mount the admin query.
- Local `statusFilter` (`all | pending | approved | rejected`), `rejectTarget`, and `rejectReason`.
- `useWhitelistApplications()` for the table; columns are email, status, reason, decision reason, created date, and actions.
- Approve button calls the approval mutation directly. Reject opens an inline reason field and calls the rejection mutation. Both buttons disable while their mutation is pending.
- No optimistic updates in D1; invalidate and refetch on success.

Both `page.tsx` files are thin App Router server components that export metadata and render the corresponding client component inside `AuthGate`. No global navigation or existing dashboard file changes.

### 6.8 Constraints

- No pagination in D1; the admin list returns all matching rows with `total`.
- No reviewer identity or timestamp columns; reviewer history is deferred to D2.
- No live refresh of the applicant's cached auth role; backend authorization updates immediately because `get_current_user` reloads the user, while the frontend role snapshot refreshes on reload/login.
- No new UI dependency; use existing Tailwind/React patterns.

---

## 7. TDD test plan

Phase 4 executes these slices in order. Each slice starts with a failing test, adds the minimum code, reruns the targeted test, then proceeds.

1. **Migration (AC-2).** In `test_public_good_whitelist_migration.py`, run Alembic from `0002` to `0003` on a temporary SQLite database. Assert the table, columns, nullability, unique constraint, FK, status CHECK, and head revision. Run downgrade and assert the table is gone while `users` survives. Mark the module `@pytest.mark.integration`.
2. **Role vocabulary (AC-1).** In `test_user_repository.py`, create a `public_good` user and assert persistence; keep `engineer` in the invalid-role cases. In `test_cli.py`, create a `public_good` user via `--role` and assert persistence.
3. **Schemas (AC-3, AC-5).** In `test_whitelist_schemas.py`, assert reason bounds (0 and 2001 rejected), `extra="forbid"` for apply and reject, valid status literals, and response serialization including nullable `decision_reason`.
4. **Service transitions (AC-5).** In `test_whitelist_service.py` with `InMemoryWhitelistRepository`:
   - eligible `commercial` and `viewer` apply successfully;
   - `public_good` and `admin` raise `RoleNotEligibleError`;
   - second pending application raises `WhitelistApplicationExistsError`;
   - approved application raises `WhitelistApplicationAlreadyApprovedError`;
   - rejected application reopens with the new reason and cleared `decision_reason`;
   - non-admin list/approve/reject raises `AdminRequiredError`;
   - approve raises `WhitelistApplicationNotPendingError` for approved/rejected rows;
   - reject stores the decision reason and leaves the user's role unchanged.
5. **Admin dependency (AC-3).** In `test_dependencies.py`, `require_admin` returns the user for `admin` and raises 403 `FORBIDDEN` for `commercial`, `public_good`, and `viewer`.
6. **API with in-memory repositories (AC-3, AC-5).** In `test_whitelist_api.py`, build an app with an in-memory user repository seeded with `admin`, `commercial`, `viewer`, and `public_good` users plus the in-memory whitelist repository. Assert:
   - anonymous calls return 401;
   - non-admin admin-route calls return 403;
   - eligible apply returns 201, duplicate returns 409, reopen returns 200;
   - own status returns 200 then 404 for a user without a row;
   - admin list filters by status;
   - approve returns 200 and a subsequent `/auth/me` shows `public_good`;
   - reject returns 200, stores `decision_reason`, and leaves role unchanged;
   - unknown IDs return 404 and non-pending decisions return 409.
7. **API with SQLite (AC-3 atomicity).** Reuse the API test module with a temporary SQLite app and real repositories. Approve a pending row and assert both `whitelist_applications.status == "approved"` and `users.role == "public_good"` persisted. Force a non-pending approval and assert neither write changed.
8. **Frontend API client (AC-4).** In `api.test.ts`, assert URL/method/body for all five functions and that `getMyWhitelistApplication` maps 404 to `null` while rethrowing other `ApiError` statuses.
9. **Frontend components (AC-4).** In `whitelist-page.test.tsx`, mock fetch like `dashboard.test.tsx` and assert:
   - eligible user sees the form, submits a reason, and sees the pending card;
   - public_good sees the approved state and no form;
   - rejected user sees the decision reason and reopen form;
   - API errors render a readable message.
   In `admin-whitelist-page.test.tsx`, assert:
   - non-admin sees access denied and no list request;
   - admin sees rows, filters by status, approves, and rejects with a reason;
   - buttons disable during pending mutations.

Commands after each slice and at the Phase 4 gate:

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
.\.venv\Scripts\python.exe -m ruff check backend/src backend/tests
.\.venv\Scripts\python.exe -m mypy
npm --prefix frontend test
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

---

## 8. Commit message

Final implementation commit after all gates pass:

```text
feat(whitelist): implement public-good whitelist flow
```

`docs/SPRINT_WORKFLOW.md` requires a commit after every successfully tested feature. Phase 4 commits each green TDD slice with a conventional message scoped to that slice, and the final integrated commit uses the message above. If the CTO prefers a single commit, squash the slices into one commit with this message.

---

## 9. Audit protocol

### Phase 3 - Review gate

- The CTO reviews this plan only. No implementation, test, migration, or frontend file is created.
- All revisions requested by the CTO are made to `docs/SPRINT_10D_PLAN.md` only.
- Before authorization, `git status --short` must show only `docs/SPRINT_10D_PLAN.md`.
- Phase 4 starts only on the exact phrase `AUTHORIZED: Sprint 10 D1 implementation phase`.
- Any scope question raised during review is resolved in this plan before implementation.

### Phase 4 - Implementation

- Follow the TDD order in section 7; do not write production code before its test exists and fails.
- Run the targeted test after each change. Run the full backend and frontend gates after each major slice and at the end.
- Enforce the allowed-file boundary from sections 4 and 5. Before each commit, `git status --short` must list only files in those sections; stop and ask the CTO if another file is required.
- Do not modify `docs/SPRINT_10_PLAN.md`, `docs/SPRINT_10B_PLAN.md`, `docs/SPRINT_10C_PLAN.md`, or any 0a/0b/0c source artifact.
- Commit only after a slice is green. Do not rewrite history or amend a failed commit; create a new commit.
- Report any deviation from this plan before proceeding, and record it for the Phase 5 report.
- End Phase 4 only when AC-1 through AC-6 pass and the final commit uses the section 8 message. The Phase 5 report is outside this plan.

---

## 10. Out of scope

- D2 Merkle-tree ESG audit trail and any application-history or reviewer-provenance storage.
- D3 open benchmark publication.
- D4 detection adapter dashboard wiring.
- NUPRC/NOGIET integration or data fetching.
- Email notifications, webhooks, or background jobs.
- Admin user-management UI, role revocation UI, or reviewer identity columns.
- Pagination beyond the D1 `{items, total}` list response.
- Tenant scoping, multi-tenancy changes, or quota enforcement.
- Changes to the existing `/` dashboard, global navigation, auth provider, auth gate, or any sprint-0a/0b/0c file.
- New dependencies.

---

## 11. Phase 2 gate

Stopping here. This plan is the only Phase 2 artifact. Phase 3 awaits CTO review and the exact authorization phrase:

```text
AUTHORIZED: Sprint 10 D1 implementation phase
```
