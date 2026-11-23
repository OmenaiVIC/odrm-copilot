# Sprint 10 Plan - Deliverable 0c: Rename `engineer` Role to `commercial`

| | |
|---|---|
| Status | **Approved - Phase 4 authorized** |
| Date | 2026-11-22 |
| Scope | Rename the default/operator role from `engineer` to `commercial` across the auth model, repository, CLI, migration, and tests without changing authorization semantics or invalidating existing JWTs |
| Dependency | 0a complete at `75180d2`; 0b complete at `3cfa7cc`; 0c Phase 1 approved with Q1-Q4 clarifications |
| Approval phrase | `AUTHORIZED: Sprint 10 0c implementation phase` |

> **Planning gate:** this file is the Phase 2 deliverable for 0c. No implementation code, test code, migration code, or test run may be created until the CTO approves this plan with the exact phrase above.

> **Revision ID correction:** the approved migration filename is `0002_rename_engineer_to_commercial.py`, but the revision ID is `0002_rename_engineer_commercial` (31 characters) because Alembic's default `alembic_version.version_num` is `VARCHAR(32)`.

> **Plan location decision:** 0c uses a separate plan file, `docs/SPRINT_10C_PLAN.md`. `docs/SPRINT_10_PLAN.md` (0a) and `docs/SPRINT_10B_PLAN.md` (0b) remain unchanged for audit continuity.

> **Phase 1 CTO decisions incorporated:**
>
> - **Q1 - Option A:** `0002` must update existing `engineer` rows and change the column `server_default` with `op.alter_column`. `downgrade()` reverses both. Use `op.batch_alter_table` on SQLite.
> - **Q2:** the four source artifacts are `models.py`, `repository.py`, `cli.py`, and the new `0002` migration. Leave `tokens.py` and `0001_create_users.py` untouched. Do not tighten `TokenClaims.role`.
> - **Q3:** update only role assignments and assertions. Leave email fixtures such as `engineer@example.com` unchanged.
> - **Q4:** create `backend/tests/db/__init__.py`; mark the migration test `@pytest.mark.integration`.

---

## 1. Goal

Rename the default/operator role from `engineer` to `commercial` so the persisted role vocabulary is `{"admin", "commercial", "viewer"}`. The change covers the ORM model, repository defaults, CLI choices/default, an Alembic data-and-default migration, and the affected tests.

0c does not add `"public_good"`, does not enforce RBAC, does not invalidate existing JWTs, and does not change `"admin"` or `"viewer"`.

---

## 2. Deliverables

1. **Canonical role vocabulary** `{"admin", "commercial", "viewer"}` in `UserRole` and `USER_ROLES`, with `"engineer"` removed.
2. **`User.role` defaults** changed to `"commercial"` in both the Python `default` and the SQLAlchemy `server_default`.
3. **Repository and CLI defaults** changed to `"commercial"`, with CLI `--role` choices limited to the three canonical roles.
4. **`0002_rename_engineer_to_commercial.py`** that updates existing `engineer` rows, changes the database default via `op.alter_column`, and reverses both in `downgrade()`.
5. **Migration tests** in a new `backend/tests/db` package proving upgrade, downgrade, default changes, and preservation of `"admin"`/`"viewer"` rows.
6. **Updated auth and frontend tests** that use `"commercial"` for role values and assertions while keeping email fixtures unchanged.
7. **JWT compatibility** preserved: `TokenClaims.role` stays `str`, `tokens.py` is untouched, and legacy `"engineer"` tokens still authenticate by `sub`.

No new dependency, route, permission check, or frontend production code is introduced.

---

## 3. Acceptance criteria

| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | `UserRole` is `Literal["admin", "commercial", "viewer"]`; `USER_ROLES` is `frozenset({"admin", "commercial", "viewer"})`; `User.role` uses `default="commercial"` and `server_default="commercial"`. The repository rejects `"engineer"` as an unsupported role. | Model/repository tests; `test_invalid_role_is_rejected` parametrized with `owner` and `engineer` |
| AC-2 | `UserRepository.create` and `SqlAlchemyUserRepository.create` default to `role="commercial"`; CLI `--role` choices are `("admin", "commercial", "viewer")` and its default is `"commercial"`. The CLI rejects `"engineer"`. | Repository default test; CLI create test; new CLI rejection test |
| AC-3 | `0002` updates every existing `role = 'engineer'` row to `'commercial'` and changes the column `server_default` to `'commercial'` via `op.alter_column`. On SQLite the migration uses `op.batch_alter_table`; on PostgreSQL it uses `op.alter_column` directly. `0001_create_users.py` remains unchanged. | Migration test on SQLite; code review of the PostgreSQL branch; `git diff` |
| AC-4 | `0002.downgrade()` updates every `role = 'commercial'` row back to `'engineer'` and restores `server_default='engineer'`. `"admin"` and `"viewer"` rows are unchanged in both directions. Upgrade then downgrade is schema-reversible. | Migration downgrade test; round-trip test |
| AC-5 | Backend auth fixtures/assertions and the two frontend dashboard fixtures use `"commercial"` for role values. Email fixtures remain `engineer@example.com`. No `"engineer"` role value remains except explicit rejection/legacy-compatibility assertions and the historical `0001`/`0002` downgrade SQL. | `rg` verification; test review; `git diff` |
| AC-6 | Existing JWTs with `role="engineer"` remain valid. `TokenClaims.role` stays `str`; `tokens.py` is untouched; a legacy engineer-role token decodes and resolves to the renamed commercial user by `sub`. | New token decode test; new auth-service legacy-token test; `git diff` showing `tokens.py` unchanged |
| AC-7 | Full backend suite, the frontend dashboard test, Ruff, and mypy pass. Only the files listed in sections 4 and 5 are created or modified. No production frontend code, documentation prose, or 0a/0b files change. | `.venv` pytest/ruff/mypy commands; `npm --prefix frontend test`; `git status --short` |

---

## 4. Files to create

| File | Purpose |
|---|---|
| `docs/SPRINT_10C_PLAN.md` | This Phase 2 plan; the only file created before Phase 4 authorization |
| `backend/migrations/versions/0002_rename_engineer_to_commercial.py` | Data migration plus `server_default` change via `op.alter_column`, with SQLite batch path and reversible downgrade |
| `backend/tests/db/__init__.py` | Empty package marker for the migration test package |
| `backend/tests/db/test_role_rename_migration.py` | Integration tests for upgrade, downgrade, default changes, admin/viewer preservation, and SQLite schema preservation |

No other file is created. The migration test package marker is intentionally empty.

---

## 5. Files to modify

| File | Change |
|---|---|
| `backend/src/odrm/auth/models.py` | `UserRole`, `USER_ROLES`, `User.role.default`, `User.role.server_default` |
| `backend/src/odrm/auth/repository.py` | Both `role: str = "engineer"` defaults in the protocol and implementation |
| `backend/src/odrm/cli.py` | `--role` choices and default |
| `backend/tests/conftest.py` | `test_user` role assignment; email remains `engineer@example.com` |
| `backend/tests/auth/fakes.py` | `InMemoryUserRepository.create` default role |
| `backend/tests/auth/test_auth_api.py` | User fixture role and expected login/`/me` role values; emails unchanged |
| `backend/tests/auth/test_auth_service.py` | `make_user` default role, unknown-token role, and new legacy-token compatibility test |
| `backend/tests/auth/test_cli.py` | CLI role argument/assertion; new removed-role rejection test; emails unchanged |
| `backend/tests/auth/test_dependencies.py` | `make_user` role; email unchanged |
| `backend/tests/auth/test_tokens.py` | Issue helper, role assertions, algorithm-none payload, expiry payload; new legacy decode test |
| `backend/tests/auth/test_user_repository.py` | Default-role assertion, model-repr role, and invalid-role parametrization; emails unchanged |
| `frontend/src/components/dashboard/dashboard.test.tsx` | Two `role: 'engineer'` fixtures become `role: 'commercial'` |

Explicitly **not modified**:

- `backend/migrations/versions/0001_create_users.py` remains the historical `server_default="engineer"` revision.
- `backend/src/odrm/auth/tokens.py` remains unchanged; `TokenClaims.role` stays `str`.
- Frontend production code, `docs/ARCHITECTURE.md`, `docs/SPRINT_10_PLAN.md`, `docs/SPRINT_10B_PLAN.md`, and all 0a/0b tests remain unchanged.
- No email fixture is renamed; `engineer@example.com` remains an email, not a role.

---

## 6. Technical design

### 6.1 Canonical role vocabulary and defaults

| Location | Before | After |
|---|---|---|
| `UserRole` | `Literal["admin", "engineer", "viewer"]` | `Literal["admin", "commercial", "viewer"]` |
| `USER_ROLES` | `frozenset({"admin", "engineer", "viewer"})` | `frozenset({"admin", "commercial", "viewer"})` |
| `User.role` Python default | `"engineer"` | `"commercial"` |
| `User.role` server default | `"engineer"` | `"commercial"` |
| `UserRepository.create` default | `"engineer"` | `"commercial"` |
| `SqlAlchemyUserRepository.create` default | `"engineer"` | `"commercial"` |
| CLI `--role` choices | `("admin", "engineer", "viewer")` | `("admin", "commercial", "viewer")` |
| CLI `--role` default | `"engineer"` | `"commercial"` |

`"admin"` and `"viewer"` keep their existing meaning. `"public_good"` is not added. No authorization middleware is introduced, so this is a vocabulary/default rename, not a permission-model change.

### 6.2 Migration structure

`backend/migrations/versions/0002_rename_engineer_to_commercial.py`:

- `revision = "0002_rename_engineer_commercial"`
- `down_revision = "0001_create_users"`
- `branch_labels = None`
- `depends_on = None`

Upgrade order:

1. Update existing rows: `UPDATE users SET role = 'commercial' WHERE role = 'engineer'`.
2. Change the column default to `'commercial'` with `op.alter_column`.
3. On SQLite, perform the column change through `op.batch_alter_table`.

Downgrade order:

1. Update rows: `UPDATE users SET role = 'engineer' WHERE role = 'commercial'`.
2. Restore the column default to `'engineer'`.
3. Use the same dialect-specific path.

Design sketch:

```python
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_rename_engineer_commercial"
down_revision: str | None = "0001_create_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _set_role_server_default(value: str) -> None:
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("users") as batch_op:
            batch_op.alter_column(
                "role",
                existing_type=sa.String(length=32),
                existing_nullable=False,
                server_default=value,
            )
        return

    op.alter_column(
        "users",
        "role",
        existing_type=sa.String(length=32),
        existing_nullable=False,
        server_default=value,
    )


def upgrade() -> None:
    op.execute("UPDATE users SET role = 'commercial' WHERE role = 'engineer'")
    _set_role_server_default("commercial")


def downgrade() -> None:
    op.execute("UPDATE users SET role = 'engineer' WHERE role = 'commercial'")
    _set_role_server_default("engineer")
```

Technical notes:

- `server_default` receives the plain string `"commercial"` / `"engineer"`, matching the style in `0001`; SQLAlchemy quotes the literal in generated DDL.
- `existing_type=sa.String(length=32)` and `existing_nullable=False` are supplied because `alter_column` needs the existing column definition for SQLite batch recreation.
- The PostgreSQL branch is the direct `op.alter_column` path required by Q1. The SQLite branch is the required batch path.
- No column type, length, nullability, index, or constraint is intentionally changed. The migration only updates data and the default.
- `op.batch_alter_table` recreates the SQLite table. The migration test must assert that the `id` primary key and the unique `ix_users_email` index survive both upgrade and downgrade.

### 6.3 Data semantics

- Existing rows with `role='engineer'` become `'commercial'`.
- Existing rows with `role='admin'` or `role='viewer'` are untouched.
- New rows inserted after upgrade without an explicit role receive `'commercial'` from the new server default.
- `downgrade()` converts all `'commercial'` rows back to `'engineer'`. This includes rows created after upgrade; that is acceptable because `'commercial'` did not exist before 0c, and a downgrade intentionally restores the old vocabulary.
- The migration does not create, delete, or reorder users.
- The migration does not change `created_at`, `is_active`, `email`, `password_hash`, or `id`.

### 6.4 JWT compatibility

`TokenClaims.role` is a plain `str`, and `AuthService.resolve_access_token` resolves the current user by `claims.sub` without comparing the claim role to the database role. Therefore:

- A token issued before 0c with `role="engineer"` continues to decode and authenticate.
- Renaming the database row to `"commercial"` does not invalidate existing sessions.
- New tokens for renamed users contain `role="commercial"` because `AuthService.issue_access_token` reads `user.role`.
- `tokens.py` must not be modified and `TokenClaims.role` must not become a `Literal`, because either change would reject legacy engineer-role tokens.

Two compatibility tests pin this behavior:

- `test_legacy_engineer_role_claim_still_decodes` in `test_tokens.py`.
- `test_legacy_engineer_token_resolves_to_renamed_user` in `test_auth_service.py`.

### 6.5 Test update map

| File | Current role use | Planned change |
|---|---|---|
| `backend/tests/conftest.py` | `test_user.role="engineer"` | `"commercial"`; email unchanged |
| `backend/tests/auth/fakes.py` | `create(..., role="engineer")` | `"commercial"` |
| `backend/tests/auth/test_auth_api.py` | User fixture and two expected JSON bodies use `"engineer"` | `"commercial"`; emails unchanged |
| `backend/tests/auth/test_auth_service.py` | `make_user(role="engineer")` and unknown-token role | `"commercial"`; add legacy-token test |
| `backend/tests/auth/test_cli.py` | `--role engineer` and `user.role == "engineer"` | `--role commercial` / `"commercial"`; add rejection test; emails unchanged |
| `backend/tests/auth/test_dependencies.py` | `make_user(role="engineer")` | `"commercial"`; email unchanged |
| `backend/tests/auth/test_tokens.py` | Issue helper, two claim assertions, algorithm-none payload, expiry payload | `"commercial"`; add legacy decode test; emails unchanged |
| `backend/tests/auth/test_user_repository.py` | Default-role assertion and model-repr role | `"commercial"`; parametrize invalid role with `owner` and `engineer`; emails unchanged |
| `frontend/src/components/dashboard/dashboard.test.tsx` | Two `role: 'engineer'` fixtures | `role: 'commercial'` |

No production frontend code references the auth role vocabulary; the dashboard test is the only frontend change.

### 6.6 Risks and mitigations

| Risk | Mitigation |
|---|---|
| SQLite batch recreation could drop the email unique index or primary key | Migration test inspects the primary key and `ix_users_email` after upgrade and downgrade. If batch recreation fails to preserve them, use `batch_alter_table(..., copy_from=...)` with the `0001` table definition as the fallback. |
| The PostgreSQL `op.alter_column` branch is not exercised by the SQLite test | Code review confirms the direct branch; optional Docker PostgreSQL smoke test if the environment is available. |
| Existing engineer-role JWTs could be rejected if `TokenClaims.role` is tightened | Q2 keeps `tokens.py` unchanged; two legacy-token tests pin decode and resolve behavior. |
| Downgrade converts post-upgrade commercial rows to engineer | Documented as intentional for a vocabulary downgrade; no pre-0c commercial rows exist. |
| Email fixtures could be accidentally renamed | Q3 leaves every `engineer@example.com` email unchanged; `rg` review distinguishes email from role values. |
| Batch mode could silently change nullability or type | `existing_type` and `existing_nullable` are supplied; the migration test can inspect the role column after both directions. |

### 6.7 Conventions

- Python 3.11+, SQLAlchemy 2.x, Alembic 1.x.
- Typed migration signatures; `Sequence` imported from `collections.abc`.
- No new dependency.
- Ruff line length 100; import sorting per repo config.
- Migration test uses `pytestmark = pytest.mark.integration`.
- Existing auth tests keep their `pytest.mark.unit` behavior through the repo's default collection rules; no marker is removed.
- No comments are added to production code.

---

## 7. TDD test plan

### 7.1 New migration test module

`backend/tests/db/test_role_rename_migration.py`

Module setup:

- `pytestmark = pytest.mark.integration`.
- Build an Alembic `Config` whose `script_location` points to `backend/migrations`.
- Use `monkeypatch.setenv("ODRM_DATABASE_URL", f"sqlite:///{tmp_path / 'migration.db'}")`.
- Call `get_settings.cache_clear()` before the migration run and in teardown.
- Run `command.upgrade(config, "0001_create_users")`, insert fixture rows with raw SQL, then run `command.upgrade(config, "0002_rename_engineer_commercial")`.
- Inspect roles with `sqlalchemy.select`; inspect the column default, primary key, and indexes with `sqlalchemy.inspect`.
- Normalize the reflected default by stripping surrounding single or double quotes before comparing to `"commercial"` or `"engineer"`.

| Test | AC | Assertion |
|---|---|---|
| `test_upgrade_renames_engineer_rows_and_sets_commercial_default` | AC-3 | Insert `engineer`, `admin`, and `viewer` rows at `0001`; upgrade to `0002`; the engineer row is `commercial`, admin/viewer are unchanged; a new row inserted without a role gets `commercial`; reflected default is `commercial`. |
| `test_downgrade_restores_engineer_rows_and_engineer_default` | AC-4 | After upgrade, downgrade to `0001`; the migrated commercial row is `engineer`; admin/viewer are unchanged; a new row inserted without a role gets `engineer`; reflected default is `engineer`. |
| `test_migration_round_trip_preserves_admin_and_viewer_rows` | AC-4 | Upgrade, downgrade, upgrade again; admin/viewer rows keep their roles through every step; engineer/commercial rows transition correctly. |
| `test_sqlite_batch_alter_preserves_primary_key_and_email_unique_index` | AC-3, AC-4 | After upgrade and after downgrade, `inspect(...).get_pk_constraint("users")["constrained_columns"] == ["id"]` and the `ix_users_email` index exists with a truthy `unique` flag. |

The migration test does not import the migration module directly; it exercises the real Alembic revision chain. This makes the missing-revision failure real in the failing-first step.

### 7.2 Updated auth tests

| Test | Change |
|---|---|
| `test_create_and_fetch_by_id_and_lowercase_email` | Default role assertion becomes `"commercial"`; email assertions stay `engineer@example.com`. |
| `test_invalid_role_is_rejected` | Parametrize with `"owner"` and `"engineer"`; both raise `ValueError`. |
| `test_model_repr_does_not_expose_password_hash` | Constructed role becomes `"commercial"`; email unchanged. |
| `test_create_user_from_stdin` | CLI argument and persisted role become `"commercial"`; email unchanged. |
| `test_create_user_rejects_removed_engineer_role` | New test: `--role engineer` raises `SystemExit` with code `2`; no user is persisted. |
| `test_login_returns_token_user_and_http_only_cookie` | Expected response role becomes `"commercial"`; email unchanged. |
| `test_me_returns_current_user_with_bearer` | Expected response role becomes `"commercial"`; email unchanged. |
| `test_bearer_token_authenticates` | Fixture role becomes `"commercial"`; email assertion unchanged. |
| `test_issued_token_has_expected_claims_and_expiry` | Issued role and payload assertion become `"commercial"`; email unchanged. |
| `test_valid_token_round_trips_to_claims` | Claims role becomes `"commercial"`; email unchanged. |
| `test_alg_none_token_fails` | Payload role becomes `"commercial"`; email unchanged. |
| `test_expiry_uses_the_injected_clock` | Issued role becomes `"commercial"`; email unchanged. |
| `test_legacy_engineer_role_claim_still_decodes` | New test: issue a token with `role="engineer"` and assert `claims.role == "engineer"`. |
| `test_legacy_engineer_token_resolves_to_renamed_user` | New test in `test_auth_service.py`: a user has `role="commercial"`, a manually issued token has `role="engineer"`, and `resolve_access_token` returns the user. |
| `test_resolve_token_rejects_unknown_user` | Manually issued role becomes `"commercial"`. |
| `test_issue_token_contains_user_claims` | Unchanged; still asserts the `"admin"` role is preserved. |
| `test_dependencies.make_user` | Role becomes `"commercial"`; email unchanged. |
| `frontend/src/components/dashboard/dashboard.test.tsx` | Both dashboard fixtures become `role: 'commercial'`; no production frontend change. |

### 7.3 TDD sequence

1. Write `backend/tests/db/test_role_rename_migration.py` first.
2. Run it before creating `0002`; expect a real Alembic missing-revision failure for `0002_rename_engineer_commercial`.
3. Create `0002` and rerun; the migration tests pass.
4. Update the auth tests and fixtures to `"commercial"`; run the targeted auth tests.
5. Add the legacy-token and CLI-rejection tests; rerun the targeted tests.
6. Run the full backend suite, then Ruff and mypy.
7. Update the two frontend dashboard fixtures and run the dashboard test.
8. Record the failing-first output, passing output, full-suite tail, lint/typecheck results, and frontend result for Phase 4.

### 7.4 Commands

Failing-first migration test:

```powershell
.venv\Scripts\python.exe -m pytest backend/tests/db/test_role_rename_migration.py -q
```

Expected failure: Alembic cannot locate revision `0002_rename_engineer_commercial` because the migration file does not exist yet. This is a real revision-chain failure, not an import or syntax error.

Targeted and regression:

```powershell
.venv\Scripts\python.exe -m pytest backend/tests/db/test_role_rename_migration.py -q
.venv\Scripts\python.exe -m pytest backend/tests/auth -q
.venv\Scripts\python.exe -m pytest backend/tests -q
.venv\Scripts\ruff.exe check backend/src/odrm/auth/models.py backend/src/odrm/auth/repository.py backend/src/odrm/cli.py backend/migrations/versions/0002_rename_engineer_to_commercial.py backend/tests/db backend/tests/auth backend/tests/conftest.py
.venv\Scripts\mypy.exe backend/src/odrm/auth/models.py backend/src/odrm/auth/repository.py backend/src/odrm/cli.py
npm --prefix frontend test -- src/components/dashboard/dashboard.test.tsx
```

Role-value audit:

```powershell
rg -n "engineer" backend/src backend/tests backend/migrations frontend/src
git status --short
```

Expected remaining `engineer` occurrences after 0c:

- Email fixtures such as `engineer@example.com`.
- Explicit negative assertions such as `role="engineer"` in the invalid-role test and CLI rejection test.
- Legacy-token compatibility tests that intentionally use `role="engineer"`.
- The historical `server_default="engineer"` in `0001_create_users.py`.
- The `downgrade()` UPDATE and default in `0002_rename_engineer_to_commercial.py`.

No role assertion or fixture should still expect `"engineer"` as the current default.

---

## 8. Commit message

Use exactly this one-line implementation commit message:

```text
feat(auth): rename engineer role to commercial
```

Commit protocol:

- This Phase 2 plan is committed separately after CTO approval as `docs(sprint-10): add 0c implementation plan`.
- The 0c implementation commit contains only the files listed in sections 4 and 5, excluding this already-committed plan.
- One implementation commit per deliverable; do not batch with 0a, 0b, or later deliverables.
- Before the implementation commit, `git status --short` must show only the allowed files.
- The implementation commit hash is reported for the Sprint 10 report.

---

## 9. Audit protocol

### Phase 2 gate

- This plan exists at `docs/SPRINT_10C_PLAN.md` and is the only new file at this gate.
- All ten required sections are present.
- The four source artifacts and every test/doc file are named explicitly.
- The `op.alter_column` requirement and SQLite `op.batch_alter_table` path are recorded.
- `0001_create_users.py` and `tokens.py` are explicitly untouched.
- No implementation code, migration code, test code, or test run exists.

### Phase 3 review gate

- The CTO reviews this plan and approves it with the exact phrase `AUTHORIZED: Sprint 10 0c implementation phase`.
- Every acceptance criterion maps to at least one test or a named gate check.
- Q1-Q4 are reflected without reinterpretation.
- The plan preserves `"admin"` and `"viewer"`, excludes `"public_good"`, performs no admin restore, and keeps email fixtures unchanged.
- The plan keeps `TokenClaims.role` as `str` and does not invalidate legacy engineer-role JWTs.
- The plan includes no frontend production change, no RBAC enforcement, and no column-type change.

### Phase 4 implementation audit

- Failing-first output is a real Alembic missing-revision failure.
- Migration tests pass on SQLite, including default reflection and primary-key/unique-index preservation.
- Targeted auth tests pass.
- Full backend suite passes with no regressions.
- Frontend dashboard test passes.
- Ruff and mypy pass.
- `rg` review confirms the only remaining `engineer` role values are the intended negative, legacy-compatibility, and historical-migration occurrences.
- `git status --short` shows only the allowed files before the implementation commit.
- The implementation commit message matches section 8 exactly.
- The PostgreSQL `op.alter_column` branch is code-reviewed; an optional Docker PostgreSQL smoke test is recorded if available.
- The commit hash and test counts are reported for the Sprint 10 report.

### Phase 5

Deferred until all Sprint 10 deliverables pass; `docs/SPRINT_10_REPORT.md` will cite this deliverable's commit hash, migration result, and test counts.

---

## 10. Out of scope

- Adding the `"public_good"` role or whitelist flow
- RBAC enforcement, permissions, middleware, route guards, or role-based access checks
- Refresh tokens, MFA, CSP, session revocation, or token invalidation
- Changing `"admin"` or `"viewer"` behavior
- Changing the `role` column type, length, nullability, or constraints
- Tightening `TokenClaims.role` to a `Literal` or changing JWT claim structure
- Admin restore steps or restoring any pre-existing administrator role
- Renaming email fixtures or changing `engineer@example.com` addresses
- Historical data changes beyond `engineer` → `commercial`
- Frontend production code, dashboard role rendering, or API client types
- Documentation prose updates such as `docs/ARCHITECTURE.md`
- Unrelated “engineering” terms in plans, reports, or domain text
- Changes to 0a/0b code, tests, or plan files
- New dependencies, Docker/Postgres setup changes, or deployment changes
- Sprint 10 report or Phase 5 activities
