# Sprint 7 — Beta Launch & Hardening: Review Note

| | |
|---|---|
| Status | **Complete** |
| Date | 2026-11-06 |
| Scope | JWT Auth, Rate Limiting, Input Hardening, Docker Containerization, UI Rebrand |

## 1. Objectives vs. outcome
| Plan Step | Outcome |
|---|---|
| 1. Auth Primitives (Argon2, JWT) | Done |
| 2. User Database & Repository | Done |
| 3. Auth Service & Dependencies | Done |
| 4. Auth API (`/login`, `/logout`, `/me`) | Done |
| 5. Protect Routes & In-Process TEA | Done |
| 6. Rate Limiting & Security Headers | Done |
| 7. Frontend Auth (Login, Provider, Gate) | Done |
| 8. Docker (Compose, Backend, Frontend) | Done |
| 9. Documentation (API, User Guide, Security) | Done |

## 2. Automated Gate Evidence
*   **Backend:** `pytest` → 457 passed. `ruff` & `mypy` clean.
*   **Frontend:** `npm run test` → 30 passed. `lint`, `typecheck`, and `build` clean.
*   **Docker:** `docker compose config` validates.

## 3. Architecture & Hardening
*   **Auth:** Argon2id password hashing, HS256 JWT tokens stored in HttpOnly cookies.
*   **CSRF Defense:** Strict Origin validation for cookie-authenticated unsafe methods.
*   **In-Process TEA:** Refactored the chat agent to call the TEA engine in-process, removing the internal HTTP hop and securing the `/tea` endpoint.
*   **Rate Limiting:** `slowapi` enforces per-IP limits (Login: 5/min, Chat: 20/min).
*   **Input Limits:** Request bodies capped at 64KB; catalyst free-text bounded to 80 chars.
*   **UI Rebrand:** Transitioned from "ODRM Copilot" to the "VALORIS | ODRM Copilot" brand identity with a modernized emerald/teal color palette.

## 4. Deviations & Deferred Work
*   **CSP Deferred:** A strict Content Security Policy was deferred to Sprint 8 to avoid breaking Next.js hydration. This is documented in `docs/SECURITY.md`.
*   **Turbopack CSS Warning:** A benign warning (`Unknown at rule: @theme`) is logged during the Next.js build due to Tailwind v4 syntax. The build succeeds and the CSS compiles correctly.
*   **Docker Live Smoke Test:** `docker compose up` was structurally verified, but a full live boot awaits the cloud deployment phase.

## 5. Known limitations
*   JWT tokens are stateless and cannot be revoked until Sprint 9 (Redis denylist).
*   Role enforcement (RBAC) is deferred to Sprint 8.

## 6. Known Issues & Backlog (Discovered during Manual Testing)
During the final manual test, two UX limitations were identified. Both are deferred to the Sprint 8 Pilot phase:
1. **Single-Turn Chat Memory:** The `/api/v1/chat` endpoint is stateless. The AI cannot answer follow-up questions based on previous messages in the thread. (Requires passing the `messages[]` array and adding session management).
2. **Markdown Rendering:** The AI outputs raw Markdown (e.g., `**bold**`, `### headers`). The frontend currently renders this as raw text. (Requires installing a library like `react-markdown` to parse the output).