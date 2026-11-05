# Sprint 5 Plan - Agentic Orchestrator

| | |
|---|---|
| Status | **Draft - awaiting CTO approval** |
| Date | 2026-11-05 |
| Scope | LangChain agent, pluggable local/API LLM, TEA tool, guardrails, `/api/v1/chat`, chat UI |
| Dependency | Sprint 4 complete and accepted |
| Approval phrase | `AUTHORIZED: Sprint 5 implementation phase` |

> **Planning gate:** this document is the only Sprint 5 artifact allowed before approval.
> No implementation code, tests, routes, schemas, dependency installs, React code, or commits
> are to be created until the CTO approves this plan with the exact phrase above.

---

## 1. Executive summary

Sprint 5 adds a narrow, tool-using agent to ODRM Copilot:

1. A user sends a natural-language process and financial description to `POST /api/v1/chat`.
2. A LangChain agent extracts a strict `TeaRequest` and calls exactly one tool,
   `calculate_project_economics`.
3. The tool applies deterministic physics/financial guardrails before any TEA call.
4. Valid requests are sent to the existing `POST /api/v1/tea` endpoint through an injectable
   TEA client.
5. The API returns a conversational reply plus the authoritative `TeaResponse` object.
6. A new chat component displays the reply and reuses the existing result-rendering path.

The LLM is an interface for extracting and explaining a request, not a numerical authority.
Every process and financial number shown as a result comes from `/api/v1/tea`. The agent cannot
compute predictions, financials, H2/CO ratio, carbon risk, or confidence scores itself.

The endpoint is `POST /api/v1/chat` as required by the Sprint 5 brief. The existing
`docs/ARCHITECTURE.md` reference to `/agent/chat` is documentation drift and must not be
implemented. The existing `/predict`, `/tea`, and `/market-prices` contracts remain unchanged.

---

## 2. Sprint scope

### 2.1 In scope

- A LangChain agent using `langchain.agents.create_agent`.
- A single tool: `calculate_project_economics`.
- Strict extraction of natural language into the existing `TeaRequest` contract.
- Deterministic guardrails for reactor conditions, catalyst, optional fields, and financial
  assumptions before the TEA call.
- An injectable TEA client that calls the existing `/api/v1/tea` endpoint in production.
- Pluggable model selection for:
  - OpenAI API;
  - local Ollama through its OpenAI-compatible API;
  - Gemini API through its OpenAI-compatible API, subject to the verification described below.
- `POST /api/v1/chat` with a typed request, typed success response, needs-input state, and
  structured guardrail/downstream errors.
- A `frontend/src/components/chat/chat-interface.tsx` component integrated into the existing
  home page.
- Backend unit, tool, agent, API, and HTTP-client tests using fake models and fake TEA clients.
- Frontend API-client and component tests using mocked `fetch`.
- README, `.env.example`, and operator notes for provider configuration.
- TDD throughout: each unit is written red-to-green before the next layer is added.

### 2.2 Out of scope

- Training or changing surrogate models.
- H2/CO ratio, carbon-risk classification, confidence scores, or prediction intervals. These
  are not returned by the current models or API and must not be fabricated.
- The full architecture tool catalogue (`validate_conditions`, `predict_syngas`,
  `simulate_sweep`, `estimate_tea`, `compare_runs`, `retrieve_docs`, `export_report`).
- Multi-turn conversation memory, checkpoints, user sessions, or persistence.
- Streaming responses, server-sent events, websockets, or background jobs.
- RAG, document retrieval, or external knowledge sources.
- Authentication, authorization, user accounts, rate limiting, or billing.
- Live market data lookup inside the agent. Market prices remain a separate service.
- Automatic model downloads, Ollama installation, or Gemini/OpenAI account setup.
- Deployment, containerisation, CI-provider changes, and production observability.
- File export, reports, charts, or evidence-chain functionality.
- Changing the existing `/predict`, `/tea`, or `/market-prices` contracts.
- Installing or upgrading Python or JavaScript packages during the planning phase.

---

## 3. Roadmap reconciliation

The roadmap, architecture document, and Sprint 5 brief do not use identical names. This plan
follows the brief and records the conflicts instead of silently choosing one.

| Source | Statement | Sprint 5 treatment |
|---|---|---|
| Sprint 5 brief | `POST /api/v1/chat` | Implemented exactly. |
| `docs/ARCHITECTURE.md` | `/agent/chat` | Not implemented; documentation drift to reconcile after approval. |
| Sprint 5 brief | Tool name `calculate_project_economics` | Implemented exactly. |
| `docs/strategy/MASTER_ROADMAP.md` | Tool name `predict_and_calculate_tea` | Not implemented; alias is not added. |
| Roadmap | Local Ollama or API Gemini/OpenAI | Provider factory supports OpenAI, Ollama, and Gemini configurations. |
| Roadmap | H2/CO ratio, carbon risk, confidence | Deferred; not present in current target or response contracts. |
| Roadmap | Full agent tool catalogue | Reduced to the single required TEA tool. |
| Market Data Service | Prices supplied by a separate service | Chat requires explicit assumptions; it does not fetch prices automatically. |
| Architecture | Evidence chain and immutable audit | Out of scope; no claim of cryptographic auditability. |
| Architecture | Four-layer orchestration/tools/guardrails/observability | Preserved in a reduced form for the one tool. |

### 3.1 Why the reduced scope is not stubbed

- A fake H2/CO ratio, carbon-risk class, or confidence percentage would be misleading in a
  screening tool.
- The current TEA response already carries model versions and warnings; those are the only
  provenance fields Sprint 5 may display.
- Adding the other architecture tools would require new domain contracts and scope approval.
- A single-turn, stateless endpoint is sufficient for the requested chat workflow and avoids
  inventing session semantics.

---

## 4. Current baseline

### 4.1 Verified Sprint 4 state

- HEAD: `a743a74 docs: add Sprint 4 report and frontend quickstart`.
- Backend: 277 tests passing.
- Frontend: 14 tests passing.
- Ruff, Ruff format, mypy, ESLint, TypeScript, and Next.js build pass.
- Existing routes:
  - `POST /api/v1/predict` -> `{predictions, model_version}`.
  - `POST /api/v1/tea` -> `{predictions, model_versions, financials, warnings}`.
  - `GET /api/v1/market-prices` -> cached mock quote.
- `Settings` uses the `ODRM_` environment prefix and currently has no LLM settings.
- `backend/src/odrm/agents/__init__.py` and `backend/tests/agent/__init__.py` are empty
  placeholders.
- No Sprint 5 implementation code exists.

### 4.2 Agent dependencies already present

- `pyproject.toml` already declares `langchain>=0.3`, `langchain-core>=0.3`,
  `langchain-openai>=0.2`, and `httpx>=0.27`.
- Installed environment: `langchain 1.4.7`, `langchain-core 1.7.3`,
  `langchain-openai 1.7.3`, `langgraph`, `openai`, and `httpx`.
- `langchain_ollama` and `langchain_google_genai` are not installed.
- LangChain 1.x APIs available in the environment:
  - `langchain.agents.create_agent`;
  - `langchain.chat_models.init_chat_model`;
  - `langchain_core.tools.tool`.
- The declared lower bounds `>=0.3` do not match the installed 1.x API surface. Dependency
  pinning is an implementation decision, not a planning-phase edit.

### 4.3 Test infrastructure already present

- `backend/tests/conftest.py` imports `FakeListChatModel`.
- `ToolSpy` records tool names and arguments.
- The autouse network guard blocks all outbound sockets except `127.0.0.1`, `::1`, and
  `localhost`.
- The `agent` pytest marker is registered.
- `frontend/src/lib/api.test.ts` already tests the API client.
- Frontend component tests use Vitest, React Testing Library, and mocked `global.fetch`.

### 4.4 Existing constraints to preserve

- `TeaRequest` already forbids extra fields and uses Pydantic bounds.
- `TeaAssumptions` already provides default values for optional fields.
- The current models predict only `ch4_conversion` and
  `syngas_yield_mol_per_mol_ch4`.
- `docs/ARCHITECTURE.md` calls for tool results to carry units, model version, and confidence;
  the current TEA contract has units in field names and `model_versions`, but no confidence.
  Sprint 5 must not invent confidence.
- `frontend/AGENTS.md` requires reading the bundled Next.js 16 documentation before frontend
  implementation.

---

## 5. Architecture

### 5.1 Request flow

```text
Browser
  |
  | POST /api/v1/chat {"message": "..."}
  v
FastAPI chat route
  |
  v
AgentService (backend/src/odrm/agents/orchestrator.py)
  |
  |-- provider factory -> ChatOpenAI-compatible model
  |-- create_agent(system_prompt, tools=[calculate_project_economics])
  |
  v
calculate_project_economics tool
  |
  |-- guardrails.validate_tea_request()
  |       |
  |       |-- invalid -> GuardrailViolation, no TEA call
  |       v
  |-- TeaClient.calculate(TeaRequest)
  |       |
  |       v
  |   POST /api/v1/tea
  |       |
  |       v
  |   TeaResponse
  |
  v
AgentRunRecorder
  |
  |-- authoritative typed result / guardrail error
  v
Chat route -> ChatResponse
  |
  v
ChatInterface
```

### 5.2 Layer responsibilities

| Layer | Responsibility | Must not do |
|---|---|---|
| API route | Validate message, invoke service, map outcomes to HTTP, generate `request_id` | Calculate physics, call a model directly, or call TEA directly |
| Agent service | Build the model, run the agent, enforce one-tool behaviour, collect outcomes | Accept model prose as numerical truth |
| Tool | Map validated arguments to `TeaRequest`, call the TEA client | Perform its own predictions or financial arithmetic |
| Guardrails | Validate bounds, catalyst, finite values, missing/extra arguments | Trust the prompt or model to enforce limits |
| TEA client | Call `/tea`, parse `TeaResponse`, map transport errors | Add business assumptions or mutate the request |
| Recorder | Store the request-scoped tool call, result, and error | Use global mutable state or retain data between requests |
| UI | Collect message, display reply and structured result, display errors | Recompute financials or invent missing outputs |

### 5.3 Authority rule

The endpoint succeeds with a result only when the TEA tool was called and returned a validated
`TeaResponse`. The model's `reply` is presentation text; the `result` field is the sole
authoritative source of predictions and financial values. If the model answers without calling
the tool, no `result` is returned.

### 5.4 Single-turn behavior

The endpoint is stateless and single-turn. The browser may keep a local display history, but it
does not send previous messages, and the backend does not persist them. Each request must contain
enough information, or the agent asks for the missing fields. Multi-turn memory is deferred.

### 5.5 Provider abstraction

`providers.py` exposes a small factory:

```text
build_chat_model(settings) -> BaseChatModel
```

Provider behavior:

| Provider | Implementation | Default base URL | Requirement |
|---|---|---|---|
| `openai` | `ChatOpenAI` | OpenAI default | `ODRM_LLM_API_KEY` and `ODRM_LLM_MODEL` |
| `ollama` | `ChatOpenAI` against Ollama's OpenAI-compatible `/v1` API | `http://localhost:11434/v1` | `ODRM_LLM_MODEL`; dummy key is allowed |
| `gemini` | `ChatOpenAI` against Gemini's OpenAI-compatible endpoint | `https://generativelanguage.googleapis.com/v1beta/openai/` | `ODRM_LLM_API_KEY` and `ODRM_LLM_MODEL` |

The provider is selected server-side. The API key is never sent to the frontend and never
logged. `ODRM_LLM_BASE_URL` overrides the base URL for self-hosted or proxy deployments.

Gemini's OpenAI-compatible endpoint must pass one manual tool-calling smoke test during
implementation. If it does not, adding `langchain-google-genai` is a dependency change requiring
separate CTO approval. The planning phase does not install it.

### 5.6 TEA client abstraction

`tea_client.py` defines:

```text
TeaClient(Protocol):
    calculate(request: TeaRequest) -> TeaResponse

HttpTeaClient:
    POST {ODRM_TEA_API_BASE_URL}/tea
    Content-Type: application/json
    body: TeaRequest
    timeout: ODRM_TEA_TIMEOUT_SECONDS
```

- The base URL is configuration only and is never supplied by the user.
- The response is validated with `TeaResponse.model_validate`.
- HTTP 422 from `/tea` maps to an internal `TeaRejectedError`.
- HTTP 5xx, connection failures, and timeouts map to `TeaUnavailableError`.
- No retries are added initially, because the TEA call is read-only but retries increase
  latency and duplicate work.
- Tests inject a fake client. The production client is tested with `httpx.MockTransport`, so no
  real socket is used.

The self-HTTP boundary is deliberate: it preserves the existing `/tea` contract as the single
TEA entry point. An in-process service call remains an alternative for a later decision; see
Open Questions.

### 5.7 Agent execution

- `AgentService` builds a request-scoped `AgentRunRecorder` and tool closure.
- The agent is created with `tools=[calculate_project_economics]`.
- The system prompt defines the role, units, tool-only rule, required fields, and refusal to
  invent results.
- The invocation uses a small recursion limit so a model cannot loop indefinitely.
- Only one successful TEA tool call is accepted per chat request. A second call is rejected.
- If the tool succeeds but the model's final message is empty or fails, the service returns the
  structured result with a deterministic fallback reply rather than discarding a completed
  calculation.
- No checkpointer, store, session, or conversation history is configured.

---

## 6. Tool design

### 6.1 Tool contract

| Property | Value |
|---|---|
| Name | `calculate_project_economics` |
| Purpose | Validate ODRM conditions and assumptions, then call the existing TEA endpoint |
| Arguments | `conditions` and `assumptions`, matching `TeaRequest` |
| Side effects | One read-only HTTP call to `/api/v1/tea` in production |
| Returns | JSON-serializable `TeaResponse` |
| Computes numbers itself | No |
| Calls other tools | No |

The tool description must say that it is the only permitted way to obtain process predictions
or financial results and that the model must not calculate those values itself.

### 6.2 Tool arguments

The tool uses `TeaRequest` as its argument schema:

```text
conditions:
  temperature_c: float
  pressure_bar: float
  ch4_o2_ratio: float
  co2_ch4_ratio: float
  h2o_ch4_ratio: float
  ghsv_per_h: float
  catalyst: string
  catalyst_loading_wt_pct: float | null
  n2_dilution_mol_pct: float | null
assumptions:
  ch4_feed_kmol_per_h: float
  natural_gas_price_usd_per_mmbtu: float
  syngas_price_usd_per_kmol: float
  carbon_credit_price_usd_per_tonne_co2e: float
  co2_utilization_fraction: float
  capex_usd: float
  opex_pct_of_capex_per_year: float
  operating_hours_per_day: float
  operating_days_per_year: float
```

All fields are units-as-specified; the schema uses Celsius, bar, per-hour GHSV, mol ratios, USD,
and the existing field names. The model must not rename or unit-convert fields into a different
schema. Ambiguous units must trigger a clarification rather than an assumed conversion.

### 6.3 Guardrail table

Physics and condition guardrails come from `backend/src/odrm/data/schema.py`; no duplicate
bound constants are introduced.

| Field | Rule | Source |
|---|---|---|
| `temperature_c` | 500 to 1000 inclusive | `schema.BOUNDS` |
| `pressure_bar` | 1 to 30 inclusive | `schema.BOUNDS` |
| `ch4_o2_ratio` | 1.4 to 2.5 inclusive | `schema.BOUNDS` |
| `co2_ch4_ratio` | 0 to 1.5 inclusive | `schema.BOUNDS` |
| `h2o_ch4_ratio` | 0 to 1.5 inclusive | `schema.BOUNDS` |
| `ghsv_per_h` | 1000 to 100000 inclusive | `schema.BOUNDS` |
| `catalyst_loading_wt_pct` | 0 to 20 inclusive when present | `schema.BOUNDS` |
| `n2_dilution_mol_pct` | 0 to 50 inclusive when present | `schema.BOUNDS` |
| `catalyst` | One of `Ni/Al2O3`, `Ni-MgO`, `Rh`, `Pt`, `none`, `other` | `schema.ENUMS` |
| All numeric fields | Finite; reject `NaN`, `+Inf`, `-Inf` | Explicit guardrail check |
| `assumptions` | Existing `TeaAssumptions` bounds and defaults | `api/schemas.py` |

The existing `Settings.max_temperature_c` is not used as a second temperature limit. Using two
different temperature sources would create drift; the schema bounds remain authoritative.

### 6.4 Guardrail sequence

1. Require an object with exactly `conditions` and `assumptions`; reject extra keys.
2. Validate against `TeaRequest`/`PredictRequest`/`TeaAssumptions`.
3. Check every supplied numeric value is finite.
4. Check the catalyst against `CATALYST_CATEGORIES`.
5. Check the physical fields against `schema.BOUNDS` so errors carry field, value, minimum, and
   maximum rather than relying on free-form Pydantic messages.
6. Only after all checks pass, call `TeaClient.calculate`.

A failure at any step records a `GuardrailViolation` and returns without calling the TEA client.
The route maps it to HTTP 422 with a structured `detail` object.

### 6.5 Missing and optional arguments

- The six condition fields other than the two optional fields are required.
- Required financial assumptions are feed rate, natural-gas price, syngas price, carbon-credit
  price, and capex.
- `co2_utilization_fraction`, `opex_pct_of_capex_per_year`, `operating_hours_per_day`, and
  `operating_days_per_year` may use the existing `TeaAssumptions` defaults.
- The agent should ask for required values it cannot extract. It must not invent feed rate,
  prices, capex, conditions, or catalyst.
- If the model calls the tool with missing required fields anyway, the guardrail returns
  `INVALID_ARGUMENTS` with the missing field paths; no TEA call occurs.
- Default assumptions are not silently presented as user-provided facts. The UI labels the
  result as a screening result.

### 6.6 Request-scoped recorder

`AgentRunRecorder` records:

```text
tool_invoked: bool
tool_arguments: TeaRequest | None
result: TeaResponse | None
guardrail_error: GuardrailViolation | None
tea_error: TeaUnavailableError | TeaRejectedError | None
tool_call_count: int
```

The tool closes over one recorder and one TEA client. No module-level mutable state is allowed.
The service reads the recorder after the agent finishes and decides the outcome independently of
the model's prose.

Outcome mapping:

| Recorder state | Service outcome | HTTP result |
|---|---|---|
| Valid tool result | `ok` with result | 200 |
| No tool call, agent asks for information | `needs_input` | 200 |
| Guardrail violation | `rejected` | 422 structured error |
| TEA unavailable/timeout | `unavailable` | 503 structured error |
| No usable model output and no tool call | `needs_input` with safe fallback text | 200 |
| Unexpected agent/runtime failure | `error` | 500 structured error |

---

## 7. API design

### 7.1 Endpoint

```text
POST /api/v1/chat
Content-Type: application/json
```

The route lives in `backend/src/odrm/api/chat.py` and is included by `create_app` with the
existing `/api/v1` prefix. Existing routers and paths remain unchanged.

### 7.2 Request schema

```json
{
  "message": "At 750 C, 5 bar, CH4:O2 2.0, CO2:CH4 0.5, H2O:CH4 0.3, GHSV 20000/h, Ni/Al2O3, 10 wt%, 0% N2, with 100 kmol/h CH4 feed, $3.25/MMBtu gas, $4.10/kmol syngas, $28.50/tCO2e credits, and $5,000,000 capex. What is the conversion, yield, and payback?"
}
```

Rules:

- `message` is required, trimmed, non-empty, and at most 2000 characters.
- Extra request fields are rejected.
- No conversation history, user id, model, provider, API key, or base URL is accepted from the
  client.
- The backend owns provider selection and all network endpoints.

### 7.3 Success response

`ChatResponse` embeds the existing `TeaResponse` model rather than duplicating it:

```json
{
  "status": "ok",
  "reply": "The screening completed. CH4 conversion is 86.2%, syngas yield is 2.31 mol/mol CH4, annual net cash flow is $1.24M, ROI is 24.8%, and payback is 4.03 years.",
  "result": {
    "predictions": {
      "ch4_conversion": 0.862,
      "syngas_yield_mol_per_mol_ch4": 2.31
    },
    "model_versions": {
      "ch4_conversion": "xgb-...",
      "syngas_yield_mol_per_mol_ch4": "xgb-..."
    },
    "financials": {
      "syngas_kmol_per_day": 0,
      "syngas_nm3_per_day": 0,
      "syngas_revenue_usd_per_day": 0,
      "co2_consumed_tonnes_per_day": 0,
      "carbon_credit_value_usd_per_day": 0,
      "total_revenue_usd_per_day": 0,
      "feed_cost_usd_per_day": 0,
      "opex_usd_per_day": 0,
      "net_cash_flow_usd_per_day": 0,
      "annual_net_cash_flow_usd": 0,
      "roi_pct": 0,
      "payback_years": null,
      "currency": "USD"
    },
    "warnings": []
  },
  "request_id": "0f8c6c1e-..."
}
```

The example financial numbers are placeholders; the invariants are the shape and authority of
`result`, not the values.

`status` values for HTTP 200:

| Status | Meaning | `result` |
|---|---|---|
| `ok` | Tool succeeded | Required, validated `TeaResponse` |
| `needs_input` | Agent needs missing information or did not call the tool | `null` |

A response with `status: "ok"` and `result: null` is invalid and must fail response-model
validation.

### 7.4 Error responses

Errors use the existing FastAPI `detail` envelope with a structured object for chat-specific
failures:

```json
{
  "detail": {
    "code": "BOUNDS_VIOLATION",
    "message": "temperature_c must be between 500 and 1000 C.",
    "field": "conditions.temperature_c",
    "value": 1500.0,
    "minimum": 500.0,
    "maximum": 1000.0,
    "request_id": "0f8c6c1e-..."
  }
}
```

Codes:

| HTTP | Code | Cause |
|---|---|---|
| 422 | `BOUNDS_VIOLATION` | Condition or assumption outside allowed range |
| 422 | `UNKNOWN_CATALYST` | Catalyst not in the supported categories |
| 422 | `MISSING_ARGUMENTS` | Required condition or assumption absent |
| 422 | `INVALID_ARGUMENTS` | Extra fields, wrong shape, non-finite value, or invalid type |
| 422 | `TEA_REJECTED` | `/tea` returned a domain 422 after passing guardrails |
| 503 | `AGENT_UNAVAILABLE` | Provider not configured, credentials missing, provider/network failure |
| 503 | `TEA_UNAVAILABLE` | `/tea` connection failure, timeout, or server error |
| 500 | `AGENT_ERROR` | Unexpected internal agent failure |

The request's Pydantic-level validation may use FastAPI's standard 422 detail shape. The UI must
handle both the standard shape and the structured chat error shape without crashing.

Error responses must not expose API keys, provider request IDs, stack traces, or internal
filesystem paths. Logs may contain the `request_id` and exception type.

### 7.5 Compatibility

- `/api/v1/predict`, `/api/v1/tea`, and `/api/v1/market-prices` retain their current methods,
  paths, schemas, status codes, and OpenAPI tags.
- The chat route is additive.
- No global exception-envelope migration is performed in Sprint 5.
- The response embeds the existing `TeaResponse`, so `/tea` remains the single TEA result
  contract.

---

## 8. Configuration

### 8.1 New settings

Add to `backend/src/odrm/core/config.py` using the existing `ODRM_` prefix and `Field`
validation:

| Setting | Type | Default | Purpose |
|---|---|---|---|
| `llm_provider` | `Literal["openai", "ollama", "gemini"]` | `"openai"` | Provider selection |
| `llm_model` | `str | None` | `None` | Model name; required for chat |
| `llm_api_key` | `SecretStr | None` | `None` | Server-side provider key |
| `llm_base_url` | `str | None` | `None` | Optional provider/proxy override |
| `llm_temperature` | `float` | `0.0` | Deterministic extraction |
| `llm_timeout_seconds` | `float` | `30.0` | Provider request timeout |
| `chat_max_message_chars` | `int` | `2000` | Message length cap |
| `tea_api_base_url` | `str` | `http://127.0.0.1:8000/api/v1` | Internal TEA base URL |
| `tea_timeout_seconds` | `float` | `30.0` | TEA HTTP timeout |

Validation rules:

- `llm_temperature` is between 0 and 1.
- Timeouts are greater than zero.
- `chat_max_message_chars` is between 1 and 8000.
- `llm_provider` is one of the three allowed values.
- An absent `llm_model` does not prevent application startup; chat returns `AGENT_UNAVAILABLE`.
- An absent key for `openai` or `gemini` does not prevent startup; chat returns
  `AGENT_UNAVAILABLE`.
- `ollama` may use a dummy key when `llm_api_key` is absent.
- The API key is never serialized into logs, errors, API responses, or frontend config.

### 8.2 Environment examples

Document these in `.env.example` and the README without real secrets:

```text
# OpenAI
ODRM_LLM_PROVIDER=openai
ODRM_LLM_MODEL=<openai-model>
ODRM_LLM_API_KEY=<server-side-key>

# Local Ollama (OpenAI-compatible endpoint)
ODRM_LLM_PROVIDER=ollama
ODRM_LLM_MODEL=<installed-ollama-model>
ODRM_LLM_BASE_URL=http://localhost:11434/v1

# Gemini (OpenAI-compatible endpoint)
ODRM_LLM_PROVIDER=gemini
ODRM_LLM_MODEL=<gemini-model>
ODRM_LLM_API_KEY=<server-side-key>

# Internal TEA endpoint
ODRM_TEA_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

The actual provider/model values are operator choices and are not hard-coded into tests.

### 8.3 Lazy initialization

`create_app` must continue to start when no LLM is configured. The agent service is constructed
lazily or with a model factory that raises a typed configuration error only when `/chat` is
called. Existing routes and health checks must not fail because the agent is unconfigured.

### 8.4 Dependency policy

- LangChain and `httpx` are already installed; no package installation occurs in the planning
  phase.
- The current lower bounds `>=0.3` do not match the 1.x API surface. Implementation may tighten
  them to tested 1.x ranges; that is a dependency-file change requiring CTO approval.
- `langchain_ollama` and `langchain_google_genai` are optional provider fallbacks, not planning
  dependencies.
- No automatic network access is allowed in tests.

---

## 9. Frontend design

### 9.1 Component

Add `frontend/src/components/chat/chat-interface.tsx` as a client component.

Responsibilities:

- Render a labelled multiline message composer.
- Keep local display history for user and assistant messages.
- Submit via `postChat(message)` from `frontend/src/lib/api.ts`.
- Display:
  - loading state while the request is pending;
  - assistant reply;
  - structured result using the existing `ResultsPanel` where practical;
  - needs-input state with no result;
  - guardrail errors with the field and limit;
  - provider/TEA unavailable states with retry guidance;
  - generic network/server errors.
- Disable duplicate submissions while pending.
- Enforce a 2000-character client-side limit as a UX aid, with the backend still authoritative.
- Clearly label the output as a screening result, not investment advice.
- Not calculate or reformat financial truth independently. Formatting for display is allowed;
  all source values come from `result`.

### 9.2 Integration

Add `<ChatInterface />` to `frontend/src/app/page.tsx` below the existing `<Dashboard />` inside
the existing page shell. Do not replace or restructure the accepted Sprint 4 dashboard. The chat
is an additive section.

The component may use the existing `ResultsPanel` for the result panel. If the panel is too large
inside a message, wrap it in a collapsible section while preserving the same authoritative data
path. Do not create a second calculation or copy of the financial formulas.

### 9.3 API client

Add to `frontend/src/lib/api.ts`:

```text
postChat(message: string): Promise<ChatResponse>
```

It posts `{ message }` to `/chat` through the existing `apiFetch` helper. `ApiError` continues to
carry status and detail. Extend `frontend/src/lib/types.ts` with:

```text
ChatRequest
ChatResponse
ChatStatus
ChatErrorDetail
```

`ChatResponse.result` reuses the existing `TeaResponse` type.

### 9.4 UI behavior

| State | User-visible behavior |
|---|---|
| Empty | Composer and brief screening disclaimer |
| Submitting | Disabled submit, loading indicator, `aria-busy` |
| Ok | Assistant reply plus structured result panel |
| Needs input | Assistant asks for the missing values; no result panel |
| 422 guardrail | Field-specific error; no result; input remains editable |
| 503 agent/TEA | Retryable error message; no fabricated result |
| Other error | Generic safe message with request id when available |

Accessibility requirements:

- The textarea has a visible label.
- Submit is keyboard-accessible; Enter submits and Shift+Enter inserts a newline, or the
  implementation uses an explicit button without hidden keyboard behavior.
- Replies use `aria-live="polite"`.
- Error state is announced and not conveyed by color alone.
- Focus remains predictable after submission.

No streaming, markdown rendering of untrusted remote content, or HTML injection is added.

### 9.5 Frontend tests

Add `frontend/src/components/chat/chat-interface.test.tsx` and extend
`frontend/src/lib/api.test.ts`:

- `postChat` sends POST `{message}` to `/chat` and returns parsed data.
- Successful response renders reply and `ResultsPanel` data.
- `needs_input` renders the clarification and no result panel.
- 422 structured detail renders the field/limit and preserves the composer.
- 503 renders a retryable error.
- Empty/whitespace and over-limit messages do not submit.
- Pending state prevents duplicate submission.
- No authoritative numbers are recomputed client-side.

Follow the existing mocked-`global.fetch` and TanStack Query wrapper patterns. Do not add a new
network-mocking package.

---

## 10. Proposed file layout

### 10.1 Backend

```text
backend/src/odrm/
  agents/
    __init__.py                  existing placeholder; export public agent types
    orchestrator.py              AgentService, AgentRunRecorder, outcome mapping
    tools.py                     calculate_project_economics tool factory
    guardrails.py                validation, GuardrailViolation, error mapping
    providers.py                 build_chat_model provider factory
    prompts.py                   system prompt for extraction/tool use
    tea_client.py                TeaClient protocol, HttpTeaClient, typed errors
  api/
    chat.py                      POST /api/v1/chat router
    schemas.py                   ChatRequest, ChatResponse, chat error schemas
  core/
    config.py                    LLM and chat settings
  main.py                        create_app wiring; lazy agent service
```

### 10.2 Backend tests

```text
backend/tests/agent/
  __init__.py                    existing
  fakes.py                       fake TeaClient, scripted tool-calling model helpers
  test_guardrails.py             bounds, catalyst, finite values, missing/extra fields
  test_tools.py                  tool schema, exact TeaRequest, recorder, no-call on rejection
  test_tea_client.py             MockTransport, path/body, response validation, error mapping
  test_providers.py              provider/base-URL selection, missing configuration, secret safety
  test_orchestrator.py           tool selection, one-call rule, no-tool path, fallback reply
  test_chat_api.py               route status codes, response models, request id, compatibility
backend/tests/conftest.py        update fake_llm to emit tool calls; keep ToolSpy and network guard
```

`FakeListChatModel` returns plain content and is insufficient for tool-call testing. Replace or
supplement the `fake_llm` fixture with a scripted `GenericFakeChatModel` or a small custom
`BaseChatModel` that emits an `AIMessage` with `tool_calls`, followed by a final `AIMessage`.
No existing test uses the current fixture, so this is a safe extension.

### 10.3 Frontend

```text
frontend/src/
  components/chat/
    chat-interface.tsx
    chat-interface.test.tsx
  lib/
    api.ts                       add postChat
    api.test.ts                  extend postChat tests
    types.ts                     add chat types
  app/
    page.tsx                     add <ChatInterface /> below the dashboard
```

### 10.4 Documentation

```text
.env.example                     add provider and TEA settings examples
README.md                        document chat endpoint, provider setup, limitations
```

`docs/ARCHITECTURE.md` route/tool naming is not edited during planning. Reconcile it after
approval if the CTO chooses to align the architecture document with the implemented names.

---

## 11. Test strategy

### 11.1 Guardrail tests

- Valid full `TeaRequest` passes and produces a typed object.
- `temperature_c = 1500` raises `BOUNDS_VIOLATION` with the correct field/value/limits.
- Each physical bound rejects values below and above its range.
- Optional `catalyst_loading_wt_pct` and `n2_dilution_mol_pct` accept `null` and valid values.
- Unknown catalyst raises `UNKNOWN_CATALYST`.
- `NaN`, positive infinity, and negative infinity raise `INVALID_ARGUMENTS`.
- Missing required conditions or assumptions report the missing field path.
- Extra fields are rejected by `TeaRequest`.
- Missing optional assumptions use the existing defaults.
- No TEA client call occurs after any violation.

### 11.2 Tool tests

- Tool name and description match the contract.
- A valid argument set produces exactly one `TeaRequest` passed to the fake client.
- The fake client receives the exact nested `conditions` and `assumptions` values.
- The returned `TeaResponse` is stored in the recorder.
- A second tool call is rejected and does not make a second TEA request.
- A guardrail failure returns a structured tool error and leaves `result` empty.
- A TEA failure records `TeaUnavailableError` or `TeaRejectedError`.

### 11.3 TEA client tests

- Uses `httpx.MockTransport`; no socket is opened.
- Sends `POST` to `/tea` with JSON body and `Content-Type: application/json`.
- Parses a valid `TeaResponse`.
- Maps 422 to `TeaRejectedError`.
- Maps 500, connect errors, and timeout to `TeaUnavailableError`.
- Rejects an invalid response body.
- Never retries automatically.

### 11.4 Agent tests

- Scripted model emits a `calculate_project_economics` tool call, then a final reply:
  - assert the tool was called once with the expected arguments;
  - assert the final result comes from the fake TEA client;
  - assert model prose cannot overwrite the result.
- Scripted model answers without a tool call:
  - assert no TEA client call;
  - assert `needs_input` and no result.
- Scripted model emits a malformed tool call:
  - assert a typed guardrail or agent error, no TEA call.
- Scripted model attempts two calls:
  - assert exactly one TEA call.
- Tool succeeds but final model generation fails:
  - assert the structured result is still returned with a fallback reply.
- Real provider classes are not invoked in the test suite.

### 11.5 Chat API tests

- Valid request returns 200 with `status: "ok"`, `reply`, `result`, and `request_id`.
- `needs_input` returns 200 with `result: null`.
- `1500 C` request returns 422 `BOUNDS_VIOLATION` and the TEA fake is not called.
- Unknown catalyst returns 422 `UNKNOWN_CATALYST`.
- Missing required fields return 422 `MISSING_ARGUMENTS`.
- Empty, whitespace-only, over-limit, and extra-field requests are rejected.
- Missing provider configuration returns 503 `AGENT_UNAVAILABLE`.
- TEA failure returns 503 `TEA_UNAVAILABLE`.
- Existing `/predict`, `/tea`, and `/market-prices` tests still pass.
- Error responses contain no API key or stack trace.
- Full `status: "ok"` response validates as `ChatResponse`.

### 11.6 Frontend tests

- `postChat` request path, method, body, and response handling.
- Successful reply/result rendering.
- Needs-input rendering.
- Guardrail 422 rendering.
- Agent/TEA 503 rendering.
- Empty and over-limit input handling.
- Loading/duplicate-submit prevention.
- Existing dashboard tests remain green.

### 11.7 Network and determinism

- The existing autouse socket guard remains enabled.
- Tests use only fake models, fake TEA clients, and `httpx.MockTransport`.
- Default model temperature is 0.
- No test depends on a live Ollama daemon, OpenAI key, Gemini key, TEA server, or internet.

### 11.8 Manual smoke checklist

These checks are manual and are not part of the automated gate:

1. Start the backend with a loaded TEA model set and one provider configuration.
2. Send a full natural-language request and confirm a structured result.
3. Send `1500 C` and confirm a 422 with no `/tea` call.
4. Send an incomplete request and confirm a clarification response.
5. Send a valid request with the provider stopped and confirm 503.
6. Start the frontend and verify success, needs-input, 422, and 503 states.

### 11.9 Commands

```text
.venv\Scripts\python.exe -m pytest backend/tests -q
.venv\Scripts\ruff.exe check backend
.venv\Scripts\ruff.exe format --check backend
.venv\Scripts\mypy.exe backend/src scripts
cd frontend
npm run lint
npm run typecheck
npm run test
npm run build
```

---

## 12. Error handling and UX

- Guardrails run before the tool's TEA call; a rejected request never becomes a model-generated
  "best guess."
- The API distinguishes user-correctable errors (422) from service availability errors (503).
- The UI keeps the composer content after errors so the user can adjust it.
- The UI never displays a result panel unless `result` is present.
- The UI shows field-level bounds from structured errors when available.
- Provider downtime and TEA model downtime are separate messages.
- The endpoint returns a generated `request_id` for correlation; the server logs the same id.
- Unexpected exceptions are logged with the request id and mapped to a generic 500 message.
- A model failure after a successful tool call does not discard the tool result.
- A model response without a tool call is not treated as a successful screening.
- The chat is labelled as a screening aid and not a substitute for engineering review or
  investment advice.

---

## 13. Security, privacy, and observability

- API keys remain server-side and use `SecretStr`.
- Provider base URLs are settings, not user input; the user cannot induce arbitrary SSRF.
- The TEA base URL is settings-only.
- The user message has a length cap.
- The system prompt is not exposed through the API.
- Tool arguments and results are validated structurally; prompt instructions are not trusted as
  guardrails.
- No RAG means no untrusted retrieved document path in this sprint.
- Logs include request id, provider, model, duration, tool invocation status, and error code.
- Logs do not include API keys. User messages and full prompts are not logged by default because
  they may contain plant economics.
- The chat endpoint inherits existing CORS settings.
- Authentication, authorization, quotas, and rate limiting are deployment concerns and are
  explicitly out of scope for Sprint 5.

---

## 14. Implementation outline

Implementation begins only after the CTO sends `AUTHORIZED: Sprint 5 implementation phase`.

1. Re-run the Sprint 4 baseline gates.
2. Add settings and provider-factory tests; implement lazy provider construction and typed
   configuration errors.
3. Add guardrail tests; implement `validate_tea_request` using the existing Pydantic schemas,
   `BOUNDS`, `ENUMS`, and explicit finite-value checks.
4. Add TEA client tests; implement the protocol and `HttpTeaClient` with `httpx`.
5. Add tool tests; implement `calculate_project_economics` with a request-scoped recorder.
6. Add orchestrator tests with a scripted tool-calling fake model; implement `AgentService`,
   one-call enforcement, fallback replies, and outcome mapping.
7. Add API tests; implement `ChatRequest`/`ChatResponse`, the chat router, app wiring, and
   structured errors.
8. Add frontend types, API-client tests, component tests, and the chat UI; reuse
   `ResultsPanel` for result rendering.
9. Update `.env.example` and the README.
10. Run the full backend and frontend gates, perform the manual smoke checklist where
    credentials are available, and report results.
11. Do not commit during planning. During implementation, follow the repository's sprint
    workflow and commit only when the CTO requests it.

---

## 15. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| LLM extracts plausible but wrong in-range values | Misleading screening result | Show the structured request values where practical, show model versions/warnings, label as screening, and require human review |
| Prompt injection or model ignores the tool-only rule | Fabricated numbers | The endpoint exposes `result` only when the recorder has a valid TEA response; prompt is not the guardrail |
| Missing required assumptions | Failed or misleading request | Agent asks for them; tool rejects missing fields; no invented defaults for required values |
| Ollama is not installed/running | Chat 503 | Typed `AGENT_UNAVAILABLE`, health of existing endpoints unaffected, local setup documented |
| Gemini OpenAI-compatible endpoint does not support the required tool calling | Provider unusable | Manual smoke test; optional provider package requires approval |
| LangChain 1.x API versus `>=0.3` lower bounds | Import/API drift | Tested-version pin decision in Open Questions; no install during planning |
| TEA self-HTTP URL is misconfigured | Chat 503 | Settings validation, documented default, `httpx.MockTransport` tests, 503 mapping |
| TEA models absent | Chat 503 | Reuse existing `ModelUnavailableError` mapping through the TEA client |
| Model latency or provider timeout | Slow UI | Server timeouts, loading state, no streaming, clear 503 |
| Duplicate tool calls or retry loops | Duplicate calculations and delay | One successful call per request; recursion limit; no automatic TEA retries |
| User sends insufficient information | Extra turns | `needs_input` response; no session memory in Sprint 5 |
| Ambiguous units | Wrong in-range request | Prompt requires clarification for ambiguous units; tests cover explicit units |
| Chat endpoint exposed without auth | Abuse or data exposure | Out of scope; deployment must add auth/rate limiting; local Ollama option documented |
| Chat text contains sensitive plant data | Privacy risk | Do not log prompts by default; document third-party provider data flow |
| Route/tool names diverge from architecture docs | Maintainer confusion | Reconciliation table and post-approval documentation update |
| Existing model limits lack H2/CO/carbon/confidence | Scope creep | Explicitly deferred and never faked |
| Frontend assumes a newer Next.js API | Build/runtime regression | Read bundled `frontend/node_modules/next/dist/docs/` before implementation |
| Test fake cannot emit tool calls | False confidence | Replace `FakeListChatModel` with a scripted tool-call-capable fake and assert arguments |

---

## 16. Assumptions

- Sprint 5 is a single-turn, stateless chat feature.
- The user supplies or the agent extracts all required conditions and financial assumptions.
- The only numerical authority is the existing `/api/v1/tea` response.
- The agent exposes exactly one tool in this sprint.
- The TEA models are loaded when the user wants a successful screening result.
- OpenAI-compatible chat endpoints used for Ollama/Gemini support tool calling; Gemini must be
  smoke-tested before it is claimed as supported.
- No new ML outputs, carbon-risk model, H2/CO target, confidence score, or evidence chain exists.
- The existing dashboard and its tests remain the primary screening UI; chat is additive.
- API keys and provider configuration are supplied by the operator, not the browser.
- The backend remains synchronous for chat; FastAPI may execute sync handlers in its threadpool.
- No new dependencies are installed during planning.
- The repository's existing test-network guard remains active.

---

## 17. Open questions for CTO review

1. **Route naming:** should the implemented route remain `POST /api/v1/chat` from the brief, or
   should `docs/ARCHITECTURE.md` be changed first to use `/agent/chat`? Recommended: keep
   `/api/v1/chat` and fix the architecture document after approval.
2. **Tool naming:** should the tool remain `calculate_project_economics`, or be renamed to the
   roadmap's `predict_and_calculate_tea`? Recommended: keep the brief's name.
3. **Provider scope:** is OpenAI-compatible access sufficient for Ollama and Gemini, or must
   native provider packages be installed? Recommended: implement OpenAI-compatible access first,
   smoke-test Gemini, and add a native package only with explicit approval.
4. **Dependency pinning:** may implementation tighten the LangChain lower bounds to the tested
   1.x versions? Recommended: yes, because the current lower bounds do not provide the installed
   API surface.
5. **Default provider/model:** should the repository ship with a default provider/model, or
   require explicit configuration and return 503 until configured? Recommended: require explicit
   `ODRM_LLM_MODEL`; no secrets or provider assumptions in code.
6. **Missing fields:** should the agent ask for missing assumptions, or should Sprint 5 use
   dashboard defaults for feed rate, prices, and capex? Recommended: ask; only the existing
   optional `TeaAssumptions` fields may default.
7. **TEA transport:** is an internal HTTP call to `/tea` acceptable, or should the tool invoke the
   TEA service in-process? Recommended: HTTP behind the injectable client, preserving the
   existing endpoint contract.
8. **Session behavior:** is single-turn/no-memory acceptable for Sprint 5? Recommended: yes;
   multi-turn memory requires a separate state and privacy design.
9. **Response contract:** is `status`, `reply`, `result`, and `request_id` sufficient, or does the
   CTO want tool arguments or a full trace in the response? Recommended: expose only the
   authoritative result and status; keep tool arguments in logs/tests.
10. **Catalyst hardening:** should `/tea` itself reject unknown catalysts, or only the chat
    guardrail? Recommended: do not change `/tea` in Sprint 5; add the chat guardrail and record
    the base-contract gap separately.
11. **Market prices:** should chat auto-fill assumptions from `/market-prices`? Recommended: no
    in Sprint 5; the user supplies price assumptions explicitly.
12. **UI placement:** is placing `<ChatInterface />` below the dashboard acceptable, or should it
    be a separate route/tab? Recommended: additive section below the dashboard to preserve the
    accepted Sprint 4 layout.
13. **Authentication and rate limiting:** are these deferred to a deployment layer? Recommended:
    defer, but document that the endpoint must not be exposed publicly without them.
14. **Streaming:** is non-streaming acceptable? Recommended: yes for Sprint 5; streaming adds a
    different API and UI contract.
15. **Error envelope:** is a structured `detail` object for chat acceptable while existing routes
    keep their current detail styles? Recommended: yes; avoid a cross-cutting migration now.

---

## 18. Acceptance criteria

Sprint 5 is complete when all of the following are true:

1. `POST /api/v1/chat` exists with the request/response contract in section 7.
2. A valid request with a scripted tool-calling model returns 200, `status: "ok"`, a validated
   `TeaResponse`, and a `request_id`.
3. The `calculate_project_economics` tool is called exactly once with the exact nested
   `TeaRequest`; the fake TEA client records one call and the body matches.
4. A `1500 C` request returns 422 `BOUNDS_VIOLATION` and the TEA client is never called.
5. Unknown catalysts, non-finite values, extra fields, and missing required fields are rejected
   before TEA.
6. No model response without a successful tool call can produce a `result`.
7. A provider or TEA failure returns a structured 503, not a fabricated result.
8. `/predict`, `/tea`, and `/market-prices` contracts and tests remain unchanged.
9. The fake-model agent tests use `FakeListChatModel`-compatible or scripted tool-call fakes and
   never open a network socket.
10. The chat UI renders success, needs-input, 422, and 503 states; it does not recompute or invent
    financial values.
11. Backend tests, Ruff, Ruff format, mypy, frontend lint, typecheck, tests, and build pass.
12. `.env.example` documents all provider and TEA settings without real secrets.
13. No H2/CO, carbon-risk, confidence, streaming, multi-turn memory, or evidence-chain claims are
    added.
14. The implementation report lists the exact changed files and any CTO-approved dependency
    changes.
15. The planning phase leaves only this plan file as a change.

---

## 19. Approval

Planning is complete when the CTO has reviewed this document and the Open Questions above.

Implementation must not start until the CTO replies with exactly:

```text
AUTHORIZED: Sprint 5 implementation phase
```
