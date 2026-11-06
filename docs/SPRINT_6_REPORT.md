# Sprint 6 — ESG Export Engine: Review Note

| | |
|---|---|
| Status | **Complete** |
| Date | 2026-11-06 |
| Scope | `POST /api/v1/report`, PDF ESG report, compliance timestamp + SHA-256 digest, Results Panel download button |

## 1. Objectives vs. outcome
| Plan Step | Outcome |
|---|---|
| 1. Shared screening pipeline | Done — `ead110e` |
| 2. Canonical report data builder | Done — `64ffeea` |
| 3. PDF renderer (reportlab) | Done — `dd3052b` |
| 4. Report API endpoint | Done — `653b627` |
| 5. Frontend download client | Done — `2c40d80` |
| 6. Frontend UI button | Done — `0200a9a` |

## 2. Automated Gate Evidence
*   **Backend:** `pytest` → 378 passed. `ruff` & `mypy` clean.
*   **Frontend:** `npm run test` → 30 passed. `lint` and `typecheck` clean.
*   **Dependencies:** `reportlab` (runtime) and `pypdf` (test-only) added to `pyproject.toml`.

## 3. Architecture & Verification
*   The report is generated server-side using the shared `run_screening` pipeline, guaranteeing the PDF numbers match the `/tea` API exactly.
*   The PDF includes a tamper-evident SHA-256 digest of the canonical JSON payload (request + response + report ID + timestamp).
*   All dynamic text is escaped before rendering to prevent markup injection.
*   CORS headers (`X-Report-Id`, `X-Report-SHA256`, `X-Report-Generated-At`) are exposed so the frontend can read the metadata.
*   No filesystem writes occur during generation; the PDF is buffered in memory.

## 4. Known limitations (By Design)
*   **Screening-level only:** The PDF explicitly states it is not a bankable audit, verified carbon credit, or blockchain proof.
*   **No Idempotency-Key:** Deferred to Sprint 7 (Hardening).
*   **ASCII-only core fonts:** Non-ASCII characters in free-text fields fall back to ASCII to prevent rendering crashes.