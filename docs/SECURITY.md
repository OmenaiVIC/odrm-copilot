# Valoris Security - Deployment Scope

| | |
|---|---|
| Status | Sprint 12A deployment-scoped baseline |
| Last reviewed | 2026-11-28 |
| Related | `docs/THREAT_MODEL.md`, `docs/DATAFLOW.md`, `docs/DEPLOYMENT.md` |

This document defines the minimum security controls for the public Valoris demo. It is
not a complete security program. It covers secrets, admin data, deployment hardening,
retention, and incident response.

---

## 1. Security principles

1. **Least privilege:** the app uses a dedicated database user; the container runs as a
   non-root user; only required files are copied into the image.
2. **Secrets out of Git:** secrets live only in Render/Vercel environment settings or a
   local shell for one-time migration/seed.
3. **Fail closed:** missing models, missing database connectivity, or missing LLM
   configuration must not silently bypass validation.
4. **Exact origins:** credentialed CORS uses an explicit Vercel origin, never `*`.
5. **No public admin creation:** the admin is seeded manually; there is no public signup.
6. **Demo data only:** do not enter confidential operator data into the public demo.

---

## 2. Secret management

### 2.1 Secret inventory

| Secret | Storage | Rotation trigger |
|---|---|---|
| `ODRM_DATABASE_URL` | Render secret env | Neon password rotation, suspected exposure, project move. |
| `ODRM_JWT_SECRET` | Render secret env | Suspected exposure, operator change, incident response. |
| `ODRM_LLM_API_KEY` | Render secret env | Provider rotation, suspected exposure, demo teardown. |
| Admin password | Password manager / operator | Suspected exposure, operator change. |

### 2.2 Rules

- Never commit `.env`, `.env.local`, `.env.docker`, or any file containing a real secret.
- Never put a secret on a command line where it can appear in shell history or process
  listings. Use `--password-stdin` for the admin password.
- Never log secret values. Review Render logs after deployment for accidental leakage.
- Do not bake secrets into the frontend; `NEXT_PUBLIC_*` values are public.
- Generate the JWT secret with a cryptographically secure random source:

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

- Use a distinct JWT secret per environment. Never reuse the development placeholder.
- Store the Neon URL with `sslmode=require` and use the direct host for migrations.

### 2.3 Rotation

1. Generate the new value.
2. Update Render's environment variable.
3. Redeploy/restart Render.
4. Verify `/health`, `/ready`, login, and prediction.
5. Revoke the old value at the provider.
6. Record the rotation date in the deployment log; never record the value.

Rotating `ODRM_JWT_SECRET` invalidates all existing sessions.

---

## 3. Admin account and personal data

### 3.1 Admin data

The demo stores:

- Admin email.
- Argon2 password hash.
- Role (`admin`, `commercial`, or `viewer`).
- Authentication/audit metadata required by the application.

The demo does not collect end-user PII, payment data, or production operator data. The
admin email should be a dedicated demo address, not a personal or corporate mailbox.

### 3.2 Password policy

- Minimum 12 characters, enforced by the CLI.
- Use a generated password or password-manager secret.
- Do not share the admin password in chat, tickets, or documentation.
- Seed with stdin, not argv:

```powershell
$plain | .\.venv\Scripts\python.exe -m odrm.cli create-user `
  --email admin@valoris.example --role admin --password-stdin
```

### 3.3 Retention and teardown

- Keep the demo database only for the grant-review window.
- Delete the Neon project or database when the demo ends.
- Delete the Render service and Vercel project.
- Revoke the LLM key.
- Remove local environment files and shell variables.
- Record the teardown date in the deployment log.

---

## 4. Deployment hardening checklist

### 4.1 Backend

- [ ] `ODRM_ENV=production`.
- [ ] `ODRM_JWT_SECRET` is 32+ characters and not the development placeholder.
- [ ] `ODRM_DATABASE_URL` uses `postgresql+psycopg://` and `sslmode=require`.
- [ ] `ODRM_CORS_ORIGINS` is the exact Vercel production origin, no trailing slash.
- [ ] `ODRM_AUTH_COOKIE_SECURE=true`.
- [ ] `ODRM_AUTH_COOKIE_SAMESITE=none`.
- [ ] `ODRM_API_PREFIX` remains `/api/v1`.
- [ ] Models are present in `/app/models/odrm`.
- [ ] Container runs as `appuser`, not root.
- [ ] `/health` is public and minimal; `/ready` requires the database.
- [ ] Rate limiting is enabled.
- [ ] LLM key is absent or scoped to the demo project.

### 4.2 Frontend

- [ ] `NEXT_PUBLIC_API_BASE_URL` points to the Render API + `/api/v1`.
- [ ] No secret is present in the Vercel environment or bundle.
- [ ] `credentials: "include"` is used for API requests.
- [ ] Security headers from `next.config.ts` remain enabled.
- [ ] The Vercel production URL is the only allowed CORS origin.

### 4.3 Database

- [ ] Neon project is dedicated to the demo.
- [ ] The app uses a least-privilege database user, not the owner account where possible.
- [ ] Migrations run before the first Render deploy.
- [ ] The admin is seeded manually.
- [ ] No production or confidential data is loaded.
- [ ] A teardown date is recorded.

### 4.4 Repository and image

- [ ] `.env` and `.env.*` are ignored; only examples are tracked.
- [ ] Root `.dockerignore` excludes `.git`, `.env*`, `data/`, `frontend/`, tests, and
  caches.
- [ ] `models/odrm/**/*.joblib` is intentionally tracked; metadata JSON is unchanged.
- [ ] No secret appears in `git status`, `git diff`, or the image history.
- [ ] Dependencies are pinned by the existing lock/requirements files; no new dependency
  was added for this deployment.

---

## 5. Logging and monitoring

- Render logs are the primary runtime signal.
- Log startup model-loading lines and migration completion.
- Do not log request bodies, cookies, authorization headers, passwords, or API keys.
- Review logs after the smoke test for leaked secrets or stack traces containing
  connection strings.
- Use `/health` for Render's health check and `/ready` for manual database verification.
- Free-tier cold starts are expected; do not treat them as a security incident.

---

## 6. Incident response

### 6.1 Suspected secret exposure

1. Rotate the affected secret immediately (JWT, Neon password, or LLM key).
2. Redeploy/restart Render.
3. Revoke the old credential at the provider.
4. Review Render, Neon, and provider audit logs for unauthorized use.
5. If admin credentials are involved, disable/reset the admin account.
6. Record the incident, actions, and timeline in the deployment log.
7. Notify the CTO and, if required, the affected provider.

### 6.2 Suspected unauthorized access

1. Rotate `ODRM_JWT_SECRET` to invalidate all sessions.
2. Reset the admin password.
3. Review Neon access and evidence rows for unexpected changes.
4. Review Render logs for unusual origins, request rates, or errors.
5. If data was exposed, follow the project's disclosure process and notify the CTO.

### 6.3 Model or image tampering

1. Stop the Render service.
2. Rebuild from the reviewed commit.
3. Verify the model artifact checksums against the tracked metadata.
4. Redeploy and re-run the prediction smoke test.
5. Record the incident and the commit used for recovery.

### 6.4 LLM provider incident

1. Remove or rotate `ODRM_LLM_API_KEY`.
2. Disable chat if the provider is compromised.
3. Confirm prediction, TEA, and report remain available.
4. Follow the provider's incident guidance.

---

## 7. Out of scope

- Formal penetration testing.
- SOC 2, ISO 27001, or regulatory certification.
- Multi-tenant authorization and row-level isolation.
- Endpoint detection/response, SIEM, or 24/7 monitoring.
- Investment-grade financial validation.

These require a separate security program and budget. This document is the minimum
deployment baseline for the grant demo.
