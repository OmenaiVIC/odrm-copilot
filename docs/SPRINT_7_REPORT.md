# Sprint 7 — Beta Launch & Hardening: Review Note

| | |
|---|---|
| Status | **Complete** |
| Date | 2026-11-06 |
| Scope | JWT Auth, Rate Limiting, Docker, UI Rebrand, Agent Persona, Markdown UI |

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
*   **Docker:** `docker compose up --build -d` successfully boots PostgreSQL, FastAPI, and Next.js. Alembic migrations run automatically.

## 3. Architecture & Hardening
*   **Auth:** Argon2id password hashing, HS256 JWT tokens stored in HttpOnly cookies.
*   **CSRF Defense:** Strict Origin validation for cookie-authenticated unsafe methods.
*   **In-Process TEA:** Refactored the chat agent to call the TEA engine in-process, removing the internal HTTP hop and securing the `/tea` endpoint.
*   **Rate Limiting:** `slowapi` enforces per-IP limits (Login: 5/min, Chat: 20/min).
*   **UI Rebrand:** Transitioned to the "VALORIS | ODRM Copilot" brand identity with an emerald/teal color palette.

## 4. Deviations & Fixes (Post-Deployment)
*   **Tailwind CSS Fix:** Migrated from the experimental `@tailwindcss/turbopack` to the official `@tailwindcss/postcss` plugin. This fixed the production Docker build where CSS was failing to compile.
*   **Markdown Rendering:** Installed `react-markdown`, `remark-gfm`, and `rehype-katex` to ensure the AI's output renders beautifully instead of displaying raw asterisks and math symbols.
*   **Agent Persona:** Updated `prompts.py` to give the AI a conversational persona, allowing it to answer "meta" questions (like "What is your purpose?") without timing out or attempting to force a tool call.
*   **Docker Live Smoke Test:** The full stack was successfully booted locally. Users can log in, run screenings, download PDF reports, and use the AI Chat.

## 5. Known limitations (Addressed in Sprint 8)
*   **Single-Turn Chat Memory:** The `/api/v1/chat` endpoint is currently stateless. This is the primary deliverable for Sprint 8 (Multi-Turn Memory).
*   **JWT tokens** are stateless and cannot be revoked until Sprint 10 (Redis denylist).