# Sprint 8 — Multi-Turn Memory & Agent Context: Review Note

| | |
|---|---|
| Status | **Complete** |
| Date | 2026-11-10 |
| Scope | `messages[]` chat contract, history-aware agent invocation, context-window management, frontend history submission |

## 1. Objectives vs. outcome
| Plan Step | Outcome |
|---|---|
| 1. Backend Schema Update (`messages[]`) | Done |
| 2. Backend Agent Update (history-aware) | Done |
| 3. Token Management (trimming) | Done |
| 4. Frontend State Update | Done |
| 5. TDD Strategy | Done |

## 2. Automated Gate Evidence
*   **Backend:** `pytest` → 503 passed. `ruff` & `mypy` clean.
*   **Frontend:** `npm run test` → 33 passed. `lint`, `typecheck`, and `build` clean.
*   **Context Coverage:** `context.py` → 100% statement and branch coverage.

## 3. Architecture & Hardening
*   **Stateless Memory:** The frontend sends the full conversation history on every turn. No database, no sessions, no server-side state.
*   **Request Validation:** The backend enforces limits (20 messages / 30,000 chars max submitted; 10 messages / 16,000 chars max sent to the model).
*   **Pure Trimming Logic:** The `trim_history` and `normalize_history` functions are pure, deterministic, and 100% unit-tested.
*   **Role Enforcement:** Only `user` and `assistant` roles are accepted. The server-owned `system` prompt cannot be overridden by the client.
*   **Graceful Timeouts:** The `DeadlineExceeded` error from Google is caught and mapped to a polite 503.

## 4. Deviations & Fixes
*   **Live Verification:** Multi-turn memory was manually verified in the Dockerized UI. The AI correctly remembers previous turns and answers follow-ups based on prior context.
*   **Google Latency:** During the manual test, the free-tier Gemini API timed out once on a longer multi-turn request. This is a provider limitation, not a code defect. Retries succeed.
*   **Lint Cleanup:** Minor pre-existing lint issues (prompt punctuation, unused imports) were fixed during Step 6.

## 5. Known limitations
*   Conversation history is browser-tab-scoped and is lost on refresh (by design; server-side persistence is Phase 2).
*   The free-tier Gemini API has a timeout on longer multi-turn requests. Production deployment should use a paid tier or a self-hosted model to eliminate this.
*   No "New Chat" button in the UI. Users clear history by refreshing the page.
*   `docs/API_DOCUMENTATION.md` and `docs/USER_GUIDE.md` remain absent from the repo; `README.md` is the canonical chat documentation for Sprint 8.