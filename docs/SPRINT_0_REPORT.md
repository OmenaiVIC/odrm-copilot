# Sprint 0 — Foundation: Review Note

| | |
|---|---|
| Status | **Complete** |
| Date | 2026-11-01 |
| Scope | Scaffolding, tooling, contracts, docs — no product features |
| Plan | [`SPRINT_0_PLAN.md`](SPRINT_0_PLAN.md) (approved) |
| Workflow | [`SPRINT_WORKFLOW.md`](SPRINT_WORKFLOW.md) |
| Architecture | [`ARCHITECTURE.md`](ARCHITECTURE.md) |

All backend and frontend gates pass. No cloud deployment, credentials, or
customer data were introduced.

---

## 1. Objectives vs. outcome

| Plan §6 step | Outcome |
|---|---|
| 1. `pyproject.toml`, `.env.example`, venv, deps, freeze | Done — 104-line `requirements.txt` |
| 2. Backend src/tests skeleton | Done — 7 packages, 4 test packages |
| 3. `conftest.py` + network-blocking smoke test | Done — 3 tests, outbound blocked |
| 4. Next.js scaffold + `typecheck` + `api.ts` | Done — Next 16.4.3, typed client |
| 5. `docs/ARCHITECTURE.md` | Done — stack, C4, data, ML, agent, API, security, NFRs, ADRs |
| 6. `SPRINT_WORKFLOW.md` + `data/schemas/` | Done — committed earlier; JSON Schema contract added |
| 7. Run all gates + evidence | Done — see §4 |

---

## 2. Environment

| Item | Value |
|---|---|
| OS / shell | Windows, PowerShell 5.1 |
| Python | 3.11.9 (`.venv`), default system 3.14 avoided |
| Node / npm | Node via `create-next-app`; npm lock committed |
| Next.js / React | 16.4.3 / 19.3.0 |
| Tailwind | v4 (`@tailwindcss/turbopack`) |
| FastAPI / Pydantic | 0.162.0 / 2.14.2 |
| pandas / PyArrow / NumPy | 3.1.0 / 26.0.0 / 2.4.6 |
| XGBoost / scikit-learn | 3.2.0 / 1.9.1 |
| LangChain / core | 1.4.7 / 1.7.3 |
| pytest | 9.2.0 |

---

## 3. Deliverables

### Backend

- `pyproject.toml` — Python `>=3.11,<3.13`, runtime + `dev` extras, pytest
  (`testpaths`, `pythonpath`, strict markers), ruff (100 cols, py311), strict mypy,
  coverage.
- `requirements.txt` — frozen (`pip freeze --exclude-editable`), 104 lines.
- `.env.example` — `ODRM_*` settings + optional `OPENAI_API_KEY`; no secrets.
- `backend/src/odrm/` — `api`, `core`, `domain`, `data`, `ml`, `agents`, `services`.
- `backend/src/odrm/core/config.py` — `Settings` (`ODRM_` prefix), CORS list
  property, cached `get_settings()`.
- `backend/src/odrm/main.py` — `create_app(settings=...)` factory, CORS, `GET /health`,
  module-level app, `uvicorn` entrypoint.
- `backend/tests/conftest.py` — session-autouse outbound-network blocker (localhost
  allowed); fixtures: `test_settings`, `app`, `client`, `odrm_row`, `odrm_frame`,
  `odrm_frame_bad`, `parquet_path`, `tiny_model`, `fake_llm`, `tool_spy`,
  `assert_valid_odrm_frame`, `assert_tool_called`.
- `backend/tests/unit/test_app_boot.py` — app boots, health returns
  `{"status":"ok","env":"test"}`, blocked outbound connection raises.

### Frontend

- `frontend/` — Next.js App Router, TypeScript, Tailwind v4, ESLint.
- `frontend/src/lib/api.ts` — typed `apiFetch<T>` + `ApiError` against
  `NEXT_PUBLIC_API_BASE_URL`.
- `frontend/.env.local.example`, `.prettierignore`, project README linking
  `docs/ARCHITECTURE.md`.
- Scripts: `dev`, `build`, `start`, `lint`, `typecheck`, `format`.

### Data and docs

- `data/schemas/odrm_v1.json` — JSON Schema 2020-12, 29 properties
  (23 required, 6 optional), enums, units-in-description, hard 1000 °C cap,
  `x-odrm` risk thresholds + storage metadata.
- `docs/ARCHITECTURE.md` — C4 L1/L2, request/failure flows, stack + ADR index,
  data architecture/versioning, ML lifecycle and R² > 0.95 gate, OOD envelope,
  4-layer agent design, API surface, tenancy/security, observability, NFRs,
  commercial model, deployment, risks, milestones.
- `docs/SPRINT_WORKFLOW.md` — plan → approval → execute → evidence → review
  (committed separately, `ee17f38`).

---

## 4. Gate evidence

### Backend

```
> .\.venv\Scripts\python.exe -m pytest backend/tests -q
...                                                                      [100%]
3 passed in 0.07s
pytest_exit=0

> .\.venv\Scripts\python.exe -m ruff check backend
All checks passed!
ruff_exit=0

> .\.venv\Scripts\python.exe -m ruff format --check backend
17 files already formatted
ruff_format_exit=0

> .\.venv\Scripts\python.exe -m mypy backend/src
Success: no issues found in 10 source files
mypy_exit=0
```

### Frontend

```
> npm run lint
eslint
lint_exit=0

> npm run typecheck
tsc --noEmit
typecheck_exit=0

> npm run build
✓ Compiled successfully
✓ Generating static pages (4/4)
build_exit=0
```

### Contract check

```
property_count 29
required_count 23
missing_in_properties []
missing_optional []
```

---

## 5. Commit history

| Commit | Message |
|---|---|
| `ee17f38` | `docs: add SPRINT_WORKFLOW.md` |
| `df5b58c` | `feat: backend dependencies installed` |
| `8383fe3` | `feat: backend scaffold and network-isolated test harness` |
| `6253b39` | `feat: scaffold Next.js frontend with typed API client` |
| `0700a19` | `docs: add approved Sprint 0 plan` |
| `e31b9ff` | `docs: architecture baseline and ODRM v1 schema contract` |
| _this_ | `docs: Sprint 0 review note` |

---

## 6. Deviations and decisions

1. **Tailwind v4 has no `tailwind.config.*`.** The plan's "confirm content globs"
   step is not applicable; v4 auto-detects sources. Recorded as ADR-002.
2. **Prettier added manually.** The planned `format` script assumed availability;
   the scaffold did not include Prettier, so it was added as a dev dependency.
3. **`create-next-app` wrote `frontend/AGENTS.md`.** Next 16 re-creates this agent
   rules file; it is committed to keep the tree clean.
4. **Column count.** The plan table contains **29** columns (23 required + 6
   nullable); the schema and fixtures follow the table, not the older "28" phrase.
5. **pytest-asyncio warning.** Added
   `asyncio_default_fixture_loop_scope = "function"` to remove the deprecation
   warning before it becomes an error.
6. **`.env.local.example` whitelist.** The scaffold's `.env*` ignore rule was
   amended with `!.env.local.example` so the template is shareable.
7. **Network blocker scope.** It intercepts `socket.connect`, `connect_ex`, and
   `create_connection`; name resolution (`getaddrinfo`) is not intercepted. This is
   sufficient for the current suite and will be revisited if any test performs DNS
   lookups for side effects.
8. **npm audit.** `create-next-app` reported 16 moderate advisories in the dev
   dependency tree. No production runtime exposure was assessed in Sprint 0;
   dependency review is a Sprint 3 CI task.

---

## 7. Risk register status

| ID | Risk | Status |
|---|---|---|
| R0-1 | LangChain churn | Mitigated — versions frozen in `requirements.txt` |
| R0-2 | Python/wheel gaps | Closed — Python 3.11.9, all imports verified |
| R0-3 | Scaffold refused non-empty dir | Closed — empty-dir scaffold succeeded |
| R0-4 | Schema drift | Mitigated — versioned JSON Schema + manifest policy in architecture |
| R0-5 | Trust outside envelope | Mitigated — OOD + envelope documented; implementation Sprint 2 |
| R0-6 | LLM invents physics | Mitigated — fake-model/tool-spy harness; tool-only path specified |
| R0-7 | Missing workflow contract | Closed — `SPRINT_WORKFLOW.md` committed |
| R0-8 | Secrets committed | Mitigated — `.env.example` only, `.env*` ignored, CI scan planned |

New follow-ups:

- **S0-F1:** Resolve npm dev-tree advisories and enable dependency review in CI (Sprint 3).
- **S0-F2:** Add `jsonschema`-based validation of `odrm_v1.json` itself in Sprint 1
  (currently syntax/shape checked with the standard library).

---

## 8. Ready for Sprint 1

Sprint 1 can start immediately: `validate_odrm_frame()` and the synthetic ODRM
generator have their contract, fixtures, and test harness in place. No blockers.

**Recommendation:** accept Sprint 0 and authorize Sprint 1 (data validation +
generator) on the same terms.
