# Valoris Deployment Runbook

Manual, zero-cost deployment of Valoris (ODRM-Copilot) to Neon Free, Render Free, and
Vercel Hobby.

This runbook is intentionally manual. It does not use deployment MCPs, CLIs, or CI.
Cloud dashboard actions require a human operator.

---

## 1. Architecture and ownership

```
Reviewer browser
    |
    | HTTPS, credentials: include
    v
Vercel Hobby (Next.js)
    |
    | HTTPS JSON, cookie odrm_access_token
    v
Render Free (Docker, FastAPI)
    |                         \
    | TLS                      \ optional HTTPS
    v                           v
Neon Free Postgres          LLM provider (Gemini/OpenAI)
```

| Component | Owner | Free-tier behavior |
|---|---|---|
| Vercel project | Frontend team | Builds on push; production URL is stable. |
| Render web service | Backend team | Sleeps after inactivity; first request can take 30-60 seconds. |
| Neon project | Backend team | Database may suspend when idle; first query can be delayed. |
| LLM provider | Product team | Optional; chat is unavailable without a key. |

The public API URL is `https://<render-service>.onrender.com`. The public frontend URL is
`https://<vercel-project>.vercel.app`. Record the actual values in the deployment log; do
not guess them.

---

## 2. Environment variables

### 2.1 Backend (Render)

| Variable | Secret? | Value / shape | Notes |
|---|---|---|---|
| `ODRM_ENV` | No | `production` | Enables production JWT validation. |
| `ODRM_LOG_LEVEL` | No | `INFO` | |
| `ODRM_DATABASE_URL` | Yes | `postgresql+psycopg://user:pass@direct-host/db?sslmode=require` | Neon direct URL, not the pooler. URL-encode special characters. |
| `ODRM_JWT_SECRET` | Yes | 32+ random characters | Generate with `python -c "import secrets; print(secrets.token_urlsafe(48))"`. |
| `ODRM_CORS_ORIGINS` | No | `https://<vercel-project>.vercel.app` | Exact origin, no trailing slash. |
| `ODRM_AUTH_COOKIE_SECURE` | No | `true` | Required for cross-site cookies over HTTPS. |
| `ODRM_AUTH_COOKIE_SAMESITE` | No | `none` | Required for Vercel-to-Render cross-site requests. |
| `ODRM_MODEL_DIR` | No | `/app/models` | Models are baked into the image. |
| `ODRM_LLM_PROVIDER` | No | `gemini` or `openai` | Optional. |
| `ODRM_LLM_MODEL` | No | Provider model ID | Optional; must be available to the key. |
| `ODRM_LLM_API_KEY` | Yes | Provider key | Optional; chat fails gracefully without it. |

Do not set `ODRM_API_PREFIX` to anything other than `/api/v1`. Routers are registered
under `/api/v1`, and the auth cookie path is derived from this setting.

### 2.2 Frontend (Vercel)

| Variable | Secret? | Value |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | No (public) | `https://<render-service>.onrender.com/api/v1` |

This value is baked at build time. Changing it requires a new Vercel deployment.

---

## 3. Neon setup

1. Create a Neon Free project and database, for example `valoris`.
2. Open **Connection Details** and copy the **direct** connection string. Do not use the
   `-pooler` host for the app or migrations.
3. Convert the scheme to SQLAlchemy's psycopg3 driver:

```text
postgresql+psycopg://<user>:<password>@<direct-host>/<database>?sslmode=require
```

4. Keep the URL out of Git. Store it only in the Render dashboard and in a local shell
   variable for the one-time migration/seed.

### 3.1 Run migrations locally

From the repository root, with the project virtual environment:

```powershell
$env:ODRM_DATABASE_URL = "postgresql+psycopg://..."
$env:PYTHONPATH = "backend/src"
.\.venv\Scripts\alembic.exe upgrade head
```

The chain is `0001` through `0004`. Running the command twice must be a no-op.

### 3.2 Seed the admin

The password must be at least 12 characters. Pipe it through stdin; never put it on the
command line.

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

If the user already exists, use `list-users` to verify it. Do not embed the password in
the Docker image or in Git.

---

## 4. Render setup

1. In Render, create a **Blueprint** from `render.yaml` and connect the repository.
2. Enter the prompted secrets:
   - `ODRM_DATABASE_URL`: the Neon direct URL.
   - `ODRM_JWT_SECRET`: a fresh 32+ character secret.
   - `ODRM_CORS_ORIGINS`: a temporary placeholder such as
     `https://placeholder.vercel.app`; replace it after Vercel exists.
   - `ODRM_LLM_API_KEY`: the provider key, or leave blank.
3. Deploy. Watch the logs for:
   - `alembic upgrade head` completing without error.
   - `Loaded model ch4_conversion ...`.
   - `Loaded model syngas_yield_mol_per_mol_ch4 ...`.
   - Uvicorn listening on the injected `PORT`.
4. Record the service URL. Verify:

```powershell
curl.exe https://<render-service>.onrender.com/health
curl.exe https://<render-service>.onrender.com/ready
```

`/health` does not require the database. `/ready` verifies database connectivity. Render's
health check uses `/health` so a slow Neon start does not cause a restart loop.

If the model log lines are absent, the image is missing `models/`. Stop and fix the Docker
copy before continuing.

---

## 5. Vercel setup

1. Import the repository into Vercel.
2. Set **Root Directory** to `frontend`.
3. Confirm the framework is Next.js, the install command is `npm ci`, and the build
   command is `npm run build`.
4. Add the production environment variable:

```text
NEXT_PUBLIC_API_BASE_URL=https://<render-service>.onrender.com/api/v1
```

5. Deploy. Vercel must build only after the Render URL is final.
6. Record the production URL. If the preferred project name is unavailable, use the
   generated `https://<project>-<hash>.vercel.app` URL.

The frontend's `next.config.ts` sets `output: "standalone"`. Vercel may ignore that output
mode; do not change it as part of this deployment.

---

## 6. Close the CORS loop

1. In Render, set:

```text
ODRM_CORS_ORIGINS=https://<vercel-production-url>
```

No trailing slash, no path. For multiple origins, use a comma-separated list.

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

The backend also performs an origin check on cookie-authenticated POSTs. A missing or
mismatched `Origin` header will be rejected even if the cookie is valid.

---

## 7. Smoke checklist

1. Open the Vercel URL in a private browser window.
2. Log in with the seeded admin.
3. In DevTools, confirm the cookie:
   - name `odrm_access_token`
   - `HttpOnly`
   - `Secure`
   - `SameSite=None`
   - `Path=/api/v1`
4. Confirm `GET /api/v1/auth/me` succeeds.
5. Run a prediction with the default dashboard values. Confirm both targets and a model
   version are returned.
6. Run TEA. Confirm financials and `X-Evidence-Status: recorded`.
7. Download the report and open the PDF.
8. If the LLM key is configured, send a chat message. Otherwise record that chat is not
   configured.
9. Wait several minutes and reload to observe the accepted Render cold start.

### 7.1 Docker preflight

```powershell
docker build -f backend/Dockerfile -t valoris-api:12a .
docker run --rm --entrypoint python valoris-api:12a -c "from pathlib import Path; print(sorted(p.name for p in Path('/app/models/odrm').glob('*')))"
docker run --rm -d -p 10000:10000 -e PORT=10000 -e ODRM_ENV=local -e ODRM_DATABASE_URL=sqlite:///./odrm.db -e ODRM_JWT_SECRET=local-test-secret-at-least-32-chars --name test-12a valoris-api:12a
Start-Sleep -Seconds 5
curl.exe http://localhost:10000/health
docker rm -f test-12a
```

The image is expected to contain `ch4_conversion` and
`syngas_yield_mol_per_mol_ch4`.

---

## 8. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Login fails with a CORS error | `ODRM_CORS_ORIGINS` does not exactly match the Vercel origin | Correct the value, restart Render, retry. |
| Login returns 200 but the next request is 401 | Cookie blocked by `SameSite`/`Secure` or frontend lacks `credentials: "include"` | Set `SameSite=None`, `Secure=true`, HTTPS, and verify the frontend fetch. |
| `/predict` returns 503 | Models missing from the image | Check Docker logs and `/app/models/odrm`; rebuild with `COPY models`. |
| `/ready` returns 503 | Neon unavailable or URL wrong | Check Neon status, direct URL, SSL mode, and connection limit. |
| Render deploy loops | Database unavailable during `alembic upgrade head` | Fix the database URL/network first; the CMD runs migrations on every start. |
| Vercel calls localhost | `NEXT_PUBLIC_API_BASE_URL` missing at build time | Set it in Vercel and redeploy. |
| Chat fails | Missing/invalid LLM key or model | Set `ODRM_LLM_API_KEY` and a model available to the provider. |

---

## 9. Rollback and rotation

- **Render deploy failure:** use Render's previous deploy rollback, then fix forward.
- **Migration failure:** read the Alembic error. Do not downgrade without a tested path.
- **Bad CORS/cookie setting:** restore the previous env values and restart.
- **Wrong frontend API URL:** change `NEXT_PUBLIC_API_BASE_URL` and redeploy Vercel.
- **Secret exposure:** rotate `ODRM_JWT_SECRET` (invalidates sessions), the Neon password,
  and the LLM key; update Render and redeploy.

---

## 10. Deployment log template

Record these values after each deployment (never record secret values):

```text
Date:
Baseline commit:
Vercel production URL:
Render service URL:
Neon project/database:
Alembic head:
Model versions:
Admin email:
Chat enabled (yes/no):
Smoke result:
Operator:
```
