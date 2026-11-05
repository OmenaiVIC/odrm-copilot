# Sprint 5 — Agentic Orchestrator: Review Note

| | |
|---|---|
| Status | **Complete** |
| Date | 2026-11-05 |
| Scope | LangChain Agent, Guardrails, TEA Tool, `/api/v1/chat` API, React Chat UI |

## 1. Objectives vs. outcome
| Plan Step | Outcome |
|---|---|
| 1. LLM Provider Factory & Settings | Done — `4b3f559` |
| 2. Request Guardrails | Done — `a447ce9` |
| 3. Typed TEA HTTP Client | Done — `d093fc3` |
| 4. Guarded TEA Tool | Done — `2b8e1b0` |
| 5. Agent Orchestrator | Done — `1409eb2` |
| 6. Chat API Endpoint | Done — `4b3d821` |
| 7. Chat Frontend UI | Done — `8459499` |
| 8. Documentation | Done — `39d6f57` |

## 2. Automated Gate Evidence
*   **Backend:** `pytest` → 352 passed. `ruff` & `mypy` clean.
*   **Frontend:** `npm run test` → 21 passed. `lint`, `typecheck`, and `build` clean.

## 3. Architecture & Guardrails
*   The LLM acts purely as an intent parser. It cannot compute physics or financials.
*   **Guardrails:** The agent strictly enforces `schema.BOUNDS`. If a user asks for 1500°C, the tool rejects it *before* hitting the `/tea` API, returning a 422 error to the UI.
*   **Single-Tool Design:** The agent is restricted to `calculate_project_economics` to prevent hallucinated endpoints.
*   **Authority:** The final response strictly embeds the `TeaResponse` returned by the backend API.

## 4. Known limitations & Configuration
*   The system requires an LLM provider to be configured in the `.env` file (Ollama, OpenAI, or Gemini).
*   If no provider is configured, the endpoint safely returns `503 Agent Unavailable`.
*   Manual smoke testing of the live LLM was deferred to environment setup.