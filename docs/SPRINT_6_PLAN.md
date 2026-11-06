# Sprint 6 Plan - ESG Export Engine

| | |
|---|---|
| Status | **Draft - awaiting CTO approval** |
| Date | 2026-11-06 |
| Scope | `POST /api/v1/report`, PDF ESG report, compliance timestamp + SHA-256 digest, Results Panel download button |
| Dependency | Sprint 5 complete and accepted |
| Approval phrase | `AUTHORIZED: Sprint 6 implementation phase` |

> **Planning gate:** this document is the only Sprint 6 artifact allowed before approval.
> No implementation code, tests, routes, schemas, dependency installs, React code, PDF
> rendering code, or commits are to be created until the CTO approves this plan with the
> exact phrase above.

---

## 1. Executive summary

Sprint 6 delivers the ESG export promised in the pitch deck and in the master roadmap:

1. A new backend endpoint `POST /api/v1/report` accepts the existing `TeaRequest` contract.
2. The endpoint recomputes the screening server-side with the existing surrogate models and
   TEA engine; it does not trust client-supplied results.
3. A professional PDF is generated in memory, with no filesystem writes, and returned as a
   downloadable attachment.
4. The PDF contains plant conditions, AI predictions and model versions, financial/TEA
   results, assumptions, warnings, a UTC generation timestamp, a report ID, and a SHA-256
   digest of the canonical audit payload.
5. The Results Panel gains a "Download ESG Report" button that downloads exactly the
   screening result the user is looking at.

The report is a **screening-level ESG summary**, not a bankable audit, a verified carbon
credit, or a cryptographic proof of custody. Sprint 9 is where the blocked Merkle-tree
evidence chain lives. Sprint 6 prints an integrity digest and a timestamp, and states the
limitations explicitly in the document.

Existing `/predict`, `/tea`, `/market-prices`, and `/chat` contracts remain unchanged.

---

## 2. Sprint scope

### 2.1 In scope

- `POST /api/v1/report` accepting `TeaRequest` and returning `application/pdf`.
- Server-side recomputation of predictions and TEA through a shared screening helper so the
  report can never disagree with `/tea`.
- PDF generation with `reportlab` (Platypus layout) into `io.BytesIO`; no temporary files.
- Report sections:
  - cover/header with product name, report title, report ID, generation timestamp (UTC);
  - executive summary KPIs;
  - plant/reactor conditions table;
  - AI predictions and model-version provenance;
  - financial/TEA results and the assumptions used;
  - warnings rendered as human-readable messages, with codes retained for auditability;
  - methodology, limitations, and disclaimer;
  - integrity block with the SHA-256 digest and the canonical audit payload appendix.
- Response headers: `Content-Type`, `Content-Disposition`, `X-Report-Id`,
  `X-Report-SHA256`, `X-Report-Generated-At`.
- CORS `expose_headers` so the browser can read the report headers.
- Frontend `downloadReport()` API client and a `ReportDownload` component on the Results
  Panel with loading, error, filename, and accessible states.
- Backend unit/API tests and frontend client/component tests, written test-first.
- Dependency additions after approval: `reportlab` at runtime, `pypdf` as a test-only
  dependency.

### 2.2 Out of scope

- Merkle tree, hash chaining, blockchain anchoring, or on-chain notarization.
- Persisted report records, object storage, download history, or report retrieval by ID.
- Authentication, authorization, tenants, quotas, rate limiting, or billing.
- Idempotency-Key handling (noted as an open question and a Sprint 7 hardening item).
- Digital signatures, certificates, X.509, or PDF/A certification.
- Charts, embedded images, company logos, or user-supplied branding.
- Email delivery, scheduled reports, or batch exports.
- Changes to the surrogate models, TEA math, warning codes, or existing endpoint contracts.
- Frontend PDF preview; the browser downloads the file.
- Deployment, CI-provider changes, and production observability.

---

## 3. Roadmap reconciliation

- `docs/strategy/MASTER_ROADMAP.md` Sprint 6 requires `POST /api/v1/report`, a professional
  PDF containing plant conditions, AI predictions, financial ROI, and a compliance
  timestamp, plus the Results Panel button. This plan implements exactly those three
  deliverables with the existing `TeaRequest` contract.
- `docs/ARCHITECTURE.md` lists `/reports/tea` for Sprint 6. That is documentation drift.
  The binding contract for this sprint is `/api/v1/report`, consistent with the sprint brief
  and the existing `/api/v1` prefix. `ARCHITECTURE.md` should be reconciled in the Sprint 6
  report, not silently implemented.
- `docs/ARCHITECTURE.md` also mentions Idempotency-Key for reports and an audit export for
  admins. Both are deferred; Sprint 6 has no persistence layer to attach them to.
- Sprint 9's cryptographic ESG/carbon accounting is explicitly not part of this sprint. The
  Sprint 6 digest must not be described as immutable or as a carbon-credit proof.

---

## 4. Current baseline

- Backend: FastAPI app factory in `backend/src/odrm/main.py`; routers for `/predict`,
  `/tea`, `/market-prices` in `backend/src/odrm/api/routes.py`, and `/chat` in
  `backend/src/odrm/api/chat.py`. All are mounted under `/api/v1`.
- `TeaRequest` = `conditions: PredictRequest` + `assumptions: TeaAssumptions`.
- `TeaResponse` = `predictions`, `model_versions`, `financials`, `warnings`.
- `/tea` orchestration currently lives inline in `routes.py`: predict, build `TeaInputs`,
  call `calculate_tea`, map errors to HTTP 422/500/503, and round financials through
  `_tea_financials`.
- Test suite: 352 backend tests passing; ruff and mypy strict clean.
- Frontend: Next.js 16.4.3, React 19, TanStack Query, Tailwind 4, Vitest 5. The dashboard
  holds the latest `TeaRequest` as `teaMutation.variables`; the Results Panel receives only
  `data`, `isLoading`, and `isError`.
- Frontend tests: 21 passing; `postTea` sends JSON through `apiFetch`, which always parses
  JSON and therefore cannot be reused unchanged for a PDF response.
- Dependencies: no PDF library installed; root `pyproject.toml` is the source of truth.
  `requirements.txt` appears to be a pip-freeze snapshot and is UTF-16 encoded.

---

## 5. Architecture

### 5.1 Request flow

```text
Results Panel "Download ESG Report"
        |
        | POST /api/v1/report  (TeaRequest JSON)
        v
FastAPI report router
        |
        +--> run_screening(request, app.state.models)   # same path as /tea
        |        |
        |        +--> predict_surrogates(...)
        |        +--> calculate_tea(...)
        |        +--> TeaResponse
        |
        +--> build_report_data(request, response, report_id, generated_at)
        |        |
        |        +--> ReportData (all display values + warnings + canonical payload)
        |        +--> SHA-256 over canonical JSON
        |
        +--> render_pdf(report_data) --> bytes in io.BytesIO
        |
        v
Response(content=pdf_bytes, media_type="application/pdf", headers=...)
```

### 5.2 Design decisions

- **Recompute, do not accept results.** The endpoint takes `TeaRequest` and runs the same
  prediction/TEA path as `/tea`. This prevents a client from obtaining a report whose
  numbers differ from the platform's calculations.
- **One screening implementation.** Extract the current `/tea` body into
  `odrm/api/screening.py::run_screening(request, models) -> TeaResponse`, preserving the
  existing exceptions and rounding. `/tea` and `/report` both call it. Existing `/tea`
  regression tests guard the refactor.
- **Separate content from rendering.** `build_report_data` is pure and deterministic given
  its inputs (request, response, report ID, timestamp). `render_pdf` only lays out a
  `ReportData`. This makes the hash logic testable without parsing PDFs, and keeps PDF
  rendering replaceable.
- **No filesystem.** `io.BytesIO` is the only output buffer; the response body is
  `bytes`. Nothing is written under `data/`, `model_dir`, or a temp directory.
- **Server-generated filename.** `odrm-esg-report-<uuid>.pdf`; no user-controlled filename
  reaches the `Content-Disposition` header.
- **Sync endpoint.** Report generation is CPU-bound; a normal `def` route lets FastAPI run
  it in the threadpool, matching the existing sync route style.

### 5.3 Hash and timestamp semantics

The canonical audit payload is a JSON object:

```json
{
  "schema_version": "esg-report/v1",
  "report_id": "<uuid4>",
  "generated_at": "<UTC ISO 8601, second precision, Z suffix>",
  "request": { "conditions": { "...": "..." }, "assumptions": { "...": "..." } },
  "response": {
    "predictions": { "...": "..." },
    "model_versions": { "...": "..." },
    "financials": { "...": "..." },
    "warnings": ["..."]
  }
}
```

- Serialization: `json.dumps(payload, sort_keys=True, separators=(",", ":"),
  ensure_ascii=True)`.
- Digest: `hashlib.sha256(canonical.encode("utf-8")).hexdigest()`.
- The digest and the canonical payload are printed in the PDF so a reader can recompute the
  digest. The same digest is returned in `X-Report-SHA256`.
- Timestamp is generated with `datetime.now(timezone.utc)`, truncated to seconds, and
  formatted with a `Z` suffix. Tests inject a fixed value; the route uses the wall clock.
- The PDF must state: "SHA-256 integrity digest of the canonical audit payload. This is a
  tamper-evident checksum of the underlying data, not a digital signature, blockchain
  anchor, or proof of carbon-credit ownership."

---

## 6. Report content specification

Page size: A4 portrait. Margins: 18 mm. Header/footer on every page with product name,
"ESG Screening Report", report ID, and page number. Built-in Helvetica/Courier fonts; no
external font assets.

1. **Title block**
   - "Valoris ODRM-Copilot"
   - "ESG Screening Report"
   - "Flare-gas valorization pre-feasibility screening"

2. **Report metadata table**
   - Report ID (UUID4)
   - Generated at (UTC, ISO 8601)
   - Report schema version (`esg-report/v1`)
   - Currency (`USD`)
   - SHA-256 digest (full 64 hex characters, wrapped in Courier)

3. **Executive summary (KPI table)**
   - CH4 conversion (%)
   - Syngas yield (mol/mol CH4)
   - Annual net cash flow (USD/year)
   - ROI (%)
   - Payback period (years, or "Not available")

4. **Plant and reactor conditions**
   - Temperature (deg C), pressure (bar), CH4/O2 ratio, CO2/CH4 ratio, H2O/CH4 ratio,
     GHSV (1/h), catalyst, catalyst loading (wt%, or "Not provided"), N2 dilution
     (mol%, or "Not provided").

5. **AI predictions and provenance**
   - Predicted values with display precision matching the dashboard.
   - Model version for each target (`ch4_conversion`,
     `syngas_yield_mol_per_mol_ch4`).
   - Statement that predictions come from the pinned surrogate models and are not
     LLM-generated.

6. **Financial screening**
   - Daily: syngas production (kmol/day and Nm3/day), syngas revenue, CO2 consumed
     (tonnes/day), carbon-credit value, total revenue, feed cost, OPEX, net cash flow.
   - Annual: annual net cash flow; ROI; payback years.
   - All values formatted with units and USD; `payback_years = null` renders as
     "Not available".

7. **Assumptions used**
   - CH4 feed rate, natural-gas price, syngas price, carbon-credit price, CO2 utilization
     fraction, CAPEX, OPEX percentage, operating hours/day, operating days/year.

8. **Warnings**
   - Human-readable message plus the machine code in parentheses.
   - If none: "No warnings were generated for this screening."
   - Canonical backend mapping:
     - `carbon_credit_not_included`
     - `negative_annual_cash_flow`
     - `syngas_yield_out_of_envelope`
     - `zero_syngas_price`
     - `zero_carbon_price`
   - Unknown codes fall back to the raw code so future warnings are never dropped.

9. **Methodology and limitations**
   - Surrogate models trained on synthetic ODRM data; screening-level estimates.
   - Not a bankable feasibility study, audited financial statement, or verified carbon
     credit.
   - Values depend on the supplied assumptions and market prices at the time of input.
   - No warranty; engineering review required before capital commitment.

10. **Integrity appendix**
    - Canonical audit payload as pretty-printed JSON in Courier (escaped for PDF text
      safety, wrapped, and paginated).
    - Instructions: recompute SHA-256 over the UTF-8 canonical form with sorted keys and
      compact separators; compare to the printed digest.

---

## 7. API design

### 7.1 Endpoint

`POST /api/v1/report`

Request body: existing `TeaRequest` (unchanged schema, `extra="forbid"`).

Success: `200 OK`

- `Content-Type: application/pdf`
- `Content-Disposition: attachment; filename="odrm-esg-report-<uuid>.pdf"`
- `X-Report-Id: <uuid>`
- `X-Report-SHA256: <64 lowercase hex characters>`
- `X-Report-Generated-At: <UTC ISO 8601 with Z>`
- Body: PDF bytes.

Implementation shape:

```python
@router.post("/report")
def report(request: TeaRequest, req: Request) -> Response:
    ...
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={...},
    )
```

No `response_model`; OpenAPI should document the PDF response and headers via
`responses={200: {"content": {"application/pdf": {}}}}` if it does not complicate typing.

### 7.2 Errors

Mirror `/tea` exactly:

| Condition | Status | Detail |
|---|---|---|
| Pydantic validation failure (missing, extra, out-of-bounds) | 422 | FastAPI validation envelope |
| `TeaInputError` (domain input rejection) | 422 | Exception message |
| `ModelUnavailableError` (models missing) | 503 | Exception message |
| `PredictionError` | 500 | "Model prediction failed." |
| `TeaCalculationError` | 500 | "TEA calculation failed." |
| PDF rendering/hash failure | 500 | "Report generation failed." |

Rendering exceptions are logged with the report ID and stack trace; the response never
contains internals and never includes the request payload.

### 7.3 CORS

`main.py` must add `expose_headers` for `Content-Disposition`, `X-Report-Id`,
`X-Report-SHA256`, and `X-Report-Generated-At`. Without this, browser JavaScript cannot read
the filename or digest cross-origin.

### 7.4 Router wiring

Add `app.include_router(report_router, prefix="/api/v1", tags=["report"])` in
`create_app`, after the existing routers.

---

## 8. PDF library selection

### 8.1 Options considered

| Library | License | Fit | Drawbacks |
|---|---|---|---|
| **reportlab** (recommended) | BSD-3-Clause | Mature, Platypus flowables and tables, pure-Python wheels, no system libraries on Windows, built-in core fonts | Larger dependency; PDFs contain generation metadata unless controlled |
| fpdf2 | LGPL-3.0 | Small, simple API, pure Python | Weaker table/flow layout; LGPL obligations for a proprietary product |
| WeasyPrint | BSD-3-Clause | HTML/CSS output is attractive | Requires GTK/Pango/Cairo system libraries on Windows; fragile CI |
| xhtml2pdf | Apache-2.0 | HTML input | Extra layer on reportlab; less control over pagination |
| pypdf | BSD-3-Clause | Reading/manipulating PDFs | Cannot generate a report |

### 8.2 Decision

Use **reportlab** for runtime generation and **pypdf** as a test-only dependency to assert
page count and extract text. Rationale:

- permissive BSD-3 license compatible with the proprietary project license;
- no native system packages on the target Windows environment;
- first-class tables, page templates, headers/footers, and automatic pagination for a
  regulatory-looking document;
- `io.BytesIO` output is natively supported by `SimpleDocTemplate`;
- pypdf lets tests verify rendered content instead of relying on PDF byte equality.

Planned dependency changes (after approval):

- `pyproject.toml` `[project].dependencies`: `"reportlab>=4.2,<5"`.
- `pyproject.toml` `[project.optional-dependencies].dev`: `"pypdf>=5,<7"`.
- Install with `.venv\Scripts\python.exe -m pip install -e ".[dev]"`.
- Do not edit `requirements.txt` until its role is confirmed (open question).

### 8.3 Rendering constraints

- Create a fresh `SimpleDocTemplate` and story per request; do not mutate reportlab global
  configuration at runtime.
- Escape every dynamic string with `xml.sax.saxutils.escape` before passing it to a
  `Paragraph`. `PredictRequest.catalyst` is currently a free string and could contain
  markup characters.
- Truncate displayed free-text fields (catalyst) to a safe length (for example 80
  characters) in the report builder; do not change the API schema.
- Use `pageCompression` default; tests must not assume byte-for-byte identical PDFs. The
  deterministic artifact is the canonical payload and its digest, not the PDF bytes.
- If a dynamic string contains characters unsupported by the core fonts, replace them with
  an ASCII-safe fallback. Font embedding is deferred (open question).

---

## 9. Configuration

No new settings are required for the initial implementation.

- API prefix stays `/api/v1` from `Settings.api_prefix`; the router is mounted with the
  existing literal prefix, consistent with current code.
- Report branding strings ("ODRM-Copilot", "ESG Screening Report") are constants in the
  reporting module, not environment configuration.
- No output directory, retention period, or storage configuration is added because no files
  are persisted.
- If the CTO requests configurable branding later, add `ODRM_REPORT_*` settings in a
  follow-up; not part of this sprint.

---

## 10. Frontend design

### 10.1 API client

Add to `frontend/src/lib/api.ts`:

```ts
export interface ReportDownload {
  blob: Blob;
  filename: string;
  reportId: string | null;
  sha256: string | null;
  generatedAt: string | null;
}

export async function downloadReport(request: TeaRequest): Promise<ReportDownload>
```

- POST to `${API_BASE_URL}/report` with JSON, `cache: "no-store"`.
- On `!response.ok`, parse JSON/text detail and throw `ApiError` (same semantics as
  `apiFetch`).
- Return `response.blob()` plus parsed `Content-Disposition` filename (fallback
  `odrm-esg-report.pdf`) and the `X-Report-*` headers.
- Do not reuse `apiFetch`; it always parses JSON.

Add `ReportDownload` to `types.ts` if the team prefers all shared interfaces there; either
location is acceptable, but pick one and keep imports consistent.

### 10.2 Component

New `frontend/src/components/dashboard/report-download.tsx`:

- Props: `{ request: TeaRequest }`.
- Renders a secondary button: "Download ESG Report".
- `type="button"` so it never submits the surrounding dashboard form.
- Uses TanStack Query `useMutation` (existing project pattern) or local async state; the
  mutation/state owns `isPending` and `error`.
- On success:
  - `URL.createObjectURL(blob)`;
  - create an anchor with `href`, `download=filename`, append/click/remove;
  - `URL.revokeObjectURL` in `finally`.
- On error: inline `role="alert"` message "Report generation failed. Please try again."
- Pending copy: "Generating PDF..." with the button disabled and `aria-busy="true"`.
- Success status announced via `aria-live="polite"` ("Report downloaded.").

### 10.3 Results Panel and Dashboard

- `ResultsPanel` gains an optional `request?: TeaRequest` prop and renders
  `<ReportDownload request={request} />` after the provenance block when both `data` and
  `request` exist.
- `Dashboard` passes `request={teaMutation.variables}`. TanStack Query retains the
  variables of the latest mutation, so the report uses the exact payload that produced the
  visible result, not unsaved form edits.
- If `teaMutation.variables` is undefined (for example a restored cached result), the
  button is hidden rather than sending an incomplete payload.

### 10.4 Styling and accessibility

- Match existing Tailwind button styles; secondary/outline treatment to distinguish from
  "Run Screening".
- Visible focus ring, disabled styling, no color-only status.
- Dark-mode classes consistent with the panel.

---

## 11. Proposed file layout

```text
backend/src/odrm/
  api/
    screening.py          # NEW: shared run_screening(request, models) -> TeaResponse
    report.py             # NEW: POST /report router, error mapping, headers
    routes.py             # EDIT: /tea delegates to screening.run_screening
  reporting/
    __init__.py           # NEW
    content.py            # NEW: ReportData, build_report_data, warning messages, hash
    pdf.py                # NEW: render_pdf(ReportData) -> bytes (reportlab)
  main.py                 # EDIT: include report router, expose CORS headers

backend/tests/unit/
  reporting/
    test_content.py       # NEW: sections, warnings, canonical payload, digest
    test_pdf.py           # NEW: PDF signature, page count, extracted text
  test_report_api.py      # NEW: success, headers, errors, model-unavailable
  test_tea_api.py         # unchanged; regression gate for the shared helper

frontend/src/
  lib/
    api.ts                # EDIT: downloadReport
    api.test.ts           # EDIT: blob/filename/error tests
    types.ts              # EDIT (optional): ReportDownload interface
  components/dashboard/
    report-download.tsx        # NEW: download button + state
    report-download.test.tsx   # NEW
    results-panel.tsx          # EDIT: optional request prop + render button
    results-panel.test.tsx     # EDIT: button visibility/props
    dashboard.tsx              # EDIT: pass teaMutation.variables

pyproject.toml            # EDIT: reportlab runtime, pypdf dev-only
docs/SPRINT_6_REPORT.md   # NEW at the end of implementation (Phase 5)
```

No other files are modified.

---

## 12. Test strategy (TDD)

Every unit is written red-to-green before the next layer. Backend tests use the existing
`TestClient` + `StubModel` pattern and the network-blocking conftest; no test touches the
network or disk for report output.

### 12.1 Backend content builder (`test_content.py`)

- Builds a `ReportData` from a fixed `TeaRequest`/`TeaResponse` and fixed report ID and
  timestamp.
- Contains every plant condition, including `null` optional fields rendered as
  "Not provided".
- Contains every prediction, model version, financial field, assumption, and warning.
- Warning mapping covers all five known codes; unknown codes fall back to the raw code.
- Canonical JSON is stable regardless of dictionary insertion order.
- Digest equals an independently computed `hashlib.sha256` of the expected canonical JSON.
- Changing any field (request, response, report ID, timestamp) changes the digest.
- Catalyst text is escaped/truncated and cannot inject reportlab paragraph markup.

### 12.2 Backend PDF renderer (`test_pdf.py`)

- Returns non-empty `bytes` starting with `%PDF-` and ending with `%%EOF`.
- `pypdf` reports at least two pages for a representative report.
- Extracted text contains: "ODRM-Copilot", "ESG Screening Report", report ID, the UTC
  timestamp, the digest, the CH4 conversion value, annual net cash flow, and the
  human-readable warning message.
- A warnings-free response renders "No warnings were generated".
- A negative-cash-flow response renders "Not available" for payback and the warning.
- Rendering does not create files (test asserts no new files under `tmp_path`; rendering
  only receives a `ReportData`, and the test runs with a temp CWD).

### 12.3 Backend API (`test_report_api.py`)

- Success: stubbed models, valid payload -> 200, `application/pdf`, PDF magic bytes,
  attachment filename ending in `.pdf`, `X-Report-Id` UUID, `X-Report-SHA256` 64 hex,
  `X-Report-Generated-At` parseable UTC.
- Report numbers match a `/tea` call made with the same stubbed models (parity test).
- Invalid conditions -> 422; invalid assumptions -> 422; extra top-level field -> 422.
- Missing models -> 503; partial models -> 503.
- Non-finite prediction -> 500 with no PDF body.
- `render_pdf` monkeypatched to raise -> 500 with generic detail.
- Header digest matches the digest recomputed from the returned PDF's appendix or from the
  shared builder given the returned report ID/timestamp (choose the builder-based check to
  avoid brittle PDF text parsing).
- No request payload appears in the error response or logs.

### 12.4 Frontend API client (`api.test.ts`)

- `downloadReport` posts to `/report` with the payload and `POST`.
- Parses `Content-Disposition` filename and `X-Report-*` headers.
- Falls back to `odrm-esg-report.pdf` when the header is missing or malformed.
- Non-OK response throws `ApiError` with parsed detail.

### 12.5 Frontend component (`report-download.test.tsx`, `results-panel.test.tsx`)

- Button renders with the correct label and `type="button"`.
- Click calls `downloadReport` with the exact `TeaRequest`.
- Success creates and revokes an object URL and triggers an anchor download with the
  server filename (stub `URL.createObjectURL`, `URL.revokeObjectURL`, and anchor `click`).
- Pending state disables the button and shows "Generating PDF...".
- Failure shows an accessible alert and does not throw.
- Results Panel renders the button only when both `data` and `request` are present.
- Dashboard passes the mutation variables (covered by an existing or new dashboard test if
  cheap; otherwise the prop contract is covered at the Results Panel level).

### 12.6 Gates

- Backend: `pytest backend/tests -q` (all existing 352 tests plus new tests).
- Backend lint/type: `ruff check backend/src backend/tests`; `mypy backend/src/odrm scripts`.
- Frontend: `npm test`, `npm run typecheck`, `npm run lint`.
- No skipped tests, no network, no filesystem artifacts, no dependency drift beyond the
  approved additions.

---

## 13. Error handling and UX

- Backend errors mirror `/tea`, so the frontend can reuse its existing error vocabulary.
- PDF rendering failures are indistinguishable to the client from other server failures
  (generic 500) to avoid leaking internals; the report ID is logged for support.
- The download button is only shown for a successful screening with a known request.
- During generation the button is disabled; the user cannot trigger parallel downloads from
  the same button.
- If the browser ignores the `download` filename (cross-origin), the fallback name is a
  valid `.pdf` filename.
- Object URLs are always revoked, including on error paths.
- The Results Panel's existing loading/error/empty states are unchanged.

---

## 14. Security, privacy, and observability

- **Markup injection:** all dynamic text is escaped before entering reportlab flowables;
  free-text fields are truncated. No HTML is accepted or rendered.
- **Header injection:** filenames are server-generated UUIDs; user input never reaches
  response headers.
- **Data handling:** the report contains commercially sensitive process/financial inputs.
  Do not log request bodies. Log only report ID, duration, byte size, warning codes, and
  outcome.
- **No persistence:** bytes exist in memory for the request lifetime only.
- **No auth/rate limiting:** unchanged from the current baseline; report generation is
  CPU-bound and becomes a hardening item in Sprint 7. Note this in the Sprint 6 report.
- **Digest limitations:** clearly documented; no claim of immutability, signature, or
  carbon-credit verification.
- **Concurrency:** reportlab objects are created per request and no global configuration is
  mutated. A future load test belongs to Sprint 7.
- **CORS:** only the required response headers are exposed; origins are unchanged.

---

## 15. Implementation outline

1. **Approval gate.** Wait for `AUTHORIZED: Sprint 6 implementation phase`.
2. **Dependencies.** Add reportlab and pypdf; install; confirm imports on Python 3.11
   Windows.
3. **Shared screening helper.** Extract `/tea` orchestration into
   `odrm/api/screening.py`; run the full backend suite to prove `/tea` is unchanged.
4. **Content builder (TDD).** Define `ReportData`, warning mapping, canonical payload, and
   SHA-256; implement until content tests pass.
5. **PDF renderer (TDD).** Implement the reportlab Platypus layout, escaping, headers and
   footers, integrity appendix; implement until PDF tests pass.
6. **Report API (TDD).** Add router, headers, CORS exposure, and error mapping; implement
   until API tests pass.
7. **Frontend client (TDD).** Add `downloadReport`; implement until client tests pass.
8. **Frontend UI (TDD).** Add `ReportDownload`, wire `ResultsPanel` and `Dashboard`;
   implement until component tests pass.
9. **Quality gates.** Run backend pytest/ruff/mypy and frontend test/typecheck/lint.
10. **Report and commit.** Write `docs/SPRINT_6_REPORT.md`, update README/API notes if
    needed, and commit per the sprint workflow only after the gates are green.

Each step is committed separately with tests, per the existing sprint workflow.

---

## 16. Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| reportlab output contains timestamps/IDs, so byte-for-byte PDF tests are flaky | High | Low | Test structure, page count, extracted text, and digest; never assert PDF equality |
| Dynamic text breaks reportlab paragraph parsing | Medium | Medium | Escape all strings; truncate free text; test catalyst with `<`, `&`, `>` |
| Core fonts cannot render non-ASCII catalyst names | Medium | Low | ASCII-safe fallback for Sprint 6; document font embedding as a follow-up |
| Report numbers diverge from `/tea` after refactor | Low | High | Shared `run_screening`; parity test with identical stubbed models |
| CORS blocks reading filename/digest headers | Medium | Medium | Add `expose_headers`; test in browser or assert middleware config |
| CPU-bound generation harms API latency under concurrency | Medium | Medium | Sync route + threadpool; bounded inputs; note load test for Sprint 7 |
| Users mistake the digest/disclaimer for a certified audit | Medium | High | Explicit limitation language on the cover and integrity appendix |
| PDF size grows with long free-text fields | Low | Medium | Truncate displayed free text; warnings are a bounded set |
| `requirements.txt` drifts from `pyproject.toml` | Medium | Low | Confirm source of truth before editing; do not regenerate blindly |
| Completion of `/tea` refactor changes rounding or error codes | Low | High | Preserve `_tea_financials` and exception mapping exactly; full regression suite |

---

## 17. Assumptions

- The endpoint accepts `TeaRequest` and recomputes predictions/TEA server-side.
- The report is English-only, A4, USD, and screening-level.
- No logo or binary brand asset is added; branding is text-only.
- Report ID is a UUID4 generated per request; the timestamp is UTC at generation time.
- The canonical audit payload is request + response + report ID + timestamp + schema
  version.
- The frontend report uses the latest successfully submitted `TeaRequest`, not live form
  state.
- Existing warning codes and messages remain the source of truth; the backend duplicates
  the display mapping rather than importing frontend code.
- `reportlab` and `pypdf` licenses are acceptable to the project.
- The root `pyproject.toml` is authoritative for dependencies; `requirements.txt` is only
  updated if the CTO confirms it is maintained.
- Existing unauthenticated API behavior is acceptable for this sprint.

---

## 18. Open questions for CTO review

1. **PDF library:** approve `reportlab` (BSD-3) with `pypdf` as a test-only dependency, or
   prefer `fpdf2` (LGPL-3) / another option?
2. **Input contract:** confirm `POST /api/v1/report` should take `TeaRequest` and recompute,
   rather than accepting a precomputed `TeaResponse` plus inputs.
3. **Digest scope:** is a SHA-256 over the canonical request + response + report ID +
   timestamp sufficient for Sprint 6, with the Sprint 9 Merkle chain deferred?
4. **Branding:** should the title be "ODRM-Copilot ESG Screening Report", and is a
   company/legal entity name required in the footer? No logo asset is planned.
5. **Page size:** A4 (recommended for the target market) or US Letter?
6. **Filename:** `odrm-esg-report-<uuid>.pdf`, or a timestamp-based name?
7. **Warnings:** include both human-readable text and raw codes (recommended), or text only?
8. **Idempotency:** defer `Idempotency-Key` support to Sprint 7 (recommended), or require it
   now?
9. **Failure cases:** always generate a report for negative cash flow/zero prices with
   warnings (recommended), or refuse to issue a report for some warning combinations?
10. **Dependencies file:** is `requirements.txt` maintained alongside `pyproject.toml`, and
    should it be regenerated after adding the PDF dependencies?
11. **Non-ASCII text:** accept ASCII-safe fallback for Sprint 6 (recommended), or bundle a
    Unicode font asset now?
12. **Frontend payload:** confirm the report should use the last successfully screened
    payload even if the form has since been edited (recommended).

---

## 19. Acceptance criteria

- `POST /api/v1/report` accepts a valid `TeaRequest` and returns a valid PDF attachment.
- The PDF contains plant conditions, AI predictions + model versions, financial/TEA
  results + assumptions, warnings, report ID, UTC timestamp, SHA-256 digest, methodology,
  and disclaimer.
- The response carries `Content-Disposition`, `X-Report-Id`, `X-Report-SHA256`, and
  `X-Report-Generated-At`, and the browser can read them.
- Error responses match `/tea` for validation, missing models, prediction, and TEA errors;
  rendering failures return a generic 500.
- `/tea` behavior is unchanged, proven by the existing regression suite and a parity test.
- The Results Panel shows a working, accessible "Download ESG Report" button for successful
  screenings, with pending and error states.
- Backend pytest, ruff, and mypy pass; frontend tests, typecheck, and lint pass.
- No filesystem report artifacts and no new network calls in tests.
- `docs/SPRINT_6_REPORT.md` is produced at the end of implementation.

---

## 20. Approval

This plan is submitted for CTO review. No Sprint 6 implementation work will begin until the
CTO replies with exactly:

`AUTHORIZED: Sprint 6 implementation phase`

Requested decisions are listed in section 18; the recommended defaults are marked there.
