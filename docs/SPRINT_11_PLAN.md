\# Sprint 11 Plan — Public-Good Intelligence Layer



| | |

|---|---|

| Status | \*\*Approved - Phase 4 authorized\*\* |

| Date | 2026-11-24 |

| Scope | Merkle-tree ESG audit trail, SAC-first Stellar integration design, Excel regulatory reporting workbook, open benchmark publication, detection adapter dashboard wiring, and SCF Build Award application preparation |

| Dependency | Sprint 10 complete at `06d969b`; Stellar CLI installed (v30.0.1); Stellar MCPs connected |

| Approval phrase | `AUTHORIZED: Sprint 11 implementation phase` |



> \*\*Planning gate:\*\* This file is the Sprint 11 plan. No implementation code, test code, or file creation beyond this plan until the CTO approves with the exact phrase above.



> \*\*Architecture decisions (2026-11-24):\*\*

> - \*\*SAC-first:\*\* Carbon credits are issued as Stellar Assets (classic `G...` issuer assets) using the native Stellar Asset Contract (SAC) for compliance. The Soroban contract is a \*\*minimal Evidence Registry\*\* (`store\_root`, `verify\_hash` only). No custom token logic.

> - \*\*Excel instead of Power BI:\*\* Power BI Desktop is free but the Service tier requires \~$10/user/month for sharing with regulators. Excel delivers the same promise with zero licensing cost and zero friction.

> - \*\*Regulator-agnostic:\*\* All whitelist and detection claims remain hedged. NOGIET-style is one example among many.



\---



\## 1. Goal



Deliver the public-good intelligence layer of Valoris: cryptographic ESG evidence (Merkle-tree audit trail), a clear on-chain integration path (Stellar Assets + SAC + minimal Soroban registry), a regulatory reporting artifact (Excel workbook), the open benchmark publication (MIT-licensed dataset + validator + baseline model), and detection adapter dashboard wiring. Prepare and submit the Stellar Community Fund (SCF) Build Award application by year-end 2026.



Sprint 11 does not deploy to Mainnet, does not build a full RWA marketplace, and does not modify Sprint 10 deliverables.



\---



\## 2. Deliverables



\### D2 — Merkle-Tree ESG Audit Trail + Stellar Integration Design



1\. \*\*Merkle-tree hash chain for every screening.\*\* Every `/api/v1/tea` and `/api/v1/report` call produces a cryptographic hash chain: individual screening hash → batch root → daily root. Stored in a new `screening\_evidence` table.

2\. \*\*Verification endpoint.\*\* `GET /api/v1/evidence/verify/{hash}` returns the Merkle proof path and validates against the root.

3\. \*\*Stellar Integration Design Document.\*\* `docs/STELLAR\_INTEGRATION.md` describing:

&#x20;  - Contract interface: `store\_root(batch\_id, merkle\_root)` and `verify\_hash(batch\_id, leaf\_hash, proof) -> bool` — registry only, no token logic.

&#x20;  - Data model: `batch\_roots` map, no balances.

&#x20;  - \*\*SAC integration:\*\* Valoris acts as the asset issuer. Credits are issued via the Stellar Asset Contract's `mint`/`transfer` calls, gated by the registry's verification. Native Stellar compliance features (freeze, clawback, authorization flags) are used for regulatory control.

&#x20;  - Migration path: off-chain hash chain (D2) → testnet anchor (D5) → mainnet anchor (post-SCF).

&#x20;  - Audit readiness: what SCF Audit Bank will review (registry contract only, not the SAC).

4\. \*\*SCF Build Award Milestone Plan.\*\* `docs/SCF\_MILESTONE\_PLAN.md` — 3–4 month tranche structure for the SCF Build Award (Integration Track). Total ask within $150K XLM range.



\### D2a — Excel Regulatory Reporting Workbook



5\. \*\*MIT-licensed Excel template.\*\* `exports/regulatory\_workbook.xlsx` (published via release, not tracked in git). Four pages: Operator Screening, Portfolio Summary, Scenario Comparison, Evidence Trail.

6\. \*\*Data export script.\*\* `scripts/export\_evidence\_for\_excel.py` — exports `screening\_evidence` to CSV for Power Query.

7\. \*\*Workbook documentation.\*\* `docs/REGULATORY\_WORKBOOK.md`.



\### D3 — Open Benchmark Publication



8\. \*\*MIT-licensed release.\*\* Tagged GitHub release `v1.0-benchmark` containing: the 10,000-scenario dataset, schema validator, baseline XGBoost model, training script, and ODRM physics benchmark documentation.

9\. \*\*Reproduction guide.\*\* `docs/BENCHMARK\_REPRODUCTION.md`.



\### D4 — Detection Adapter Dashboard Wiring



10\. \*\*Dashboard detection panel.\*\* New component showing hotspots from the configured `DetectionSource`. Default is `MockNogietAdapter`.

11\. \*\*API client extension.\*\* `GET /api/v1/detection/hotspots` wired into the frontend with TanStack Query.



\### D5 — Soroban Evidence Registry Prototype



12\. \*\*Minimal Soroban contract.\*\* `contracts/valoris-evidence/` — Rust contract with two functions only: `store\_root`, `verify\_hash`. Deployed to Testnet. Ready for SCF Audit Bank review.



\---



\## 3. Acceptance Criteria



| ID | Criterion | Verified by |

|---|---|---|

| AC-1 | Every `/api/v1/tea` call produces a `screening\_evidence` row with valid SHA-256 hashes. | `test\_tea\_creates\_evidence\_row` |

| AC-2 | `GET /api/v1/evidence/verify/{hash}` returns a valid Merkle proof path and confirms inclusion in the current batch root. | `test\_evidence\_verification\_round\_trip` |

| AC-3 | `docs/STELLAR\_INTEGRATION.md` exists with all five sections (contract interface, data model, SAC integration, migration path, audit readiness). | File exists; CTO review |

| AC-4 | `docs/SCF\_MILESTONE\_PLAN.md` exists with 3–4 month tranche structure and SCF Build Award total ask. | File exists; CTO review |

| AC-5 | `exports/regulatory\_workbook.xlsx` opens, contains four pages, and consumes the export CSV. | Manual review; CTO sign-off |

| AC-6 | `scripts/export\_evidence\_for\_excel.py` runs cleanly and produces a CSV the workbook consumes. | `test\_evidence\_export\_script` |

| AC-7 | `v1.0-benchmark` GitHub release exists with dataset, validator, model, training script, and reproduction guide. | Manual check; CTO review |

| AC-8 | Dashboard shows detection hotspots from `MockNogietAdapter`; clicking a hotspot pre-fills the screening form coordinates. | `test\_detection\_panel\_renders\_hotspots` |

| AC-9 | Soroban contract builds with `stellar contract build`, deploys to Testnet, stores a Merkle root, and verifies a hash. | Manual deploy; Testnet explorer |

| AC-10 | Full backend suite passes; frontend typecheck, lint, build pass; `ruff` and `mypy` clean. | Standard quality gates |



\---



\## 4. Files to Create



\### D2 — Merkle-Tree + Stellar Design

\- `backend/src/odrm/evidence/\_\_init\_\_.py`

\- `backend/src/odrm/evidence/models.py` (ScreeningEvidence, EvidenceBatch)

\- `backend/src/odrm/evidence/schemas.py` (EvidencePublic, EvidenceVerifyResponse)

\- `backend/src/odrm/evidence/repository.py` (EvidenceRepository, MerkleRootRepository)

\- `backend/src/odrm/evidence/service.py` (MerkleService — hashing, root, proof)

\- `backend/src/odrm/api/evidence.py` (verify endpoint router)

\- `backend/migrations/versions/0004\_evidence\_chain.py`

\- `backend/tests/evidence/\_\_init\_\_.py`

\- `backend/tests/evidence/test\_merkle\_service.py`

\- `backend/tests/evidence/test\_evidence\_api.py`

\- `backend/tests/db/test\_evidence\_chain\_migration.py`

\- `docs/STELLAR\_INTEGRATION.md`

\- `docs/SCF\_MILESTONE\_PLAN.md`



\### D2a — Excel Workbook

\- `scripts/export\_evidence\_for\_excel.py`

\- `exports/regulatory\_workbook.xlsx` (release artifact, not tracked)

\- `docs/REGULATORY\_WORKBOOK.md`



\### D3 — Open Benchmark

\- `docs/BENCHMARK\_REPRODUCTION.md`

\- Git tag `v1.0-benchmark`



\### D4 — Dashboard Wiring

\- `frontend/src/components/detection/detection-panel.tsx`

\- `frontend/src/hooks/use-detection.ts`

\- `frontend/src/components/detection/detection-panel.test.tsx`



\### D5 — Soroban Registry

\- `contracts/valoris-evidence/Cargo.toml`

\- `contracts/valoris-evidence/src/lib.rs`

\- `contracts/valoris-evidence/README.md`



\---



\## 5. Files to Modify



\- `backend/src/odrm/api/routes.py` — hook evidence creation into `/api/v1/tea`

\- `backend/src/odrm/api/report.py` — hook evidence creation into `/api/v1/report`

\- `backend/src/odrm/main.py` — wire `EvidenceService` and include evidence router

\- `backend/migrations/env.py` — import evidence models

\- `frontend/src/lib/api.ts` — add evidence verification and detection client functions

\- `frontend/src/lib/types.ts` — add Evidence and Detection types

\- `frontend/src/app/page.tsx` — include `<DetectionPanel>`

\- `README.md` — link to `v1.0-benchmark` release and `docs/BENCHMARK\_REPRODUCTION.md`



\---



\## 6. Technical Design



\### 6.1 Merkle-tree Evidence Chain



\*\*Hash function:\*\* SHA-256.



`screening\_evidence` row:

\- `id` (UUID, PK)

\- `screening\_id` (UUID, FK to TEA screening)

\- `input\_hash` (SHA-256 of canonical JSON input)

\- `output\_hash` (SHA-256 of canonical JSON output)

\- `screening\_hash` (SHA-256 of `input\_hash || output\_hash`)

\- `batch\_id` (UUID, FK to `evidence\_batches.id`)

\- `created\_at`



`evidence\_batches` row:

\- `id` (UUID, PK)

\- `merkle\_root` (String(64) — hex SHA-256)

\- `leaf\_count` (int)

\- `created\_at`

\- `anchor\_status` (`pending`, `anchored\_on\_soroban`, `verified`)



\*\*Batch cadence:\*\* every 100 screenings or every calendar day, whichever first.



\*\*Proof generation:\*\* sibling path from leaf to root. Verification recomputes root from hash + proof and compares to stored `merkle\_root`.



\*\*Soroban anchor (D5):\*\* background job reads `evidence\_batches` where `anchor\_status='pending'`, calls `store\_root(batch\_id, merkle\_root)`, updates `anchor\_status='anchored\_on\_soroban'`.



\### 6.2 Stellar Integration Design (SAC-first)



`STELLAR\_INTEGRATION.md` covers:



1\. \*\*Contract interface:\*\*

&#x20;  ```rust

&#x20;  fn store\_root(env: Env, batch\_id: Symbol, merkle\_root: BytesN<32>) -> Result<(), Error>;

&#x20;  fn verify\_hash(env: Env, batch\_id: Symbol, leaf\_hash: BytesN<32>, proof: Vec<BytesN<32>>) -> Result<bool, Error>;

&#x20;  ```

2\. \*\*Data model:\*\* `batch\_roots: Map<Symbol, BytesN<32>>`. No balances, no transfers.

3\. \*\*SAC integration:\*\* Valoris issues a Stellar Asset (classic `G...` issuer asset) for the carbon credit token. Native controls (freeze, clawback, authorization) handle compliance. Credit issuance happens via the SAC's `mint` function, gated by registry verification.

4\. \*\*Migration path:\*\* off-chain hash chain (D2) → testnet anchor (D5) → mainnet anchor (post-SCF).

5\. \*\*Audit readiness:\*\* the Soroban contract is \~50 lines of Rust, no external calls, no reentrancy surface. The SAC is protocol-audited. Total audit surface is minimal — highly favorable for SCF Audit Bank review.



\### 6.3 SCF Milestone Plan



\*\*Total ask:\*\* $150,000 in XLM (SCF Build Award range).



| Month | Deliverable | Tranche Criteria |

|---|---|---|

| \*\*Month 1\*\* | D2 complete: Merkle-tree audit trail + Stellar design doc. First batch anchored to Testnet. | "Validated idea" → "Prototype on Testnet" |

| \*\*Month 2\*\* | D5 complete: Soroban Registry on Testnet. Integration tests passing. | "Testnet ready" |

| \*\*Month 3\*\* | SCF Audit Bank review passed. Contract hardened. Demo video published. | "Audit passed" |

| \*\*Month 4\*\* | Mainnet deployment. First 10 real batches anchored on-chain. Excel workbook integration tested. | "Mainnet live" |



\*\*Success metrics:\*\* 10+ Mainnet-anchored batches; end-to-end Excel-to-chain verification; 3+ NGFCP permit holders using the workbook; 50+ GitHub clones or stars on the benchmark.



\### 6.4 Excel Workbook Structure



\*\*Page 1 — Operator Screening:\*\* one row per screening; columns: date, operator, site, screening hash, Merkle status (✓/✗), ROI, payback. Slicers: operator, site, date.



\*\*Page 2 — Portfolio Summary:\*\* PivotTables by operator, by state, by screening status. Charts: top 10 sites by ROI; screenings per week time series.



\*\*Page 3 — Scenario Comparison:\*\* pick two screening IDs; side-by-side ROI, payback, CO2, hash status, delta.



\*\*Page 4 — Evidence Trail:\*\* all batches; columns: batch\_id, leaf\_count, merkle\_root (truncated), anchor\_status, anchor\_tx. Slicer: anchor\_status.



\*\*Data connection:\*\* Power Query loads `exports/evidence\_export.csv`. Manual refresh after each batch.



\### 6.5 Detection Dashboard Panel



`frontend/src/components/detection/detection-panel.tsx`:

\- `useDetectionHotspots()` calls `GET /api/v1/detection/hotspots`.

\- Renders hotspot list (lat, lon, intensity, detected\_at).

\- Click → pre-fills the screening form (coordinates) or displays for manual entry.

\- Default source: `mock\_nogiet`.



\---



\## 7. TDD Test Plan



\### 7.1 D2 — Merkle-tree

1\. `test\_screening\_produces\_evidence\_row`

2\. `test\_batch\_root\_computation`

3\. `test\_verify\_valid\_hash`

4\. `test\_verify\_invalid\_hash`

5\. `test\_batch\_anchoring\_status\_transitions`

6\. `test\_evidence\_api\_verify\_endpoint`



\### 7.2 D2a — Excel export

7\. `test\_export\_script\_produces\_csv`

8\. `test\_export\_respects\_date\_range`

9\. Manual workbook review (CTO)



\### 7.3 D3 — Benchmark

10\. `test\_release\_artifact\_contains\_dataset`

11\. `test\_reproduction\_guide\_succeeds`



\### 7.4 D4 — Detection panel

12\. `test\_detection\_panel\_renders\_hotspots`

13\. `test\_detection\_panel\_prefills\_form`



\### 7.5 D5 — Soroban contract

14\. `test\_contract\_stores\_root` (Rust unit)

15\. `test\_contract\_verifies\_hash` (Rust unit)

16\. Testnet deployment smoke test (manual)



\---



\## 8. Commit Message Sequence



\- D2: `feat(evidence): add Merkle-tree screening evidence chain and Stellar integration design`

\- D2a: `feat(reporting): add Excel regulatory reporting workbook and evidence export script`

\- D3: `docs(benchmark): publish v1.0 benchmark dataset and reproduction guide`

\- D4: `feat(dashboard): add detection hotspot panel to screening dashboard`

\- D5: `feat(soroban): add evidence registry contract and testnet deployment`

\- Final: `docs(sprint-11): add sprint 11 report`



\---



\## 9. Audit Protocol



\### Phase 1 (per deliverable)

Load `.opencode/skills/cto-architect/SKILL.md`, `data-engineer/SKILL.md`. For D5, the connected Stellar Docs MCP provides authoritative Soroban syntax. For D2a, load Excel/Power Query conventions if available. Confirm compliance before restating criteria.



\### Phase 2 (per deliverable)

Write `docs/SPRINT\_11X\_PLAN.md` (X = D2, D2a, D3, D4, D5). Stop for CTO approval.



\### Phase 3 (per deliverable)

Show exact file contents in chat. CTO audits. No disk writes.



\### Phase 4 (per deliverable)

TDD: fail, paste failure, implement, pass, paste pass. Run full backend suite, ruff, mypy, frontend gates. Commit with per-deliverable message. Push. Stop for CTO audit.



\### Phase 5 (per deliverable)

Write `docs/SPRINT\_11X\_REPORT.md`.



\### Sprint 11 final

After all five pass, write `docs/SPRINT\_11\_REPORT.md` and submit SCF Build Award application.



\---



\## 10. Out of Scope



\- Mainnet deployment of the Soroban contract (post-SCF)

\- Full RWA carbon credit marketplace or secondary trading

\- Predictive maintenance ML features

\- Multi-tenant scoping

\- Any change to Sprint 10 deliverables (0a, 0b, 0c, D1)

\- Power BI (replaced by Excel)

\- Actual NUPRC/NOGIET integration or live satellite data ingestion

\- Deployment to any hosted environment (all testing local)



\---



\## 11. Timeline



| Week | Focus |

|---|---|

| Week 1 (2026-11-24 to 2026-11-30) | Submit SCF interest form; D2 Phase 1 + plan + implementation (Merkle-tree) |

| Week 2 (2026-12-01 to 2026-12-07) | Complete D2; begin D2a Excel workbook |

| Week 3 (2026-12-08 to 2026-12-14) | Complete D2a; publish D3 benchmark; submit SCF Build Award |

| Week 4 (2026-12-15 to 2026-12-21) | Complete D4 detection panel; begin D5 Soroban prototype |

| Week 5-6 (2026-12-22 to 2027-01-04) | Complete D5 testnet deployment; write Sprint 11 report |



\---



\## 12. Approval Gate



Sprint 11 implementation awaits CTO approval with the exact phrase:



```

AUTHORIZED: Sprint 11 implementation phase

```



No code, no files, no test runs until this phrase is provided.

