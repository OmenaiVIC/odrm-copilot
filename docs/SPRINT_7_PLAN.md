# Sprint 7 Plan - Beta Launch & Hardening

| | |
|---|---|
| Status | **Draft - awaiting CTO approval** |
| Date | 2026-11-06 |
| Scope | JWT authentication, protected API, rate limiting, input hardening, Docker Compose, API/user documentation |
| Dependency | Sprint 6 complete and accepted |
| Approval phrase | `AUTHORIZED: Sprint 7 implementation phase` |

> **Planning gate:** this document is the only Sprint 7 artifact allowed before approval.
> No implementation code, tests, routes, schemas, dependency installs, migrations, Dockerfiles,
> Compose files, React code, or commits are to be created until the CTO approves this plan
> with the exact phrase above.

---

## 1. Executive summary

Sprint 7 turns the working screening prototype into a controlled beta:

1. Email/password authentication with Argon2id password hashing and short-lived JWT access
   tokens.
2. Every business endpoint requires an authenticated, active user. Health, readiness, login,
   logout, and API documentation remain public.
3. Browser sessions use an HttpOnly cookie; API clients may use a bearer token. No token is
   stored in `localStorage`.
4. A conservative rate limiter protects login and expensive endpoints, with a consistent 429
   response.
5. Input hardening closes the remaining gaps: bounded free text, request-body limits, stricter
   CORS, security headers, and origin checks for cookie-authenticated state-changing requests.
6. Dockerfiles and a root `docker-compose.yml` run the frontend, API, and PostgreSQL database
   together, with migrations and health checks.
7. `docs/API_DOCUMENTATION.md` and `docs/USER_GUIDE.md` make the beta operable by a new user.

Sprint 7 is deliberately **not** a full identity platform. Refresh tokens, token revocation,
password reset, public registration, multi-tenancy, RLS, quotas, billing, and Redis-backed
distributed rate limiting are deferred and documented.

---

## 2. Sprint scope

### 2.1 In scope

- User persistence with a `users` table, SQLAlchemy 2.x repository, and Alembic migration.
- CLI-only user provisioning; no public registration endpoint.
- Argon2id password hashing through `pwdlib[argon2]`.
- HS256 JWT access tokens through `PyJWT`, with `iss`, `aud`, `exp`, `iat`, `jti`, `sub`,
  `email`, and `role` claims.
- `POST /api/v1/auth/login`, `POST /api/v1/auth/logout`, and `GET /api/v1/auth/me`.
- HttpOnly cookie session transport, plus bearer-token support for API clients.
- Authentication dependency and protection of `/predict`, `/tea`, `/market-prices`, `/chat`,
  and `/report`.
- Internal chat-to-TEA call refactor to avoid requiring an internal HTTP bearer token.
- Per-route rate limiting with `slowapi`, a custom 429 JSON handler, and an enable/disable
  setting for tests and local development.
- Security middleware: request-body size limit, security headers, no-store caching for API and
  auth responses, stricter CORS.
- Origin validation for cookie-authenticated unsafe methods (CSRF mitigation).
- Frontend auth provider, auth gate, login form, logout control, 401 handling, and credentialed
  API requests.
- Backend and frontend Dockerfiles, root `docker-compose.yml`, `.dockerignore` files,
  `.env.docker.example`, and a Compose smoke procedure.
- `docs/API_DOCUMENTATION.md`, `docs/USER_GUIDE.md`, and README updates.
- Backend and frontend tests for auth, authorization, rate limiting, input limits, and UI auth
  states.
- `docs/SPRINT_7_REPORT.md` at the end of implementation.

### 2.2 Out of scope

- Refresh tokens, token rotation, token revocation/denylists, or server-side sessions.
- Password reset, password change, email verification, MFA, SSO, or public registration.
- Role-based authorization beyond carrying a `role` claim. Every active user can use every
  business endpoint in this sprint.
- Multi-tenancy, tenant isolation, PostgreSQL RLS, per-tenant quotas, or billing/metering.
- Redis, distributed rate limiting, or multi-replica rate-limit coordination.
- OAuth providers, social login, API keys, or service-to-service mTLS.
- SOC 2, pen-test certification, or a formal third-party security audit.
- Model retraining, feature changes, or TEA math changes.
- Cloud-provider-specific deployment manifests (Render, Fly.io, Vercel, Neon, etc.).
- Email delivery, notifications, or admin UI.
- Storing the access token in `localStorage` or `sessionStorage`.
- Fixing the missing `docs/SPRINT_6_REPORT.md`; see section 4.

---

## 3. Roadmap reconciliation

`docs/strategy/MASTER_ROADMAP.md` Sprint 7 requires:

1. A security audit on the API: rate limiting, input sanitization, JWT auth.
2. `docs/API_DOCUMENTATION.md` and `docs/USER_GUIDE.md`.
3. A Docker Compose file for frontend, backend, and database.

This plan delivers those three items. It also adds the minimum user store and login UI required
to make JWT auth usable by a browser.

`docs/ARCHITECTURE.md` describes a broader Sprint 3 identity design: `/auth/login`,
`/auth/refresh`, rotating refresh tokens, Argon2 password hashing, role-based access, Postgres
RLS, and Docker Compose. Sprint 7 implements the subset needed for beta:

- Argon2id password hashing: **in scope**.
- JWT access token and `/auth/login`: **in scope**.
- `/auth/me` and `/auth/logout`: **in scope** (additive to the architecture list).
- Role claim: **in scope as data only**; role enforcement is deferred.
- Refresh and rotation: **deferred**.
- Tenant RLS: **deferred**.
- Docker Compose: **in scope**; PostgreSQL 16 is used in Compose.
- `/ready`: **in scope** as a small readiness endpoint because Compose needs it.

The architecture document should be reconciled in `docs/SPRINT_7_REPORT.md` rather than silently
rewritten during implementation.

---

## 4. Current baseline

- Git worktree is clean on branch `main`; `docs/SPRINT_7_PLAN.md` did not exist before this
  document.
- Backend baseline: **378 tests passing** via
  `.venv\Scripts\python.exe -m pytest backend/tests -q`.
- Frontend baseline: **30 tests passing** via `npm test -- --run`.
- Backend app factory: `backend/src/odrm/main.py::create_app(settings=None, *,
  agent_service=None)`.
- Existing routers are mounted under the literal `/api/v1`:
  - `POST /predict`, `POST /tea`, `GET /market-prices` in `backend/src/odrm/api/routes.py`.
  - `POST /chat` in `backend/src/odrm/api/chat.py`.
  - `POST /report` in `backend/src/odrm/api/report.py`.
  - `GET /health` in `backend/src/odrm/main.py`.
- Existing tests instantiate `create_app(...)` directly in multiple files, including
  `backend/tests/unit/test_predict_api.py`, `backend/tests/unit/test_market_prices_api.py`,
  `backend/tests/unit/test_report_api.py`, `backend/tests/integration/test_market_prices_flow.py`,
  `backend/tests/integration/test_tea_flow.py`, and `backend/tests/agent/test_chat_api.py`.
  These will need authenticated fixtures after protection is enabled.
- `backend/tests/conftest.py` blocks outbound network access and provides shared app/client
  fixtures. The session-scoped `client` fixture currently has no authentication.
- `Settings` currently has no JWT, database, auth-cookie, or rate-limit fields.
- `POST /chat` builds a `HttpTeaClient` pointing back at `ODRM_TEA_API_BASE_URL`. Protecting
  `/tea` without changing this path would make chat fail with an unauthenticated internal call.
- `HttpTeaClient` posts to `/tea` with no credentials.
- `PredictRequest.catalyst` is an unbounded free string. All other numeric fields have bounds,
  and `extra="forbid"` is already set.
- `apiFetch()` always sets `Content-Type: application/json`, does not set `credentials`, and
  does not distinguish 401 from other failures. `downloadReport()` also omits credentials.
- The frontend page renders `Dashboard` and `ChatInterface` directly with no auth gate.
- `frontend/next.config.ts` does not set `output: "standalone"`.
- No auth, users table, database, Alembic, rate limiting, Dockerfile, or Compose file exists.
- `.env.example` has no JWT, database, cookie, or rate-limit variables.
- `.gitignore` ignores `.env` and `.env.local` but not `.env.docker` or local SQLite database
  files.
- `requirements.txt` is a pip-freeze snapshot. `pyproject.toml` is the dependency source of
  truth; Docker must install from `pyproject.toml`.
- Process discrepancy: `docs/SPRINT_6_REPORT.md` is not present in the working tree even though
  commit `70fc69a docs: add Sprint 6 report and finalize ESG export` exists. That commit did not
  add the report file. This is not a Sprint 7 deliverable; it is flagged for the CTO and must not
  be silently fabricated during implementation.

---

## 5. Architecture

### 5.1 Request flow

```text
Browser
  |
  | POST /api/v1/auth/login {email, password}
  v
FastAPI auth router
  |
  +--> AuthService.authenticate(email, password)
  |       +--> UserRepository.get_by_email()
  |       +--> Argon2id verify
  |
  +--> TokenService.issue_access_token(user)
  |
  +--> Set-Cookie: odrm_access_token=...; HttpOnly; Path=/api/v1; SameSite=Lax
  +--> 200 {access_token, token_type, expires_in, user}
  |
  | GET /api/v1/auth/me (cookie)
  v
get_current_user dependency
  |
  +--> read Bearer first, else cookie
  +--> decode/validate JWT
  +--> load active user by id
  +--> 200 UserPublic, or 401 with WWW-Authenticate: Bearer
  |
  | POST /api/v1/tea (cookie, unsafe method)
  v
get_current_user dependency
  |
  +--> cookie source? validate Origin against ODRM_CORS_ORIGINS
  +--> then normal business route
```

### 5.2 Authentication design

- **Password hashing:** `pwdlib[argon2]` with `PasswordHash.recommended()` (Argon2id). Verify
  through a constant-time library path. For unknown emails, verify against a dummy hash so the
  response time does not reveal whether the account exists.
- **Tokens:** `PyJWT`, HS256 only. Decode with an explicit algorithm allowlist, issuer,
  audience, and required claims. Never accept `alg=none` or an algorithm from the token.
- **Token lifetime:** 60 minutes by default. No refresh token in this sprint.
- **Claims:** `iss`, `aud`, `iat`, `exp`, `jti` (UUID4), `sub` (user UUID), `email`, `role`.
- **Secret:** `ODRM_JWT_SECRET`, at least 32 characters. Local/dev/test may use an explicitly
  insecure development fallback; staging/production must fail fast if the secret is missing,
  short, or the development placeholder.
- **User lookup on every request:** a valid token is not enough; the user must still exist and
  be active. Deactivating a user therefore blocks future requests after the current token
  expires at most one hour later. There is no immediate revocation denylist.
- **Generic failures:** invalid credentials, unknown email, inactive user, expired token,
  malformed token, and unknown user all return the same 401 shape. Log the event without
  logging the password or token.
- **No public registration:** users are created by an operator CLI. This avoids building
  signup, email verification, abuse controls, and password reset in the same sprint.

### 5.3 Transport: cookie and bearer

- Login returns the token in JSON **and** sets a cookie.
- Browser clients use only the cookie; the frontend does not store the token.
- API clients use `Authorization: Bearer <token>` and may ignore the cookie.
- Cookie properties:
  - name: `odrm_access_token` (configurable);
  - `HttpOnly`;
  - `Path` = `ODRM_API_PREFIX` (currently `/api/v1`);
  - `SameSite=Lax` by default;
  - `Secure` controlled by `ODRM_AUTH_COOKIE_SECURE` (false for local HTTP, true for HTTPS);
  - `Max-Age` equal to the token lifetime;
  - no `Domain` attribute, so the cookie is host-only.
- The Bearer header takes precedence when both a Bearer token and a cookie are present. An
  invalid Bearer token fails the request; the server does not silently fall back to the cookie.
- `POST /auth/logout` is public and idempotent: it clears the cookie and returns 204 even if the
  token is already expired. Bearer clients discard their token themselves. Logout does not
  revoke an already-issued bearer token.
- If the frontend and API are on different sites, `SameSite=Lax` will not send the cookie.
  Deployment must either keep them on the same registrable site or set
  `ODRM_AUTH_COOKIE_SAMESITE=none` and `ODRM_AUTH_COOKIE_SECURE=true` with a CSRF review. This
  is a documented deployment constraint, not an automatic fallback.

### 5.4 CSRF and origin policy

Cookie authentication introduces CSRF risk on unsafe methods. Sprint 7 uses two layers:

1. `SameSite=Lax` blocks the cookie on cross-site unsafe requests in modern browsers.
2. When authentication comes from the cookie and the method is `POST`, `PUT`, `PATCH`, or
   `DELETE`, the request must carry an `Origin` header that exactly matches one of
   `ODRM_CORS_ORIGINS`. Missing or mismatched Origin returns 403 with code
   `CSRF_ORIGIN_REJECTED`.

Bearer-authenticated requests are not subject to the Origin check; non-browser API clients use
Bearer. `GET` and `HEAD` are unaffected. Login itself is not cookie-authenticated, but the
frontend must call it from an allowed origin; browser CORS and `SameSite` still apply.

This is intentionally smaller than a double-submit CSRF-token system. If the CTO requires
cross-site cookie deployment, a CSRF token endpoint becomes necessary and is a plan change.

### 5.5 Endpoint authorization matrix

| Method | Path | Auth | Rate limit | Notes |
|---|---|---|---|---|
| GET | `/health` | Public | None | Liveness only |
| GET | `/ready` | Public | None | DB readiness; 503 if DB is unreachable |
| GET | `/docs`, `/openapi.json` | Public | None | FastAPI documentation |
| POST | `/api/v1/auth/login` | Public | 5/minute per IP | Sets cookie; returns token |
| POST | `/api/v1/auth/logout` | Public | 30/minute per IP | Clears cookie; 204 |
| GET | `/api/v1/auth/me` | Cookie or Bearer | 60/minute per IP | Returns current user |
| POST | `/api/v1/predict` | Cookie or Bearer | 60/minute per IP | Existing contract |
| POST | `/api/v1/tea` | Cookie or Bearer | 60/minute per IP | Existing contract |
| GET | `/api/v1/market-prices` | Cookie or Bearer | 120/minute per IP | Existing contract |
| POST | `/api/v1/chat` | Cookie or Bearer | 20/minute per IP | Expensive LLM call |
| POST | `/api/v1/report` | Cookie or Bearer | 10/minute per IP | CPU-bound PDF generation |

Rate limits are per client IP. With a single API process they are enforced per process; see
section 6.5.

### 5.6 Internal chat-to-TEA call

Protecting `/tea` means the existing default `HttpTeaClient` call from `/chat` would be
unauthenticated. The recommended fix is to remove that internal HTTP hop:

- Add `InProcessTeaClient`, implementing the existing `TeaClient` protocol.
- It holds a reference to `app.state.models` and calls the existing
  `run_screening(request, models)` helper directly.
- Map `TeaInputError` to `TeaRejectedError`; map `ModelUnavailableError`, `PredictionError`, and
  `TeaCalculationError` to `TeaUnavailableError`, preserving the chat error vocabulary.
- Build the default `AgentService` after models are loaded so the in-process client has the
  model dictionary.
- Keep `HttpTeaClient` for tests and for deployments that deliberately use a separate TEA
  service, but it is no longer the default path.

This avoids a service JWT, avoids forwarding the user's token to an internal endpoint, reduces
latency, and keeps one screening implementation. It is a small architectural change that must be
called out in the Sprint 7 report.

Alternative if the CTO rejects the in-process change: mint a narrowly scoped, short-lived
service token for the internal call, with its own audience and claim. That requires additional
secret management and tests, so it is not the recommended route.

### 5.7 Rate limiting

Use `slowapi` with an in-memory storage backend for the beta:

- One module-level `Limiter` with `key_func=get_remote_address`.
- Per-route decorators rather than global middleware, so `/health`, `/ready`, and docs stay
  unthrottled.
- `ODRM_RATE_LIMIT_ENABLED` controls the limiter globally. It defaults to `true` in normal
  runtime and is set to `false` in the shared test settings; rate-limit tests explicitly enable
  it and reset storage.
- Limits are constants in `odrm/security/rate_limit.py` for Sprint 7. They are not
  environment-tunable per route yet. This keeps the limiter deterministic and avoids a module
  import dependency on Settings.
- Custom handler returns:

```json
{"detail": {"code": "RATE_LIMITED", "message": "Too many requests. Try again later."}}
```

with the 429 status and a `Retry-After` header when the limiter provides one.

- Client IP is `request.client.host`. Do not trust `X-Forwarded-For` by default. If the API is
  placed behind a trusted reverse proxy, enable the proxy's header handling at the server
  layer and document the trust boundary.
- In-memory limits are per process. The beta runs one API process. Multiple workers or replicas
  would each have their own buckets; Redis is deferred.
- Tests must reset limiter storage between tests to avoid cross-test contamination.

### 5.8 Database and user model

Use SQLAlchemy 2.x sync sessions:

- `backend/src/odrm/db.py`: engine/session factory helpers. Create the engine lazily so
  importing `odrm.main` does not require a live database.
- `backend/src/odrm/auth/models.py`: `User` mapped class and `Base`.
- `backend/src/odrm/auth/repository.py`: `UserRepository` protocol and
  `SqlAlchemyUserRepository`.
- `backend/src/odrm/auth/service.py`: authentication and token-to-user resolution.
- `backend/src/odrm/auth/router.py`: login, logout, me.
- `backend/src/odrm/auth/dependencies.py`: current-user dependency and cookie/Bearer extraction.
- `backend/src/odrm/auth/passwords.py`: Argon2id hasher wrapper.
- `backend/src/odrm/auth/tokens.py`: token issuance/validation and claims model.
- `backend/src/odrm/cli.py`: `create-user` and `list-users`.

`users` table:

| Column | Type | Notes |
|---|---|---|
| `id` | string(36) | UUID4, primary key |
| `email` | string(320) | stored lowercase, unique index |
| `password_hash` | string(255) | Argon2id hash, never returned |
| `role` | string(32) | `admin`, `engineer`, or `viewer`; default `engineer` |
| `is_active` | boolean | default true |
| `created_at` | timestamp with time zone | server-side UTC |

No `password_hash` or internal row values are exposed by API responses.

Database choices:

- **Recommended:** `ODRM_DATABASE_URL` defaults to `sqlite:///./odrm.db` for bare local
  development and tests; Docker Compose sets a `postgresql+psycopg://` URL for PostgreSQL 16.
  This keeps the existing Windows quickstart usable without installing Postgres while exercising
  a real production database in Compose.
- The repository uses portable SQLAlchemy types only. Do not add Postgres-only types before RLS
  work.
- `alembic upgrade head` is the schema path everywhere. Do not use `Base.metadata.create_all`
  in production or in the Compose entrypoint.
- Add `*.db` to `.gitignore`; do not commit local database files.
- If the CTO requires Postgres for local development too, only the default setting and README
  change; the repository and migration stay portable.

User provisioning:

```text
python -m odrm.cli create-user --email admin@example.com
python -m odrm.cli create-user --email engineer@example.com --role engineer --password-stdin
python -m odrm.cli list-users
```

- Password prompt is the default; `--password-stdin` supports automation without putting the
  password in shell history.
- Minimum password length: 12 characters. No composition rules that encourage predictable
  substitutions.
- Email is normalized to lowercase and validated with Pydantic `EmailStr`/`email-validator`.
- Repeated email returns a clear non-zero error.
- The CLI writes through the same repository and hashing code as login.

### 5.9 Input hardening and security headers

- Add `catalyst: str = Field(min_length=1, max_length=80)` and strip surrounding whitespace
  before validation. This is the only free-text field in `PredictRequest`.
- Keep `extra="forbid"` on every request schema.
- Login uses `EmailStr` and a bounded password field; never log either value.
- Add a request-body limit middleware with `ODRM_MAX_REQUEST_BYTES` (default 65,536). Enforce
  both `Content-Length` and cumulative ASGI body bytes. Return 413 with a structured detail.
- Add response headers on API/auth routes:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Referrer-Policy: no-referrer`
  - `Permissions-Policy: geolocation=(), microphone=(), camera=()`
  - `Cache-Control: no-store` for `/api/v1` and auth responses
- Tighten CORS:
  - explicit origins from `ODRM_CORS_ORIGINS`;
  - methods `GET, POST, OPTIONS`;
  - headers `Authorization, Content-Type`;
  - `allow_credentials=True`;
  - keep the existing report header exposure.
- Add equivalent basic security headers to the Next.js app through `next.config.ts` headers;
  do not add a CSP that would break Next.js without a separate compatibility review.
- Do not log request bodies, passwords, tokens, Authorization headers, or full report contents.
- Preserve existing generic 500 handling and report error mapping.

---

## 6. API design

### 6.1 Authentication endpoints

#### `POST /api/v1/auth/login`

Request:

```json
{"email": "engineer@example.com", "password": "correct horse battery staple"}
```

Success: `200 OK`

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "<uuid>",
    "email": "engineer@example.com",
    "role": "engineer"
  }
}
```

Also sets the HttpOnly cookie. Responses are `Cache-Control: no-store`.

Failure: `401 Unauthorized` with a generic detail:

```json
{"detail": {"code": "INVALID_CREDENTIALS", "message": "Invalid email or password."}}
```

The same response is used for unknown email, wrong password, and inactive user. The response must
not reveal whether the email exists.

#### `GET /api/v1/auth/me`

Requires cookie or Bearer authentication. Returns the public user object. `401` otherwise.

#### `POST /api/v1/auth/logout`

Public and idempotent. Clears the cookie and returns `204 No Content`. No response body. Does not
revoke bearer tokens.

### 6.2 Existing endpoints

Contracts, request/response bodies, error statuses, report headers, and model behavior remain
unchanged. Only the authentication dependency and rate limit are added.

- `/predict` and `/tea`: existing 422/500/503 mapping.
- `/market-prices`: existing 503 mapping.
- `/chat`: existing structured 422/503/500 shapes and request IDs.
- `/report`: existing PDF body and `Content-Disposition`, `X-Report-Id`, `X-Report-SHA256`,
  `X-Report-Generated-At` headers.
- `/health`: unchanged.
- `/ready`: new public readiness endpoint; returns 200 with `{"status": "ready"}` when the
  database answers `SELECT 1`, otherwise 503 with a generic detail.

### 6.3 Authentication errors

All protected routes return `401` with:

```json
{"detail": {"code": "UNAUTHORIZED", "message": "Authentication required."}}
```

and header `WWW-Authenticate: Bearer`.

The same shape covers missing credentials, malformed Bearer, expired JWT, wrong issuer,
wrong audience, unknown user, and inactive user. No token internals are returned.

### 6.4 Authorization errors

Cookie-authenticated unsafe requests with a missing or disallowed Origin return `403`:

```json
{"detail": {"code": "CSRF_ORIGIN_REJECTED", "message": "Request origin is not allowed."}}
```

Bearer-authenticated requests do not require Origin.

### 6.5 Rate-limit response

`429 Too Many Requests`:

```json
{"detail": {"code": "RATE_LIMITED", "message": "Too many requests. Try again later."}}
```

Include `Retry-After` when available. Rate-limit tests cover login and at least one expensive
business route.

### 6.6 OpenAPI

FastAPI's `/docs` and `/openapi.json` remain available for beta. Document the auth scheme in the
manual API guide and ensure the generated schema declares the HTTP bearer scheme. If the CTO
prefers private docs in production, add `ODRM_DOCS_ENABLED` in a follow-up; it is not required
for this sprint.

---

## 7. Frontend design

### 7.1 API client

Update `frontend/src/lib/api.ts`:

- `apiFetch` always sends `credentials: "include"`.
- Set `Content-Type: application/json` only when a body is present; avoid unnecessary
  preflights on `GET`.
- On `401`, dispatch a browser event `odrm:unauthorized` before throwing `ApiError`.
  Guard `window` access for non-browser execution.
- `downloadReport` also sends `credentials: "include"`.
- Add:

```ts
export interface AuthUser {
  id: string;
  email: string;
  role: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  user: AuthUser;
}

export async function postLogin(email: string, password: string): Promise<LoginResponse>;
export async function getCurrentUser(): Promise<AuthUser>;
export async function postLogout(): Promise<void>;
```

The frontend never reads `access_token` from `LoginResponse`; the cookie is the session.

### 7.2 Auth provider and gate

- `frontend/src/components/auth/auth-provider.tsx`:
  - state: `status: "loading" | "authenticated" | "anonymous"`, `user`;
  - on mount, call `getCurrentUser()`;
  - expose `login(email, password)` and `logout()`;
  - listen for `odrm:unauthorized`, clear the React Query cache, and set anonymous;
  - on logout, call `postLogout()` in a `finally` block and always clear local state.
- `frontend/src/app/providers.tsx`:
  - keep `QueryClientProvider` as the outer provider;
  - mount `AuthProvider` inside it so it can use `useQueryClient()`.
- `frontend/src/components/auth/auth-gate.tsx`:
  - loading state: accessible skeleton/status;
  - anonymous: render `LoginForm`;
  - authenticated: render children.
- `frontend/src/app/page.tsx`:
  - wrap `Dashboard` and `ChatInterface` in `AuthGate`.
- `frontend/src/components/auth/login-form.tsx`:
  - email and password inputs with labels, `autoComplete="email"` and
    `autoComplete="current-password"`;
  - generic error message, pending state, disabled submit while pending;
  - no registration link, no password-reset link, no token display.
- Add a compact logout control and the signed-in email to the dashboard header. Reuse the
  existing header rather than adding a second page-level header.

### 7.3 Unauthorized flow

- Any API 401 dispatches `odrm:unauthorized`.
- `AuthProvider` clears React Query cached data and switches to anonymous.
- `AuthGate` renders the login form. No redirect loop and no `window.location` reload.
- A failed login does not dispatch a global session-expired message; the form shows
  "Invalid email or password."

### 7.4 Tests

- API client: credentials on all requests, including report download; 401 event and `ApiError`
  shape; login/logout/me request shapes.
- Auth provider: bootstraps authenticated, bootstraps anonymous, login, logout, 401 event clears
  user and query cache.
- Auth gate: loading, anonymous, authenticated.
- Login form: validation, generic failure, pending state, successful callback.
- Existing dashboard/chat tests remain valid; update any fetch mocks that now assert
  `credentials`.

---

## 8. Docker and deployment

### 8.1 Backend image

`backend/Dockerfile`, build context repository root:

- `python:3.11-slim` runtime.
- `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUNBUFFERED=1`, `PIP_NO_CACHE_DIR=1`.
- Install the package from `pyproject.toml`; do not install dev dependencies.
- Copy `alembic.ini` and `backend/migrations`.
- Run as a non-root user.
- Expose 8000.
- Health check via Python standard library against `/ready` or `/health`; do not require curl.
- Entrypoint: `alembic upgrade head` followed by
  `exec uvicorn odrm.main:app --host 0.0.0.0 --port 8000`.
- Do not bake `.env`, secrets, `data/`, or model artifacts into the image.
- Models are mounted read-only at `/app/models`; the existing registry behavior returns 503 for
  missing models.

### 8.2 Frontend image

`frontend/Dockerfile`, build context `frontend/`:

- `node:22-alpine` consistent with Next.js 16 and the existing `>=20.9` engine.
- deps stage: `npm ci` using `package-lock.json`.
- builder stage: `npm run build` with `NEXT_PUBLIC_API_BASE_URL` as a build argument.
- runner stage: copy `.next/standalone`, `.next/static`, and `public`; run `node server.js` as a
  non-root user.
- `next.config.ts` adds `output: "standalone"`.
- Health check via Node's built-in `fetch`.
- Document that `NEXT_PUBLIC_API_BASE_URL` is inlined at build time; changing the public API URL
  requires rebuilding the image.

### 8.3 Compose stack

Root `docker-compose.yml`:

| Service | Image/build | Ports | Depends on | Notes |
|---|---|---|---|---|
| `db` | `postgres:16-alpine` | none by default | - | named volume, `pg_isready` health check |
| `api` | `backend/Dockerfile` | `8000:8000` | `db` healthy | migrations, non-root, `./models:/app/models:ro` |
| `web` | `frontend/Dockerfile` | `3000:3000` | `api` healthy | build arg for public API URL |

- `db`, `api`, and `web` share `.env.docker` (copied from `.env.docker.example`).
- `ODRM_DATABASE_URL` points at `db:5432`; the database port is not published by default.
- `ODRM_CORS_ORIGINS` includes `http://localhost:3000`.
- `ODRM_AUTH_COOKIE_SECURE=false` for local HTTP; production must set true.
- `.env.docker` and local database files are gitignored. No secret is committed.
- Add root `.dockerignore` and `frontend/.dockerignore`.
- Compose must build from a clean checkout with no local `.next`, `node_modules`, `.venv`, or
  model artifacts inside the build context.

### 8.4 First-run procedure

```text
copy .env.docker.example .env.docker
# set ODRM_JWT_SECRET, POSTGRES_PASSWORD, and optional LLM credentials
docker compose up --build -d
docker compose exec api python -m odrm.cli create-user --email admin@example.com
# open http://localhost:3000 and sign in
```

If model artifacts are absent, the API still starts and market/auth flows work, but screening
and report endpoints return 503. The user guide must state this clearly.

### 8.5 Compose smoke test

After build:

1. `docker compose config` validates without unresolved required variables.
2. `docker compose up --build -d` reaches healthy for `db`, `api`, and `web`.
3. `GET /health` returns 200 and `GET /ready` returns 200.
4. `POST /api/v1/auth/login` with the CLI-created user returns 200 and a cookie.
5. `GET /api/v1/auth/me` works with the cookie and with the bearer token.
6. `GET /api/v1/market-prices` works with auth and returns 401 without auth.
7. `POST /api/v1/report` returns a PDF when models are mounted; otherwise returns 503 with the
   expected model-unavailable shape.
8. `docker compose down` leaves no orphan containers. The named database volume persists unless
   explicitly removed.

---

## 9. Configuration

Add to `backend/src/odrm/core/config.py` (names are `ODRM_`-prefixed via the existing settings
model):

| Setting | Default | Purpose |
|---|---|---|
| `jwt_secret` | development-only placeholder | HS256 signing secret; production validation requires 32+ chars |
| `jwt_algorithm` | `HS256` | Fixed allowlist |
| `jwt_issuer` | `odrm-copilot` | `iss` claim |
| `jwt_audience` | `odrm-api` | `aud` claim |
| `jwt_access_token_minutes` | `60` | Token lifetime, 5-1440 |
| `database_url` | `sqlite:///./odrm.db` | SQLAlchemy URL; Compose overrides with Postgres |
| `auth_cookie_name` | `odrm_access_token` | Cookie name |
| `auth_cookie_secure` | `false` | Must be true under HTTPS |
| `auth_cookie_samesite` | `lax` | `lax`, `strict`, or `none` |
| `rate_limit_enabled` | `true` | Disable in shared test settings |
| `max_request_bytes` | `65536` | Request-body cap |
| `cors_origins` | existing | Also used for cookie-origin validation |

Production validation:

- If `env` is `staging`, `production`, or `prod`, fail at startup when `jwt_secret` is the
  development placeholder or shorter than 32 characters.
- If `auth_cookie_samesite=none`, require `auth_cookie_secure=true`.
- Document that `auth_cookie_secure=false` is only acceptable for local HTTP.

Update `.env.example` with commented auth/database/rate-limit entries. Do not put real secrets in
it.

`requirements.txt` is not updated in this sprint unless the CTO confirms it is maintained.
Docker installs from `pyproject.toml`.

---

## 10. Proposed file layout

```text
backend/src/odrm/
  auth/
    __init__.py
    models.py              # NEW: User, Base mapping
    passwords.py           # NEW: Argon2id hash/verify
    tokens.py              # NEW: JWT claims, issue/validate
    repository.py          # NEW: UserRepository protocol + SQLAlchemy implementation
    service.py             # NEW: AuthService
    dependencies.py        # NEW: current-user dependency, cookie/Bearer extraction, CSRF origin check
    router.py              # NEW: /auth/login, /auth/logout, /auth/me
  security/
    __init__.py            # NEW
    rate_limit.py          # NEW: slowapi limiter, limits, 429 handler
    middleware.py          # NEW: body-size limit, security headers
  db.py                    # NEW: engine/session factory
  cli.py                   # NEW: create-user, list-users
  agents/
    tea_client.py          # EDIT: add InProcessTeaClient
  api/
    routes.py              # EDIT: auth dependency + rate limits
    chat.py                # EDIT: auth dependency + rate limit
    report.py              # EDIT: auth dependency + rate limit
  main.py                  # EDIT: auth router, /ready, middleware, CORS tightening, in-process TEA wiring
  core/config.py           # EDIT: new settings
backend/migrations/
  env.py                   # NEW
  script.py.mako           # NEW
  versions/0001_create_users.py  # NEW
alembic.ini                # NEW
backend/tests/
  auth/
    fakes.py               # NEW: in-memory repository, test user, test secrets
    test_passwords.py      # NEW
    test_tokens.py         # NEW
    test_auth_service.py   # NEW
    test_auth_api.py       # NEW
    test_auth_dependencies.py # NEW
  security/
    test_rate_limit.py     # NEW
    test_middleware.py     # NEW
  unit/
    test_readiness.py      # NEW
    test_user_repository.py # NEW: SQLite-backed repository
  conftest.py              # EDIT: authenticated client, anonymous client, auth headers, limiter reset
  unit/test_predict_api.py # EDIT: authenticated fixture
  unit/test_market_prices_api.py # EDIT: authenticated fixture
  unit/test_report_api.py  # EDIT: authenticated fixture
  unit/test_app_boot.py    # EDIT: health/ready/auth app state
  integration/test_market_prices_flow.py # EDIT: authenticated fixture
  integration/test_tea_flow.py # EDIT: authenticated fixture
  agent/test_chat_api.py   # EDIT: authenticated helper
frontend/src/
  lib/api.ts               # EDIT: credentials, auth calls, 401 event
  lib/api.test.ts          # EDIT: new expectations
  lib/types.ts             # EDIT: auth types
  components/auth/
    auth-provider.tsx      # NEW
    auth-provider.test.tsx # NEW
    auth-gate.tsx          # NEW
    auth-gate.test.tsx     # NEW
    login-form.tsx         # NEW
    login-form.test.tsx    # NEW
  app/providers.tsx        # EDIT: mount AuthProvider
  app/page.tsx             # EDIT: AuthGate
  components/dashboard/dashboard.tsx # EDIT: user email + logout
frontend/next.config.ts    # EDIT: standalone output + security headers
frontend/Dockerfile        # NEW
frontend/.dockerignore     # NEW
backend/Dockerfile         # NEW
docker-compose.yml         # NEW
.dockerignore              # NEW
.env.docker.example        # NEW
.env.example               # EDIT: auth/database/rate-limit examples
.gitignore                 # EDIT: .env.docker, *.db
pyproject.toml             # EDIT: runtime dependencies and Alembic config
README.md                  # EDIT: auth-aware quickstart and Docker instructions
docs/API_DOCUMENTATION.md  # NEW
docs/USER_GUIDE.md         # NEW
docs/SPRINT_7_REPORT.md    # NEW at the end of implementation (Phase 5)
```

Dependency additions after approval:

- Runtime: `PyJWT`, `pwdlib[argon2]`, `email-validator`, `SQLAlchemy`, `psycopg[binary]`,
  `alembic`, `slowapi`.
- Test-only: none required beyond the existing suite; tests use SQLite and the standard library.
- Keep `pyproject.toml` authoritative. Do not regenerate `requirements.txt` blindly.

No other production files are modified.

---

## 11. Test strategy (TDD)

Every slice is written test-first and committed only after the relevant tests pass, per
`docs/SPRINT_WORKFLOW.md`. The shared test app uses an in-memory user repository, so the default
test suite does not require PostgreSQL or Docker.

### 11.1 Auth primitives

`test_passwords.py`:

- hash differs from plaintext and verifies correctly;
- wrong password fails;
- two hashes of the same password differ (salt);
- dummy verification does not raise.

`test_tokens.py`:

- issued token has the expected claims and expiry;
- valid token round-trips to claims;
- expired token fails;
- wrong secret, wrong issuer, wrong audience, malformed token, missing required claim, and
  `alg=none` all fail;
- `jti` is unique per issue;
- token service accepts an injected clock so expiry tests are deterministic.

### 11.2 User repository

`test_user_repository.py`:

- create and fetch by id and lowercase email;
- duplicate email is rejected;
- inactive user is preserved and returned;
- SQLite-backed repository uses a temporary database per test;
- password hash is not exposed in public serialization.

### 11.3 Auth service and dependencies

- valid credentials return the user and issue a token;
- wrong password, unknown email, and inactive user return the same failure;
- email normalization is applied;
- token resolution rejects expired, tampered, unknown-user, and inactive-user tokens;
- Bearer takes precedence over cookie;
- invalid Bearer does not fall back to a valid cookie;
- cookie-authenticated unsafe request with missing/disallowed Origin returns 403;
- Bearer-authenticated unsafe request with no Origin succeeds;
- cookie-authenticated GET does not require Origin;
- missing credentials return 401 with `WWW-Authenticate: Bearer`.

### 11.4 Auth API

`test_auth_api.py`:

- login success: 200, token shape, user shape, `Set-Cookie` with `HttpOnly`, `Path`,
  `SameSite`, `Max-Age`, and expected `Secure` flag;
- login failure: 401 generic, no cookie, no email enumeration;
- inactive user: same 401;
- `/auth/me`: cookie and Bearer success, missing/expired/tampered 401;
- logout: 204, clears cookie, idempotent with no auth;
- login rate limit: sixth request in the window returns 429 with `Retry-After`;
- login response is `Cache-Control: no-store`.

### 11.5 Protected routes

Update existing API tests and add auth-specific protection tests:

- every business endpoint returns 401 without credentials;
- every business endpoint works with a valid test cookie and with a valid bearer token;
- existing 422/500/503 behavior is unchanged once authenticated;
- report headers remain intact;
- `/health`, `/ready`, `/docs`, and `/openapi.json` are public;
- `/ready` returns 503 when the repository ping fails;
- chat still succeeds through the in-process TEA client with the stubbed models;
- internal `/tea` protection does not break chat.

### 11.6 Rate limiting and middleware

`test_rate_limit.py`:

- login limit triggers 429 with the structured detail and `Retry-After`;
- a per-route business limit triggers independently of login;
- `/health` and `/ready` are not rate-limited;
- limiter reset isolates tests;
- disabled mode never returns 429.

`test_middleware.py`:

- request bodies at or below the limit pass;
- bodies above the limit return 413 without calling the route;
- `Content-Length` and streamed/chunked bodies are both covered;
- security headers are present on API/auth responses;
- `Cache-Control: no-store` is present;
- CORS allowed origin/method/header behavior is correct;
- report headers remain exposed.

### 11.7 Backend regression

All existing tests must still pass after the authenticated fixture update. The baseline is 378
passing tests; the final count will grow. No test may be skipped or deleted to make the suite
green.

### 11.8 Frontend tests

- `api.test.ts`: credentials on every request including `downloadReport`; 401 event; auth call
  shapes; no token storage.
- `auth-provider.test.tsx`: bootstrap authenticated/anonymous, login, logout, unauthorized event
  clears query cache.
- `auth-gate.test.tsx`: loading, login, authenticated children.
- `login-form.test.tsx`: labels, validation, pending state, generic error, successful submit.
- Existing tests: update fetch mocks for `credentials`; keep dashboard/chat behavior unchanged.

### 11.9 Docker and quality gates

- `docker compose config`
- `docker compose build`
- Compose smoke procedure in section 8.5
- Backend: `pytest backend/tests -q`
- Backend lint/type: `ruff check backend/src backend/tests`;
  `mypy backend/src/odrm scripts`
- Frontend: `npm test`, `npm run typecheck`, `npm run lint`
- Optional but recommended: `pip-audit` and `npm audit --omit=dev`; record findings rather than
  auto-upgrading unrelated packages.

No skipped tests, no network access in the default suite, no real secrets in tests or images.

---

## 12. Implementation outline

Each step is test-first. Do not start step 2 until step 1's tests pass. Commit after each
successfully tested feature only after the CTO authorization phrase.

1. **Approval gate.** Wait for `AUTHORIZED: Sprint 7 implementation phase`.
2. **Dependencies and settings.** Add runtime dependencies and settings; write settings
   validation tests.
3. **Auth primitives.** Password hashing and JWT tests, then implementation.
4. **User persistence.** SQLite repository tests, model, migration, and CLI tests.
5. **Auth service and dependency.** Auth service, cookie/Bearer extraction, CSRF origin check,
   and 401 behavior.
6. **Auth API.** Login/logout/me, cookie attributes, rate-limit hook, and tests.
7. **Protect routes and refactor internal TEA.** Add dependencies to existing routes; add
   `InProcessTeaClient`; update all direct-app tests to authenticated fixtures.
8. **Rate limiting and middleware.** `slowapi`, 429 handler, body limit, security headers, CORS
   tightening, readiness endpoint.
9. **Frontend auth.** API client, provider, gate, login form, logout, 401 handling, tests.
10. **Docker.** Backend/frontend Dockerfiles, standalone output, Compose, env example,
    gitignore/dockerignore, build and smoke validation.
11. **Docs.** API documentation, user guide, README quickstart and auth examples.
12. **Final gates.** Run all backend/frontend gates and the Compose smoke; fix regressions.
13. **Report and commit.** Write `docs/SPRINT_7_REPORT.md` with what was built, test results,
    deviations, and known issues; commit only after gates are green.

---

## 13. Security, privacy, and observability

- Passwords are hashed with Argon2id and never logged, returned, or included in errors.
- Tokens are never logged, placed in URLs, or stored in `localStorage`/`sessionStorage`.
- Login failures and authorization failures return generic messages to prevent enumeration.
- Bearer tokens are accepted only over HTTPS in production; local HTTP is development-only.
- Cookie flags are explicit and covered by tests.
- CORS is restricted to configured origins; cookie-authenticated unsafe requests require a
  matching Origin.
- Request bodies are size-capped; free text is bounded and stripped.
- Rate limits protect login and expensive routes, but are per-process and IP-based in this
  sprint. This is a beta limitation, not a claim of DDoS protection.
- No PII is added to logs. Log auth outcomes, rate-limit events, request IDs, and endpoint
  outcomes without emails, passwords, tokens, or request bodies.
- Report content remains in memory and is not persisted. The existing report digest semantics
  are unchanged.
- Docker images run as non-root and do not contain secrets or model artifacts.
- `.env`, `.env.docker`, local databases, and model artifacts remain untracked.
- The API's `/health` and `/ready` responses contain only status/env-level information.
- No third-party security certification is implied by this sprint.

---

## 14. Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Protecting `/tea` breaks chat's internal HTTP call | High | High | Use `InProcessTeaClient`; test chat with stubbed models before and after protection |
| Existing tests fail because every route now needs auth | High | Medium | Authenticated `client` fixture, anonymous fixture, helper for direct `create_app` tests; update all constructors in one tested slice |
| Cookie auth is broken across frontend/API origins | Medium | High | Same-site deployment assumption; `SameSite`/`Secure` settings; document cross-site requirements; test CORS/cookie flags |
| CSRF gap from cookie auth | Medium | High | `SameSite=Lax` plus Origin validation for unsafe cookie requests; Bearer bypass; tests |
| In-memory rate limiting is bypassed by multiple workers | Medium | Medium | Run one API process for beta; document Redis/multi-replica work as deferred |
| Rate limiting misfires behind a proxy | Medium | Medium | Do not trust `X-Forwarded-For` by default; document trusted-proxy setup |
| `slowapi` global state leaks between tests | Medium | Low | Disable by default in test settings; autouse reset fixture; explicit rate-limit tests |
| SQLite/Postgres behavior drift | Medium | Medium | Portable types; repository tests on SQLite; Compose smoke on Postgres; no Postgres-only features |
| Alembic migration fails at container startup | Medium | High | `depends_on db healthy`; migration is explicit; smoke test; clear user-guide troubleshooting |
| JWT secret missing or weak in deployment | Medium | High | Production startup validation; `.env.docker.example` guidance; no default in Compose |
| Token theft via XSS remains possible despite HttpOnly cookie | Low | High | No token in JS storage; standard security headers; no CSP claim; XSS review remains a follow-up |
| Logout does not revoke bearer tokens | High | Medium | Document token lifetime and client responsibility; revocation deferred |
| Docker build is large or slow due to ML dependencies | Medium | Medium | Runtime-only install; `.dockerignore`; no dev deps; model volume outside image |
| `NEXT_PUBLIC_API_BASE_URL` is baked at build time | High | Medium | Document rebuild requirement; Compose build arg; cloud deployment note |
| Model artifacts absent in Docker | Medium | Medium | Read-only volume; clear 503 behavior; user-guide prerequisite check |
| `requirements.txt` drifts from `pyproject.toml` | Medium | Low | `pyproject.toml` authoritative; do not regenerate without CTO confirmation |
| Frontend auth gate changes existing component tests | Medium | Low | Keep dashboard/chat presentational; test auth at provider/gate level; update mocks |
| Argon2 hashing slows tests | Low | Low | Hash one session fixture user; use real parameters; no per-test hashing loop |
| Missing Sprint 6 report confuses the record | Low | Low | Flag the discrepancy; do not fabricate a report; produce Sprint 7 report normally |

---

## 15. Assumptions

- The beta is single-tenant and single-process. Every active user may use every business
  endpoint; role is recorded but not enforced.
- Users are provisioned by an operator; there is no self-service signup or password reset.
- Access tokens last 60 minutes. Refresh, rotation, revocation, and server-side logout are
  deferred.
- The frontend and API are served on the same registrable site in the default deployment, so a
  `SameSite=Lax` cookie works. Cross-site deployment requires cookie and CSRF changes.
- PostgreSQL 16 is the deployment database in Compose; SQLite is the recommended zero-setup
  local default. The repository stays portable.
- Model artifacts are mounted into the API container; images do not ship model files.
- `pyproject.toml` is the dependency source of truth; `requirements.txt` is not authoritative.
- The API documentation and `/docs` remain public for beta.
- Basic security headers and rate limiting are appropriate for beta; this is not a claim of
  production-grade DDoS protection.
- The existing screening, TEA, report, and chat contracts do not change.
- The missing Sprint 6 report is a process discrepancy and is not recreated as part of Sprint 7.

---

## 16. Open questions for CTO review

1. **Auth stack:** approve Argon2id + PyJWT HS256, 60-minute access tokens, no refresh, and
   CLI-only user provisioning?
2. **Database default:** approve SQLite for bare local development with PostgreSQL 16 in
   Compose, or require PostgreSQL for all environments?
3. **Rate limiter:** approve `slowapi` with in-memory, per-IP limits for a single-process beta,
   or require a Redis-backed limiter now?
4. **Cookie/CSRF model:** approve HttpOnly `SameSite=Lax` cookies plus Origin validation for
   unsafe methods, or require a full CSRF-token flow?
5. **Internal TEA call:** approve replacing the default chat-to-`/tea` HTTP call with
   `InProcessTeaClient`, or require a service JWT instead?
6. **Token in login response:** approve returning the bearer token in JSON for API clients while
   the browser uses the cookie?
7. **Logout semantics:** approve public, idempotent logout that only clears the cookie, with
   bearer-token revocation deferred?
8. **Roles:** approve recording `admin`/`engineer`/`viewer` without enforcing role permissions in
   this sprint?
9. **Public docs:** approve keeping `/docs` and `/openapi.json` public for beta?
10. **Dependency file:** confirm `requirements.txt` should not be regenerated, with
    `pyproject.toml` remaining authoritative?
11. **Pre-existing report gap:** should the missing `docs/SPRINT_6_REPORT.md` be reconstructed
    separately, or only noted in the Sprint 7 report?

Recommended defaults are the first option in each question.

---

## 17. Acceptance criteria

- A user created by the CLI can log in with email/password and receives a valid JWT plus an
  HttpOnly cookie.
- `/auth/me` works with either the cookie or a bearer token; logout clears the cookie.
- Every business endpoint returns 401 without valid credentials and preserves its existing
  contract when authenticated.
- Expired, tampered, wrong-issuer, wrong-audience, and unknown-user tokens are rejected with the
  same generic 401 shape and `WWW-Authenticate: Bearer`.
- Cookie-authenticated unsafe requests with a missing/disallowed Origin are rejected; Bearer
  requests are unaffected.
- Login and expensive routes return 429 after their configured limits, with `Retry-After` and a
  consistent JSON detail; health/readiness are exempt.
- Oversized request bodies return 413; the `catalyst` field is bounded and stripped; security
  headers and `Cache-Control: no-store` are present on API/auth responses.
- Chat continues to produce screening results after `/tea` becomes protected, using the
  in-process TEA client.
- Frontend bootstraps auth, shows a login form when anonymous, shows the app when authenticated,
  logs out cleanly, clears query data on 401/logout, and sends credentials on every API call.
- `docker compose config`, `docker compose build`, and the smoke procedure succeed; the stack
  runs the frontend, API, and PostgreSQL database together; migrations run before the API starts.
- `docs/API_DOCUMENTATION.md` and `docs/USER_GUIDE.md` are accurate and complete enough for a new
  operator.
- Backend pytest, ruff, and mypy pass; frontend tests, typecheck, and lint pass.
- No secrets, `.env.docker`, local databases, or model artifacts are committed.
- `docs/SPRINT_7_REPORT.md` is produced at the end of implementation with test results,
  deviations, and known issues.

---

## 18. Approval

This plan is submitted for CTO review. No Sprint 7 implementation work will begin until the CTO
replies with exactly:

`AUTHORIZED: Sprint 7 implementation phase`

Requested decisions are listed in section 16; the recommended defaults are marked there.
