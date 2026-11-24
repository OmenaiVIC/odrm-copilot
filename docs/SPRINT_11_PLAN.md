# Sprint 11 Plan — Public-Good Intelligence Layer

| | |
|---|---|
| Status | **Approved - Phase 4 authorized** |
| Date | 2026-11-24 |
| Scope | Merkle-tree ESG audit trail, SAC-first Stellar integration design, cryptographic provenance workbook, open benchmark publication, detection adapter dashboard wiring, and SCF Build Award application preparation |
| Dependency | Sprint 10 complete at `06d969b`; Stellar CLI installed (v30.0.1); Stellar MCPs connected |
| Approval phrase | `AUTHORIZED: Sprint 11 implementation phase` |

> **Planning gate:** This file is the Sprint 11 plan. No implementation code, test code, or file creation beyond this plan until the CTO approves with the exact phrase above.

> **Architecture decisions (2026-11-24):**
> - **SAC-first:** Carbon credits are issued as Stellar Assets (classic `G...` issuer assets) using the native Stellar Asset Contract (SAC) for compliance. The Soroban contract is a **minimal Evidence Registry** (`store_root`, `verify_hash` only). No custom token logic.
> - **Excel instead of Power BI:** Power BI Desktop is free but the Service tier requires ~$10/user/month for sharing with regulators. Excel delivers the same promise with zero licensing cost and zero friction.
> - **Regulator-agnostic:** All whitelist and detection claims remain hedged. NOGIET-style is one example among many.

---

## 1. Goal

Deliver the public-good intelligence layer of Valoris: cryptographic ESG evidence (Merkle-tree audit trail), a clear on-chain integration path (Stellar Assets + SAC + minimal Soroban registry), a cryptographic provenance workbook (Excel), the open benchmark publication (MIT-licensed dataset + validator + baseline model), and detection adapter dashboard wiring. Prepare and submit the Stellar Community Fund (SCF) Build Award application by year-end 2026.

Sprint 11 does not deploy to Mainnet, does not build a full RWA marketplace, and does not modify Sprint 10 deliverables.

---

## 2. Deliverables

### D2 — Merkle-Tree ESG Audit Trail + Stellar Integration Design

1. **Merkle-tree hash chain for every screening.** Every `/api/v1/tea` and `/api/v1/report` call produces a cryptographic hash chain: individual screening hash -> batch root -> daily root. Stored in a new `screening_evidence` table.
2. **Verification endpoint.** `GET /api/v1/evidence/verify/{hash}` returns the Merkle proof path and validates against the root.
3. **Stellar Integration Design Document.** `docs/STELLAR_INTEGRATION.md` describing:
   - Contract interface: `store_root(batch_id, merkle_root)` and `verify_hash(batch_id, leaf_hash, proof) -> bool` — registry only, no token logic.
   - Data model: `batch_roots` map, no balances.
   - **SAC integration:** Valoris acts as the asset issuer. Credits are issued via the Stellar Asset Contract's `mint`/`transfer` calls, gated by the registry's verification. Native Stellar compliance features (freeze, clawback, authorization flags) are used for regulatory control.
   - Migration path: off-chain hash chain (D2) -> testnet anchor (D5) -> mainnet anchor (post-SCF).
   - Audit readiness: what SCF Audit Bank will review (registry contract only, not the SAC).
4. **SCF Build Award Milestone Plan.** `docs/SCF_MILESTONE_PLAN.md` — 3–4 month tranche structure for the SCF Build Award (Integration Track). Total ask within $150K XLM range.

### D2a — Cryptographic Provenance Workbook (Excel)

5. **MIT-licensed Excel template.** `exports/regulatory_workbook.xlsx` (published via release, not tracked in git). The workbook is a **cryptographic provenance audit tool, not a financial dashboard.** It consumes the D2 evidence chain output and contains four pages:
   - **Operator Screening:** per-screening view with hash, batch_id, **Integrity Status** (✓ Verified / ✗ Failed), leaf_index, and date. (Note: "Integrity Status" is the plain-English label for the Merkle proof verification).
   - **Portfolio Summary:** charts for screening volume over time and batch sizes. No ROI or financial data (see "Data source limitation" below).
   - **Scenario Comparison:** lookup sheet to compare two screening hashes and confirm batch membership.
   - **Evidence Trail:** all batches with batch_id, leaf_count, merkle_root (truncated), anchor_status, anchor_tx (blank until D5).
6. **Data export script.** `scripts/export_evidence_for_excel.py` — exports `screening_evidence` and `evidence_batches` to CSV for the workbook. Uses `openpyxl` to generate the `.xlsx` file programmatically.
7. **Workbook documentation.** `docs/REGULATORY_WORKBOOK.md` — explicitly states that **financial data (ROI, payback, CO2, operator, site) is NOT in this workbook** because the D2 evidence schema stores only cryptographic hashes. Financial portfolio reporting is a separate future deliverable (Sprint 12). The workbook's purpose is regulatory-grade provenance verification.

### D3 — Open Benchmark Publication

8. **MIT-licensed release.** Tagged GitHub release `v1.0-benchmark` containing: the 10,000-scenario dataset, schema validator, baseline XGBoost model, training script, and ODRM physics benchmark documentation.
9. **Reproduction guide.** `docs/BENCHMARK_REPRODUCTION.md`.

### D4 — Detection Adapter Dashboard Wiring

10. **Dashboard detection panel.** New component showing hotspots from the configured `DetectionSource`. Default is `MockNogietAdapter`.
11. **API client extension.** `GET /api/v1/detection/hotspots` wired into the frontend with TanStack Query.

### D5 — Soroban Evidence Registry Prototype

12. **Minimal Soroban contract.** `contracts/valoris-evidence/` — Rust contract with two functions only: `store_root`, `verify_hash`. Deployed to Testnet. Ready for SCF Audit Bank review.

---

## 3. Acceptance Criteria

| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | Every `/api/v1/tea` call produces a `screening_evidence` row with valid SHA-256 hashes. | `test_tea_creates_evidence_row` |
| AC-2 | `GET /api/v1/evidence/verify/{hash}` returns a valid Merkle proof path and confirms inclusion in the current batch root. | `test_evidence_verification_round_trip` |
| AC-3 | `docs/STELLAR_INTEGRATION.md` exists with all five sections (contract interface, data model, SAC integration, migration path, audit readiness). | File exists; CTO review |
| AC-4 | `docs/SCF_MILESTONE_PLAN.md` exists with 3–4 month tranche structure and SCF Build Award total ask. | File exists; CTO review |
| AC-5 | `exports/regulatory_workbook.xlsx` opens, contains four pages (Operator Screening, Portfolio Summary, Scenario Comparison, Evidence Trail), and consumes the export CSV. **The workbook is a cryptographic provenance audit tool, not a financial dashboard.** | Manual review; CTO sign-off |
| AC-6 | `scripts/export_evidence_for_excel.py` runs cleanly and produces a CSV the workbook consumes. | `test_evidence_export_script` |
| AC-7 | `v1.0-benchmark` GitHub release exists with dataset, validator, model, training script, and reproduction guide. | Manual check; CTO review |
| AC-8 | Dashboard shows detection hotspots from `MockNogietAdapter`; clicking a hotspot pre-fills the screening form coordinates. | `test_detection_panel_renders_hotspots` |
| AC-9 | Soroban contract builds with `stellar contract build`, deploys to Testnet, stores a Merkle root, and verifies a hash. | Manual deploy; Testnet explorer |
| AC-10 | Full backend suite passes; frontend typecheck, lint, build pass; `ruff` and `mypy` clean. | Standard quality gates |

---

## 4. Files to Create

### D2 — Merkle-Tree + Stellar Design
- `backend/src/odrm/evidence/__init__.py`
- `backend/src/odrm/evidence/models.py` (ScreeningEvidence, EvidenceBatch)
- `backend/src/odrm/evidence/schemas.py` (EvidencePublic, EvidenceVerifyResponse)
- `backend/src/odrm/evidence/repository.py` (EvidenceRepository, MerkleRootRepository)
- `backend/src/odrm/evidence/service.py` (MerkleService — hashing, root, proof)
- `backend/src/odrm/api/evidence.py` (verify endpoint router)
- `backend/migrations/versions/0004_evidence_chain.py`
- `backend/tests/evidence/__init__.py`
- `backend/tests/evidence/test_merkle_service.py`
- `backend/tests/evidence/test_evidence_api.py`
- `backend/tests/db/test_evidence_chain_migration.py`
- `docs/STELLAR_INTEGRATION.md`
- `docs/SCF_MILESTONE_PLAN.md`

### D2a — Cryptographic Provenance Workbook
- `scripts/export_evidence_for_excel.py`
- `exports/regulatory_workbook.xlsx` (release artifact, not tracked)
- `docs/REGULATORY_WORKBOOK.md`

### D3 — Open Benchmark
- `docs/BENCHMARK_REPRODUCTION.md`
- Git tag `v1.0-benchmark`

### D4 — Dashboard Wiring
- `frontend/src/components/detection/detection-panel.tsx`
- `frontend/src/hooks/use-detection.ts`
- `frontend/src/components/detection/detection-panel.test.tsx`

### D5 — Soroban Registry
- `contracts/valoris-evidence/Cargo.toml`
- `contracts/valoris-evidence/src/lib.rs`
- `contracts/valoris-evidence/README.md`

---

## 5. Files to Modify

- `backend/src/odrm/api/routes.py` — hook evidence creation into `/api/v1/tea`
- `backend/src/odrm/api/report.py` — hook evidence creation into `/api/v1/report`
- `backend/src/odrm/main.py` — wire `EvidenceService` and include evidence router
- `backend/migrations/env.py` — import evidence models
- `frontend/src/lib/api.ts` — add evidence verification and detection client functions
- `frontend/src/lib/types.ts` — add Evidence and Detection types
- `frontend/src/app/page.tsx` — include `<DetectionPanel>`
- `README.md` — link to `v1.0-benchmark` release and `docs/BENCHMARK_REPRODUCTION.md`

---

## 6. Technical Design

### 6.1 Merkle-tree Evidence Chain

**Hash function:** SHA-256.

`screening_evidence` row:
- `id` (UUID, PK)
- `screening_id` (UUID, FK to TEA screening)
- `input_hash` (SHA-256 of canonical JSON input)
- `output_hash` (SHA-256 of canonical JSON output)
- `screening_hash` (SHA-256 of `input_hash || output_hash`)
- `batch_id` (UUID, FK to `evidence_batches.id`)
- `created_at`

`evidence_batches` row:
- `id` (UUID, PK)
- `merkle_root` (String(64) — hex SHA-256)
- `leaf_count` (int)
- `created_at`
- `anchor_status` (`pending`, `anchored_on_soroban`, `verified`)

**Batch cadence:** every 100 screenings or every calendar day, whichever first.

**Proof generation:** sibling path from leaf to root. Verification recomputes root from hash + proof and compares to stored `merkle_root`.

**Soroban anchor (D5):** background job reads `evidence_batches` where `anchor_status='pending'`, calls `store_root(batch_id, merkle_root)`, updates `anchor_status='anchored_on_soroban'`.

### 6.2 Stellar Integration Design (SAC-first)

`STELLAR_INTEGRATION.md` covers:

1. **Contract interface:**
   `fn store_root(env: Env, batch_id: Symbol, merkle_root: BytesN<32>) -> Result<(), Error>;`
   `fn verify_hash(env: Env, batch_id: Symbol, leaf_hash: BytesN<32>, proof: Vec<BytesN<32>>) -> Result<bool, Error>;`
2. **Data model:** `batch_roots: Map<Symbol, BytesN<32>>`. No balances, no transfers.
3. **SAC integration:** Valoris issues a Stellar Asset (classic `G...` issuer asset) for the carbon credit token. Native controls (freeze, clawback, authorization) handle compliance. Credit issuance happens via the SAC's `mint` function, gated by registry verification.
4. **Migration path:** off-chain hash chain (D2) -> testnet anchor (D5) -> mainnet anchor (post-SCF).
5. **Audit readiness:** the Soroban contract is ~50 lines of Rust, no external calls, no reentrancy surface. The SAC is protocol-audited. Total audit surface is minimal — highly favorable for SCF Audit Bank review.

### 6.3 SCF Milestone Plan

**Total ask:** $150,000 in XLM (SCF Build Award range).

| Month | Deliverable | Tranche Criteria |
|---|---|---|
| **Month 1** | D2 complete: Merkle-tree audit trail + Stellar design doc. First batch anchored to Testnet. | "Validated idea" -> "Prototype on Testnet" |
| **Month 2** | D5 complete: Soroban Registry on Testnet. Integration tests passing. | "Testnet ready" |
| **Month 3** | SCF Audit Bank review passed. Contract hardened. Demo video published. | "Audit passed" |
| **Month 4** | Mainnet deployment. First 10 real batches anchored on-chain. Excel workbook integration tested. | "Mainnet live" |

**Success metrics:** 10+ Mainnet-anchored batches; end-to-end Excel-to-chain verification; 3+ NGFCP permit holders using the workbook; 50+ GitHub clones or stars on the benchmark.

### 6.4 Cryptographic Provenance Workbook Structure

**Page 1 — Operator Screening:** one row per screening; columns: date, screening_hash, batch_id, **Integrity Status** (✓/✗), leaf_index. Slicers: date.

**Page 2 — Portfolio Summary:** Charts: screenings per week time series; batch sizes.

**Page 3 — Scenario Comparison:** lookup sheet to compare two screening hashes and confirm batch membership.

**Page 4 — Evidence Trail:** all batches; columns: batch_id, leaf_count, merkle_root (truncated), anchor_status, anchor_tx. Slicer: anchor_status.

**Data connection:** Rerun `scripts/export_evidence_for_excel.py` to refresh data.

### 6.5 Detection Dashboard Panel

`frontend/src/components/detection/detection-panel.tsx`:
- `useDetectionHotspots()` calls `GET /api/v1/detection/hotspots`.
- Renders hotspot list (lat, lon, intensity, detected_at).
- Click -> pre-fills the screening form (coordinates) or displays for manual entry.
- Default source: `mock_nogiet`.

---

## 7. TDD Test Plan

### 7.1 D2 — Merkle-tree
1. `test_screening_produces_evidence_row`
2. `test_batch_root_computation`
3. `test_verify_valid_hash`
4. `test_verify_invalid_hash`
5. `test_batch_anchoring_status_transitions`
6. `test_evidence_api_verify_endpoint`

### 7.2 D2a — Cryptographic Provenance Workbook
7. `test_export_script_produces_csv`
8. `test_export_respects_date_range`
9. `test_export_includes_all_required_columns`
10. `test_integrity_status_is_verified_for_valid_row`
11. Manual workbook review (CTO)

### 7.3 D3 — Benchmark
12. `test_release_artifact_contains_dataset`
13. `test_reproduction_guide_succeeds`

### 7.4 D4 — Detection panel
14. `test_detection_panel_renders_hotspots`
15. `test_detection_panel_prefills_form`

### 7.5 D5 — Soroban contract
16. `test_contract_stores_root` (Rust unit)
17. `test_contract_verifies_hash` (Rust unit)
18. Testnet deployment smoke test (manual)

---

## 8. Commit Message Sequence

- D2: `feat(evidence): add Merkle-tree screening evidence chain and Stellar integration design`
- D2a: `feat(reporting): add cryptographic provenance workbook and export script`
- D3: `docs(benchmark): publish v1.0 benchmark dataset and reproduction guide`
- D4: `feat(dashboard): add detection hotspot panel to screening dashboard`
- D5: `feat(soroban): add evidence registry contract and testnet deployment`
- Final: `docs(sprint-11): add sprint 11 report`

---

## 9. Audit Protocol

### Phase 1 (per deliverable)
Load `.opencode/skills/cto-architect/SKILL.md`, `data-engineer/SKILL.md`. For D5, the connected Stellar Docs MCP provides authoritative Soroban syntax. For D2a, load Excel/Power Query conventions if available. Confirm compliance before restating criteria.

### Phase 2 (per deliverable)
Write `docs/SPRINT_11X_PLAN.md` (X = D2, D2a, D3, D4, D5). Stop for CTO approval.

### Phase 3 (per deliverable)
Show exact file contents in chat. CTO audits. No disk writes.

### Phase 4 (per deliverable)
TDD: fail, paste failure, implement, pass, paste pass. Run full backend suite, ruff, mypy, frontend gates. Commit with per-deliverable message. Push. Stop for CTO audit.

### Phase 5 (per deliverable)
Write `docs/SPRINT_11X_REPORT.md`.

### Sprint 11 final
After all five pass, write `docs/SPRINT_11_REPORT.md` and submit SCF Build Award application.

---

## 10. Out of Scope

- Mainnet deployment of the Soroban contract (post-SCF)
- Full RWA carbon credit marketplace or secondary trading
- Predictive maintenance ML features
- Multi-tenant scoping
- Any change to Sprint 10 deliverables (0a, 0b, 0c, D1)
- Power BI (replaced by Excel)
- Actual NUPRC/NOGIET integration or live satellite data ingestion
- Deployment to any hosted environment (all testing local)
- Financial data (ROI, payback, CO2) in the workbook (deferred to Sprint 12)
- Live Next.js portfolio dashboard (deferred to Sprint 12)

---

## 11. Timeline

| Week | Focus |
|---|---|
| Week 1 (2026-11-24 to 2026-11-30) | Submit SCF interest form; D2 Phase 1 + plan + implementation (Merkle-tree) |
| Week 2 (2026-12-01 to 2026-12-07) | Complete D2; begin D2a workbook |
| Week 3 (2026-12-08 to 2026-12-14) | Complete D2a; publish D3 benchmark; submit SCF Build Award |
| Week 4 (2026-12-15 to 2026-12-21) | Complete D4 detection panel; begin D5 Soroban prototype |
| Week 5-6 (2026-12-22 to 2027-01-04) | Complete D5 testnet deployment; write Sprint 11 report |

---

## 12. Approval Gate

Sprint 11 implementation awaits CTO approval with the exact phrase:

`AUTHORIZED: Sprint 11 implementation phase`

No code, no files, no test runs until this phrase is provided.