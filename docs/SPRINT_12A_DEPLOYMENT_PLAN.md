# Sprint 12A Plan - Zero Runway Deployment

| | |
|---|---|
| Status | Draft - awaiting CTO Phase 2 approval |
| Date | 2026-11-28 |
| Deliverable | Public, always-on Valoris demo at zero monthly cost |
| Baseline | `e3fec6bd8123e9a5c3f7866335a6541404b01a80` |
| Phase 4 authorization phrase on record | Pending |
| Target stack | Vercel Hobby (Next.js) + Render Free (Docker/FastAPI) + Neon Free (Postgres) |

No implementation code, test code, config file, or deployment action is performed until
the CTO approves this plan and authorizes Phase 4. This document is the Phase 2
deliverable only.

---

## 1. Scope and traceability

### 1.1 Objective

Give Valoris (ODRM-Copilot) public, always-on demo URLs with no monthly infrastructure
spend:

- Frontend: `https://<vercel-project>.vercel.app`
- API: `https://<render-service>.onrender.com`
- Database: Neon Free Postgres
- Model artifacts: shipped inside the Render Docker image

A reviewer must be able to open the Vercel URL, log in with a seeded admin account, run a
screening, view TEA output, download a report, and use the chat assistant when an LLM key
is configured.

### 1.2 In scope

1. Commit the two existing runtime model artifacts so Render can serve predictions.
2. Add a root `.dockerignore` and update `backend/Dockerfile` to copy models and honor
   Render's `PORT`.
3. Add `render.yaml` for a reproducible Render Blueprint.
4. Add `frontend/vercel.json` and a production env template.
5. Update `.env.example` with the database, JWT, and cookie variables that are currently
   undocumented.
6. Document the manual Neon -> Render -> Vercel sequence, including the build-time env
   dependency and the CORS close loop.
7. Run migrations with `alembic upgrade head` against Neon and seed an admin with
   `python -m odrm.cli create-user --password-stdin`.
8. Add deployment smoke verification and permanent deployment documentation.
9. Close the mandatory audit-readiness documentation gaps created by exposing the app to
   the public internet.

### 1.3 Out of scope

- Application feature work, UI changes, marker/icon swap, map attribution, or the D4 test.
- Next.js version bump, CORS refactor, database-path refactor, SEP-0055, or CI workflow.
- Paid Render/Vercel/Neon tiers, custom domains, uptime SLAs, or eliminating Render cold
  starts.
- Model retraining, new model versions, or changing prediction behavior.
- Full threat-model expansion beyond the deployment boundary (deferred to Sprint 12B if
  the CTO wants a broader review).

### 1.4 Success criteria

| ID | Criterion |
|---|---|
| 12A-1 | Vercel production URL loads the login page over HTTPS. |
| 12A-2 | `GET https://<render>/health` returns `{"status":"ok","env":"production"}`. |
| 12A-3 | `GET https://<render>/ready` returns `{"status":"ready"}` after Neon is reachable. |
| 12A-4 | Login from the Vercel origin sets `odrm_access_token` with `HttpOnly`, `Secure`, `SameSite=None`, `Path=/api/v1`. |
| 12A-5 | Authenticated `POST /api/v1/predict` returns both model predictions, not `503`. |
| 12A-6 | Authenticated `POST /api/v1/tea` returns financials and `X-Evidence-Status: recorded`. |
| 12A-7 | Report download works from the UI. |
| 12A-8 | Chat works when `ODRM_LLM_API_KEY` is set; otherwise the limitation is documented. |
| 12A-9 | No secret is committed; `.env` remains untracked. |
| 12A-10 | Re-running `alembic upgrade head` is a no-op; the admin user can be listed. |
| 12A-11 | Existing backend and frontend test/build gates still pass. |
| 12A-12 | Audit Readiness Impact section is complete and the deployment docs exist. |

---

## 2. Verified facts and deployment gotchas

These were checked against the repository, not assumed from prior notes.

| Area | Verified fact | Consequence |
|---|---|---|
| Frontend API URL | `frontend/src/lib/api.ts` uses `process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1"`. | The Vercel env var must be exactly `NEXT_PUBLIC_API_BASE_URL=https://<render>/api/v1`; it is baked at build time. |
| Backend env prefix | `backend/src/odrm/core/config.py` uses `SettingsConfigDict(env_prefix="ODRM_")`. | The real database variable is `ODRM_DATABASE_URL`, not `DATABASE_URL`. |
| Database driver | `pyproject.toml` installs `psycopg[binary]>=3.2`; the Docker image installs `psycopg[binary]`. | Use `postgresql+psycopg://`, not `postgresql+psycopg2://`. |
| CORS | `backend/src/odrm/main.py` reads `settings.cors_origins`, splits on commas, and sets `allow_credentials=True`. | `ODRM_CORS_ORIGINS` must contain the exact Vercel origin, with no trailing slash. |
| Auth cookie | `backend/src/odrm/auth/router.py` sets `httponly=True`, `path=settings.api_prefix`, `secure=settings.auth_cookie_secure`, `samesite=settings.auth_cookie_samesite`. | Cross-site login needs `ODRM_AUTH_COOKIE_SECURE=true` and `ODRM_AUTH_COOKIE_SAMESITE=none`. |
| API prefix | Routers are included with a hardcoded `prefix="/api/v1"`, while the cookie uses `settings.api_prefix`. | Keep the default `/api/v1`; do not set `ODRM_API_PREFIX` to a different value. |
| JWT validation | `config.py` rejects the development secret or any secret shorter than 32 characters when `env` is `staging`, `production`, or `prod`. | Set `ODRM_ENV=production` and a unique 32+ character `ODRM_JWT_SECRET`. |
| Docker context | `backend/Dockerfile` copies `pyproject.toml`, `README.md`, `backend/src`, `alembic.ini`, and `backend/migrations` from the repository root. | Render must build with the repository root as context and `backend/Dockerfile` as the Dockerfile. |
| Docker port | The current `CMD` hardcodes `--port 8000`; Render injects `PORT`. | Change the command to `${PORT:-8000}` and update the healthcheck. |
| Models in Docker | `backend/Dockerfile` does not copy `models/`; `backend/.dockerignore` excludes `models/`; Compose mounts `./models:/app/models:ro`. | A Git-based Render build would start with no models and return `503` from `/predict`, `/tea`, and `/report`. |
| Model ignore rules | `.gitignore` ignores `models/*.joblib` and `models/**/*.joblib`; the JSON metadata is already tracked. | Add a narrow exception and commit the two `model.joblib` files. |
| Model size | `ch4_conversion` is 3,724,130 bytes; `syngas_yield_mol_per_mol_ch4` is 3,581,398 bytes; total 7,305,528 bytes. | Committing both artifacts adds about 7 MB to the repository, which is acceptable. |
| Root Docker context | There is no root `.dockerignore`. | Docker would send `.git`, `node_modules`, `frontend`, `docs`, and other large paths to the builder. Add a root `.dockerignore`. |
| Migrations | `alembic.ini` points at `%(here)s/backend/migrations`; `backend/migrations/env.py` overrides the SQLite URL with `get_settings().database_url`. | The Docker CMD's `alembic upgrade head` works with `ODRM_DATABASE_URL`; migrations 0001-0004 are the chain. |
| Admin seed | `backend/src/odrm/cli.py` supports `--password-stdin` and requires at least 12 characters. | Seed via stdin, never via argv; `list-users` verifies the result. |
| LLM | `build_chat_model` requires `ODRM_LLM_MODEL` and a provider key; the app still starts without them. | Chat is optional for deployment; document it if no key is provided. |
| Docs gaps | `docs/THREAT_MODEL.md`, `docs/DATAFLOW.md`, and `docs/SECURITY.md` do not exist. | Mandatory audit items 4, 5, and 8 need at least deployment-scoped versions or explicit CTO deferral. |

---

## 3. Target architecture

```
Reviewer browser
    |
    | HTTPS, credentials: include
    v
Vercel Hobby (Next.js 16.4.3)
    |
    | HTTPS JSON, cookie odrm_access_token
    v
Render Free Web Service (Docker, FastAPI/uvicorn)
    |                         \
    | TLS                      \ optional HTTPS
    v                           v
Neon Free Postgres          LLM provider (Gemini/OpenAI)
```

### 3.1 URL and build dependency

The order matters:

1. Render must exist first because Vercel needs the API URL at build time.
2. Vercel must exist next because Render's CORS allowlist needs the exact frontend origin.
3. Render must be restarted after the Vercel URL is known.

Do not build Vercel against a guessed Render URL. Do not set CORS to a wildcard:
`allow_credentials=True` makes `*` invalid for credentialed requests.

### 3.2 Accepted operational behavior

- Render Free spins down after inactivity. The first request can take roughly 30-60
  seconds. This is accepted for the grant demo and is not treated as a defect.
- Neon Free may suspend an idle database; the first query can add a short delay.
- The API and frontend are single-instance. In-memory rate limiting is sufficient.

---

## 4. Decisions requiring CTO approval

| ID | Decision | Rationale | Alternative |
|---|---|---|---|
| D1 | Commit the two existing `model.joblib` artifacts and copy `models/` into the Docker image. | Deterministic, no build-time training, no extra build minutes, and the artifacts total only ~7 MB. | Train at Docker build time from `data/odrm_dataset.parquet`; slower and requires committing or generating the dataset. |
| D2 | Use a Neon direct (non-pooler) connection string for both the app and Alembic. | Avoids pooler behavior during migrations and keeps the free-tier setup simple. | Pooled URL for the app plus direct URL for migrations; more moving parts. |
| D3 | Build Render from the repository root with a root `.dockerignore`. | The Dockerfile already assumes root-relative paths. | Move the Dockerfile and restructure paths; unnecessary risk. |
| D4 | Keep `ODRM_API_PREFIX` at its default `/api/v1`. | Routers are hardcoded to `/api/v1`; changing the setting would break the cookie path. | Refactor router prefixes; out of scope. |
| D5 | Seed the admin from a local shell against Neon before the first Render deploy. | Avoids relying on Render free-tier shell availability. | Seed from Render Shell after deploy; keep as fallback. |
| D6 | Create minimal deployment-scoped audit docs. | Items 4, 5, and 8 are mandatory; the files are absent. | Explicit CTO deferral with sign-off; this blocks release under the current workflow. |
| D7 | Do not add a root `vercel.json`; use `frontend/vercel.json` and the Vercel root-directory setting. | The frontend is a subdirectory; Vercel's root-directory setting is the reliable mechanism. | Root `vercel.json` with `cd frontend` commands; more brittle. |

---

## 5. Files to create or modify

### 5.1 `.gitignore` (modify)

Add one narrow exception after the existing `models/**/*.joblib` rule:

```gitignore
# Sprint 12A: runtime model artifacts required by the Render image
!models/odrm/**/*.joblib
```

Then stage the two model files:

```powershell
git add .gitignore `
  models/odrm/ch4_conversion/v1-20261104T120949Z/model.joblib `
  models/odrm/syngas_yield_mol_per_mol_ch4/v1-20261104T121024Z/model.joblib
git check-ignore -v models/odrm/ch4_conversion/v1-20261104T120949Z/model.joblib
```

`git check-ignore` must produce no output. The metadata JSON files are already tracked and
must not be regenerated.

### 5.2 `.dockerignore` (create at repository root)

```dockerignore
# Root build context for Render / Docker
.git
.github
.vscode
.venv
venv
env
__pycache__
*.py[cod]
.pytest_cache
.ruff_cache
.mypy_cache
.coverage
htmlcov
frontend
node_modules
docs
contracts
benchmark
data
exports
scripts
backend/tests
*.db
*.sqlite
*.sqlite3
*.log
.env
.env.*
!.env.example
!.env.docker.example
```

`models/` is deliberately not excluded. `backend/.dockerignore` remains in the tree for
local backend-context builds, but it is not authoritative for the Render root context.

### 5.3 `backend/Dockerfile` (modify)

Exact changes:

1. Copy the committed models into the runtime image, after dependency installation so
   model-only changes do not invalidate the dependency layer:

```dockerfile
COPY models ./models
```

2. Make the model directory explicit:

```dockerfile
ENV ODRM_MODEL_DIR=/app/models
```

3. Replace the healthcheck with a `PORT`-aware command:

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os, urllib.request; port=os.getenv('PORT','8000'); urllib.request.urlopen('http://127.0.0.1:'+port+'/health', timeout=3)"
```

4. Replace the `CMD`:

```dockerfile
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn odrm.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

Keep `EXPOSE 8000`; Render ignores it and uses `PORT`.

### 5.4 `render.yaml` (create)

```yaml
services:
  - type: web
    name: valoris-api
    runtime: docker
    plan: free
    dockerfilePath: ./backend/Dockerfile
    healthCheckPath: /health
    autoDeploy: true
    envVars:
      - key: ODRM_ENV
        value: production
      - key: ODRM_LOG_LEVEL
        value: INFO
      - key: ODRM_DATABASE_URL
        sync: false
      - key: ODRM_JWT_SECRET
        sync: false
      - key: ODRM_CORS_ORIGINS
        sync: false
      - key: ODRM_AUTH_COOKIE_SECURE
        value: "true"
      - key: ODRM_AUTH_COOKIE_SAMESITE
        value: "none"
      - key: ODRM_MODEL_DIR
        value: /app/models
      - key: ODRM_LLM_PROVIDER
        value: gemini
      - key: ODRM_LLM_MODEL
        value: gemini-3.5-flash
      - key: ODRM_LLM_API_KEY
        sync: false
```

Notes:

- `sync: false` means Render prompts for the value in the dashboard; no secret is stored
  in Git.
- If the service name `valoris-api` is already taken, choose a unique name and update all
  URLs in this plan.
- If chat is not part of the demo, remove the three `ODRM_LLM_*` entries; the API still
  starts.
- Do not add `ODRM_API_PREFIX`; the default is correct.

### 5.5 `frontend/vercel.json` (create)

```json
{
  "framework": "nextjs",
  "installCommand": "npm ci",
  "buildCommand": "npm run build"
}
```

The Vercel project's Root Directory must be set to `frontend`. `vercel.json` cannot set
the root directory itself.

### 5.6 `frontend/.env.production.example` (create)

```dotenv
# Build-time variable for Vercel. Replace with the Render service URL + /api/v1.
NEXT_PUBLIC_API_BASE_URL=https://<render-service>.onrender.com/api/v1
```

### 5.7 `.env.example` (modify)

Add the currently undocumented deployment-relevant variables:

```dotenv
# Database
# Local default is SQLite. Production uses a Neon Postgres URL with the
# postgresql+psycopg:// scheme and ?sslmode=require.
ODRM_DATABASE_URL=sqlite:///./odrm.db

# JWT
# Must be at least 32 characters and must not be the development placeholder
# when ODRM_ENV is staging/production.
ODRM_JWT_SECRET=dev-only-insecure-jwt-secret-change-me

# Auth cookie
ODRM_AUTH_COOKIE_SECURE=false
ODRM_AUTH_COOKIE_SAMESITE=lax
```

Keep the existing local CORS, model, data, LLM, and TEA values. Do not add real secrets.

### 5.8 `docs/DEPLOYMENT.md` (create)

Permanent operator runbook containing:

1. Architecture and URL ownership.
2. Full environment-variable table (name, where set, secret/public, example shape).
3. Neon project/database creation and direct-URL conversion.
4. Local migration and admin-seed commands.
5. Render Blueprint creation and first-deploy checks.
6. Vercel project creation with Root Directory `frontend`.
7. CORS close loop and redeploy.
8. Smoke checklist and troubleshooting.
9. Rollback and secret-rotation notes.

### 5.9 Audit documentation (create, deployment-scoped)

These are minimal files, not a full security program:

- `docs/THREAT_MODEL.md`: assets, trust boundaries, deployment threats, mitigations,
  residual risk, remediation table. Reference the existing auth, evidence-chain, and
  LLM-guardrail tests.
- `docs/DATAFLOW.md`: Mermaid diagram of browser -> Vercel -> Render -> Neon, plus
  Render -> LLM provider, with trust boundaries and data classes.
- `docs/SECURITY.md`: secret storage, admin account data, retention/access policy,
  incident response, and deployment hardening checklist.

If the CTO explicitly defers these, the deferral must be recorded here and the release
gate remains blocked under `docs/SPRINT_WORKFLOW.md`.

### 5.10 `README.md` (modify)

Add a short "Deployment" section linking to `docs/DEPLOYMENT.md` and listing the two
public URLs once known. Do not duplicate the full runbook.

---

## 6. Deployment sequence (manual, after Phase 4 approval)

### Phase 0 - Preflight locally

1. Confirm the worktree contains only intended changes.
2. Run the existing backend and frontend gates:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check backend/src backend/tests scripts
.\.venv\Scripts\python.exe -m mypy backend/src scripts
cd frontend
npm ci
npm run lint
npm run typecheck
npm run test
npm run build
```

3. Build the Docker image from the repository root:

```powershell
docker build -f backend/Dockerfile -t valoris-api:12a .
```

4. Verify the model copy and `PORT` override:

```powershell
docker run --rm --entrypoint python valoris-api:12a -c "from pathlib import Path; print(sorted(p.name for p in Path('/app/models/odrm').glob('*')))"
docker run --rm -p 10000:10000 -e PORT=10000 -e ODRM_ENV=local -e ODRM_DATABASE_URL=sqlite:///./odrm.db -e ODRM_JWT_SECRET=local-test-secret-at-least-32-chars valoris-api:12a
curl.exe http://localhost:10000/health
curl.exe http://localhost:10000/ready
```

### Phase 1 - Neon

1. Create a Neon Free project and database (for example `valoris`).
2. Copy the direct connection string, not the `-pooler` host.
3. Convert it to SQLAlchemy's psycopg3 form:

```text
postgresql+psycopg://<user>:<password>@<direct-host>/<database>?sslmode=require
```

URL-encode any special characters in the password.

4. Run migrations from the repository root:

```powershell
$env:ODRM_DATABASE_URL = "postgresql+psycopg://..."
$env:PYTHONPATH = "backend/src"
.\.venv\Scripts\alembic.exe upgrade head
```

5. Seed the admin. The password must be at least 12 characters and must be piped through
   stdin:

```powershell
$env:ODRM_DATABASE_URL = "postgresql+psycopg://..."
$env:PYTHONPATH = "backend/src"
$secure = Read-Host -AsSecureString "Admin password"
$plain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
  [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
)
$plain | .\.venv\Scripts\python.exe -m odrm.cli create-user `
  --email admin@valoris.example --role admin --password-stdin
Remove-Variable plain, secure
.\.venv\Scripts\python.exe -m odrm.cli list-users
```

Do not put the password on the command line. If the user already exists, `list-users`
is the verification path.

### Phase 2 - Render backend

1. Create a Render Blueprint from `render.yaml` and connect the repository.
2. Enter the prompted secrets:
   - `ODRM_DATABASE_URL`: the Neon direct URL from Phase 1.
   - `ODRM_JWT_SECRET`: generate with
     `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
   - `ODRM_CORS_ORIGINS`: a temporary placeholder such as
     `https://placeholder.vercel.app`; this is replaced in Phase 4.
   - `ODRM_LLM_API_KEY`: the provider key, or leave blank if chat is disabled.
3. Deploy and watch the logs for:
   - `alembic upgrade head` completing.
   - `Loaded model ch4_conversion ...` and `Loaded model syngas_yield_mol_per_mol_ch4 ...`.
   - Uvicorn listening on the injected `PORT`.
4. Record the service URL. Verify:

```powershell
curl.exe https://<render-service>.onrender.com/health
curl.exe https://<render-service>.onrender.com/ready
```

If the model lines are absent, the image is missing `models/`; stop and fix the Docker
copy before continuing.

### Phase 3 - Vercel frontend

1. Import the repository into Vercel.
2. Set Root Directory to `frontend`.
3. Confirm Framework Preset is Next.js, Install Command is `npm ci`, and Build Command is
   `npm run build`.
4. Set the production environment variable:

```text
NEXT_PUBLIC_API_BASE_URL=https://<render-service>.onrender.com/api/v1
```

5. Deploy. Vercel must build only after the Render URL is final.
6. Record the production URL. If the project name is unavailable, use the generated
   `https://<project>-<hash>.vercel.app` URL.

### Phase 4 - Close the CORS loop

1. In Render, set:

```text
ODRM_CORS_ORIGINS=https://<vercel-production-url>
```

No trailing slash and no path. If a custom domain is added later, use a comma-separated
list.

2. Save; Render restarts the service.
3. Verify preflight from the Vercel origin:

```powershell
curl.exe -i -X OPTIONS "https://<render-service>.onrender.com/api/v1/auth/login" `
  -H "Origin: https://<vercel-production-url>" `
  -H "Access-Control-Request-Method: POST" `
  -H "Access-Control-Request-Headers: content-type"
```

Expect the exact `Access-Control-Allow-Origin` value and
`Access-Control-Allow-Credentials: true`.

### Phase 5 - Smoke verification

1. Open the Vercel URL in a private browser window.
2. Log in with the seeded admin. In DevTools, confirm the cookie:
   - name `odrm_access_token`
   - `HttpOnly`
   - `Secure`
   - `SameSite=None`
   - `Path=/api/v1`
3. Confirm `GET /api/v1/auth/me` succeeds with the cookie.
4. Run a prediction with the default dashboard values; confirm `predictions` contains
   both targets and `model_version` is present.
5. Run TEA; confirm financials and `X-Evidence-Status: recorded`.
6. Download the report; confirm the PDF opens.
7. If the LLM key is configured, send a chat message; otherwise record "chat not
   configured" in the deployment notes.
8. Refresh after several minutes to observe the accepted Render cold start.

### Phase 6 - Documentation and evidence

1. Record the final URLs, Render service name, Neon project, migration head, model
   versions, and env-var names (never secret values) in `docs/DEPLOYMENT.md`.
2. Update `README.md` with the public links.
3. Capture smoke output for the Phase 5 report.
4. Confirm `git status` contains no `.env`, no secrets, and no unintended generated files.

---

## 7. Testing strategy

### 7.1 Existing gates

- Backend: `pytest -q`, `ruff check`, `mypy`.
- Frontend: `npm ci`, `lint`, `typecheck`, `test`, `build`.
- No application behavior changes are planned, so the existing suites are regression
  evidence rather than new feature tests.

### 7.2 Deployment-specific checks

| Check | Method | Pass condition |
|---|---|---|
| Docker image contains models | `docker run --entrypoint python ...` | Both target directories appear under `/app/models/odrm`. |
| Port override | `docker run -e PORT=10000 -p 10000:10000` | `/health` responds on 10000. |
| Migration idempotence | Run `alembic upgrade head` twice | Second run is a no-op. |
| Admin seed | `create-user --password-stdin` then `list-users` | Admin row appears. |
| CORS preflight | `curl.exe -X OPTIONS` with Vercel Origin | Exact allow-origin and allow-credentials headers. |
| Cookie flags | Browser DevTools | `HttpOnly`, `Secure`, `SameSite=None`, `Path=/api/v1`. |
| Model availability | Authenticated `POST /api/v1/predict` | `200` with two predictions, not `503`. |
| Evidence recording | Authenticated `POST /api/v1/tea` | `X-Evidence-Status: recorded`. |
| Cold start | Wait for Render idle, then load Vercel | Request eventually succeeds; no code change. |

### 7.3 Negative checks

- Request from an unlisted origin: browser blocks the response.
- Request without the cookie: `401`.
- Request with `ODRM_CORS_ORIGINS` missing the Vercel origin: login fails at CORS.
- Request to `/predict` with models absent: `503` (only expected in a deliberately broken
  image; production must not show this).

---

## 8. Rollback and recovery

| Failure | Recovery |
|---|---|
| Render deploy fails | Use Render's previous deploy rollback; keep the prior env values. |
| Migration fails | Read the Alembic error; fix forward with a new migration. Do not downgrade without a tested path. |
| Bad CORS/cookie setting | Restore the prior Render env values and restart. |
| Vercel build uses the wrong API URL | Change `NEXT_PUBLIC_API_BASE_URL` and redeploy; the value is build-time. |
| Neon unavailable | Check Neon status and connection limit; the app returns `503` on `/ready`. |
| Secret exposure | Rotate `ODRM_JWT_SECRET` (invalidates sessions), rotate the Neon password, rotate the LLM key, and redeploy. |

---

## 9. Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Models missing from the Render image | High without D1 | Predict/TEA/report return `503` | Commit artifacts, copy `models/`, verify logs and image contents. |
| CORS/cookie misconfiguration | Medium | Login fails cross-site | Exact origin, `SameSite=None`, `Secure`, `allow_credentials=True`, preflight check. |
| Vercel built before Render URL is known | Medium | Frontend calls the wrong API | Enforce Neon -> Render -> Vercel order; rebuild if the Render URL changes. |
| Render cold start mistaken for an outage | High | Demo delay | Document the accepted 30-60 second first request. |
| Root Docker context too large | Medium | Slow/failed builds | Add root `.dockerignore`; keep `models/` only. |
| Neon pooler breaks migrations | Medium | Deploy fails | Use the direct non-pooler URL. |
| Secret committed by accident | Low | Credential compromise | Dashboard secrets, `.env` ignored, `git status` review, rotation plan. |
| LLM key absent | Medium | Chat unavailable | Document the limitation; chat is not required for prediction/TEA/report. |
| `ODRM_API_PREFIX` changed | Low | Cookie path and routes diverge | Keep the default `/api/v1`. |
| Audit docs missing | High | Release gate blocked | Create the deployment-scoped docs in 5.9 or record explicit CTO deferral. |

---

## 10. Audit Readiness Impact

### 10.1 Mandatory items

| # | Item | Impact | Evidence produced | Status after this sprint |
|---|---|---|---|---|
| 1 | Scope traceability | This plan defines the deployment boundary, target stack, and exclusions. | Section 1 of this plan. | Compliant. |
| 2 | Repo hygiene | Adds root `.dockerignore`, documents the model-artifact policy, and adds deployment docs; no dead code or secret files. | `.dockerignore`, `.gitignore`, `docs/DEPLOYMENT.md`, README link. | Compliant. |
| 3 | Integration tests | No application behavior changes. Existing backend/frontend suites remain the regression gate; deployment checks are manual smoke evidence. | Phase 4 test output plus Phase 5 smoke output. | Compliant for existing scope; no new integration test required. |
| 4 | Threat model | Public exposure adds Vercel, Render, Neon, and an optional LLM provider to the trust boundary. | `docs/THREAT_MODEL.md` deployment section. | Gap closed by 5.9; otherwise explicit CTO deferral blocks release. |
| 5 | Dataflow diagram | New external flows and trust boundaries. | `docs/DATAFLOW.md` Mermaid diagram. | Gap closed by 5.9; otherwise explicit CTO deferral blocks release. |
| 6 | Cryptographic correctness | No changes to the evidence chain, Merkle proof, or JWT implementation; TLS protects transport. | Existing evidence tests; no new crypto code. | N/A / unchanged. |
| 7 | LLM boundary integrity | If Gemini/OpenAI is enabled, prompts leave Render for a third party. Existing guardrails remain; the deployment doc records the boundary. | Threat-model section and existing guardrail tests. | Compliant if chat is enabled; N/A if disabled. |
| 8 | Personal data handling | Admin email and Argon2 password hash are stored in Neon; no end-user PII is collected. | `docs/SECURITY.md` retention/access section. | Gap closed by 5.9; otherwise explicit CTO deferral blocks release. |

### 10.2 Bonus items

| # | Item | Impact | Status |
|---|---|---|---|
| 9 | Tooling scan | No new dependencies are added. A dated `pip-audit` / `npm audit` run is still recommended. | Deferred to Sprint 12B; no new dependency risk introduced here. |
| 10 | Remediation plan | No deployment findings yet. | Deferred until the first scan. |
| 11 | Dependency review | No `pyproject.toml` or `package.json` changes. | N/A. |

### 10.3 SDF repo-hygiene and security notes

- The two model binaries are the only new large tracked artifacts; their metadata and
  checksums remain in the tracked JSON files.
- No `.env` file, database URL, JWT secret, or LLM key is committed.
- Public endpoints are limited to the existing authenticated API plus `/health` and
  `/ready`.
- The admin account is the only seeded identity; it is created manually and is not
  embedded in the image.
- The deployment docs record how to rotate the JWT secret, Neon password, and LLM key.

---

## 11. Phase 4 authorization checklist

The CTO should approve or amend:

- [ ] D1: commit the two `model.joblib` artifacts (~7 MB) and copy `models/` into the image.
- [ ] D2: use the Neon direct (non-pooler) URL for app and migrations.
- [ ] D3: root Docker context plus root `.dockerignore`.
- [ ] D4: keep `ODRM_API_PREFIX` at `/api/v1`.
- [ ] D5: seed the admin from a local shell against Neon.
- [ ] D6: create deployment-scoped `THREAT_MODEL.md`, `DATAFLOW.md`, and `SECURITY.md`.
- [ ] D7: use `frontend/vercel.json` and Vercel's Root Directory setting.
- [ ] Exact `render.yaml`, `backend/Dockerfile`, `.dockerignore`, `.gitignore`, and
  `.env.example` contents.
- [ ] Manual-only deployment: the agent will not call external deployment MCPs/CLIs.

After approval, the Phase 4 authorization phrase is:

```text
AUTHORIZED: Sprint 12A deployment implementation phase
```
