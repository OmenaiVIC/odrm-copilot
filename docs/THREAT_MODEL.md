# Valoris Threat Model - Deployment Scope

| | |
|---|---|
| Status | Sprint 12A deployment-scoped baseline |
| Scope | Public Vercel + Render + Neon deployment and optional LLM boundary |
| Last reviewed | 2026-11-28 |
| Related | `docs/DATAFLOW.md`, `docs/SECURITY.md`, `docs/DEPLOYMENT.md` |

This document covers the trust boundaries introduced by exposing Valoris to the public
internet. It does not replace a full product security review. Application-internal threats
that predate this deployment (for example, evidence-chain correctness and model quality)
are covered by their existing tests and sprint records.

---

## 1. System and scope

### 1.1 In scope

- Reviewer browser to Vercel over HTTPS.
- Vercel to Render API over HTTPS.
- Render to Neon Postgres over TLS.
- Render to an optional LLM provider over HTTPS.
- Build and deploy pipeline for the Docker image.
- Admin account creation and session handling.
- Runtime model artifacts shipped in the image.

### 1.2 Out of scope

- Physical security of Vercel, Render, Neon, or the LLM provider.
- Full source-code supply-chain audit beyond the existing dependency pins.
- Regulatory certification or investment-grade financial validation.
- Multi-tenant isolation beyond the current single-admin/demo use.
- Denial-of-service resistance beyond free-tier platform limits.

---

## 2. Assets

| Asset | Sensitivity | Where it lives | Why it matters |
|---|---|---|---|
| Admin email and password hash | High | Neon `users` table | Grants access to the demo and evidence features. |
| JWT signing secret | Critical | Render secret env | Forgery would allow session impersonation. |
| Neon connection string | Critical | Render secret env | Direct database access. |
| LLM API key | High | Render secret env | Billing and provider access. |
| Session cookie | High | Reviewer browser | Bearer-equivalent access to the API. |
| Prediction/TEA inputs | Medium | Request bodies; Neon evidence rows | May contain commercial assumptions. |
| Generated reports | Medium | API response | Intended for reviewer download. |
| Model artifacts | Medium | Docker image | Tampering changes predictions. |
| Application logs | Medium | Render logs | May contain request metadata; must not contain secrets. |

---

## 3. Trust boundaries

| ID | Boundary | Controls |
|---|---|---|
| TB1 | Browser -> Vercel | HTTPS, Vercel platform TLS, Next.js security headers. |
| TB2 | Vercel -> Render | HTTPS, CORS allowlist, credentialed requests, JSON API. |
| TB3 | Render -> Neon | TLS (`sslmode=require`), secret connection string, least-privilege DB user. |
| TB4 | Render -> LLM provider | HTTPS, provider API key, prompt/response guardrails, no secrets in prompts. |
| TB5 | Build context -> image | `.dockerignore`, committed model artifacts, pinned dependencies, non-root runtime user. |
| TB6 | Operator -> cloud dashboards | Platform account security, MFA where available, no shared credentials. |

---

## 4. Threats and mitigations

### 4.1 Credential and session threats

| Threat | Impact | Mitigation | Verification |
|---|---|---|---|
| Credential stuffing or password guessing | Unauthorized access | Argon2 password hashing; login rate limiting; strong seeded password; no public signup. | Auth tests; login rate-limit test; manual review of seeded account. |
| Session theft via JavaScript | Account takeover | `HttpOnly` cookie; no token in `localStorage`. | Browser DevTools cookie inspection. |
| Session sent over HTTP | Session interception | `Secure` cookie; HTTPS-only deployment; HSTS at platform edge where available. | Cookie flags; HTTPS URLs. |
| CSRF on cookie-authenticated POSTs | Unauthorized state changes | `SameSite=None` plus explicit `Origin` allowlist check; CORS credentials restricted to the Vercel origin. | Preflight check; CSRF rejection test. |
| JWT forgery | Full API access | 32+ character secret; production validator rejects the development placeholder; secret stored only in Render. | Config tests; secret rotation runbook. |
| Session fixation | Account takeover | Server-issued JWT after successful login; no client-supplied session ID. | Auth flow review. |

### 4.2 Network and configuration threats

| Threat | Impact | Mitigation | Verification |
|---|---|---|---|
| CORS wildcard with credentials | Cross-origin data theft | Exact origin allowlist; `allow_credentials=True`; no `*`. | Preflight check with Vercel origin. |
| Wrong frontend API URL | Requests to attacker or localhost | Build-time env is explicit; Vercel env is public but reviewed; no runtime fallback in production. | Vercel build log and browser network tab. |
| Database exposed publicly | Data breach | Neon manages network access; use TLS; keep the URL secret; rotate on exposure. | Neon dashboard review. |
| Pooler/migration mismatch | Failed or partial deploy | Direct non-pooler URL for app and Alembic. | Migration preflight. |
| Missing models in image | Predict/TEA/report fail | Commit artifacts; `COPY models`; startup log check; `/predict` smoke test. | Docker image inspection; authenticated prediction. |
| Container runs as root | Larger blast radius | Runtime `USER appuser`; only required files copied. | Dockerfile review; `id` in container. |
| Build context leaks local files | Secret or data exposure | Root `.dockerignore` excludes `.git`, `.env*`, `data/`, `frontend/`, tests, and caches. | `docker build` context review. |

### 4.3 Data and privacy threats

| Threat | Impact | Mitigation | Verification |
|---|---|---|---|
| Admin password stored in plaintext | Credential breach | Argon2 hash only; password entered via stdin; never logged. | CLI review; database inspection. |
| Commercial assumptions retained indefinitely | Confidentiality/privacy | Demo data only; document retention; delete Neon project when the demo ends. | `docs/SECURITY.md`. |
| Secrets in logs | Credential leak | Do not log env values; review Render logs; redact error details. | Log review after smoke test. |
| Report contains sensitive assumptions | Unintended disclosure | Reviewer downloads are intentional; no public object storage; response is authenticated. | Auth tests. |
| Evidence rows tampered with | Loss of auditability | Existing hash-chain/Merkle design; database access restricted to the app. | Existing evidence tests. |

### 4.4 LLM boundary threats

| Threat | Impact | Mitigation | Verification |
|---|---|---|---|
| Prompt injection changes tool behavior | Unsafe or misleading output | Existing guardrails and tool validation; TEA remains deterministic; no arbitrary code execution. | Existing chat/guardrail tests. |
| Secrets included in prompts | Credential leak | System prompt excludes secrets; user input is untrusted; no env interpolation into prompts. | Code review. |
| Provider outage or quota exhaustion | Chat unavailable | Chat is optional; prediction/TEA/report do not depend on the LLM. | Smoke test with and without a key. |
| Model output treated as financial advice | Misleading decision | UI/report disclaimer; TEA is a screening tool, not investment-grade. | Existing copy review. |

### 4.5 Availability threats

| Threat | Impact | Mitigation | Verification |
|---|---|---|---|
| Render free-tier cold start | Demo delay | Accepted; document the 30-60 second first request. | Manual reload test. |
| Neon idle suspension | First-query delay | Accepted; `/ready` exposes DB state. | Manual `/ready` test. |
| Request flooding | Free-tier exhaustion | Existing in-memory rate limiting; platform limits. | Rate-limit tests. |
| Deploy-time migration failure | Service unavailable | Run migrations locally first; startup logs; rollback plan. | Migration preflight. |

---

## 5. Residual risks

| Risk | Residual level | Acceptance |
|---|---|---|
| Free-tier cold starts and limited resources | Medium | Accepted for grant demo; not an SLA. |
| Single admin account | Medium | Accepted for demo; no public registration. |
| LLM provider sees prompt content | Medium | Accepted only when chat is enabled; documented for reviewers. |
| No independent penetration test | Medium | Deployment-scoped controls only; full review deferred. |
| Neon/Render/Vercel platform compromise | Low/Medium | Relies on provider security; out of direct control. |

---

## 6. Security requirements for this deployment

1. No secret in Git, Docker image, frontend bundle, logs, or documentation.
2. `ODRM_ENV=production` and a unique 32+ character JWT secret.
3. Exact CORS origin; no wildcard with credentials.
4. `HttpOnly`, `Secure`, `SameSite=None` session cookie; `Path=/api/v1`.
5. Non-root container runtime; only required files in the image.
6. Model artifacts copied from the reviewed repository, not downloaded at runtime.
7. `/health` public and minimal; `/ready` reveals only readiness, not configuration.
8. Admin password entered via stdin and stored only as Argon2 hash.
9. LLM key optional; chat must fail closed and must not block prediction/TEA/report.
10. Rollback and secret-rotation steps documented in `docs/DEPLOYMENT.md`.

---

## 7. Review and change control

Review this threat model when any of the following changes:

- A new external service or data store is added.
- Authentication, authorization, cookies, or CORS changes.
- The LLM provider or prompt/tool boundary changes.
- The deployment platform or public URL changes.
- A security finding or incident occurs.

Record the review date and the reviewer in the change that modifies this file.
