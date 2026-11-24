# SCF Build Award Milestone Plan

| | |
|---|---|
| Applicant | Valoris (ODRM-Copilot) |
| Program | Stellar Community Fund, Build Award |
| Track | Integration |
| Total ask | US$150,000 in XLM |
| Duration | 4 months |
| Status | Draft for Sprint 11 submission |
| Source of truth | `docs/SPRINT_11_PLAN.md` |

## 1. Summary

Valoris gives methane-to-syngas project developers a fast techno-economic
screening tool and a tamper-evident ESG evidence trail. Every screening is
hashed, batched into a Merkle tree, and made independently verifiable. Carbon
credits are issued as Stellar Assets through the Stellar Asset Contract (SAC).
A minimal Soroban Evidence Registry anchors batch roots so regulators, auditors,
and buyers can verify inclusion without trusting the operator's database.

SCF funding covers production hardening, Testnet anchoring, an independent audit,
Mainnet deployment, and adoption work with permit holders. The core off-chain
evidence chain and the Soroban prototype are delivered in Sprint 11 as
pre-award work and are disclosed below.

## 2. Pre-award baseline and matching contribution

The following are already delivered or scheduled in Sprint 11 before an award:

- Merkle-tree evidence chain for `/tea` and `/report`.
- Canonical hashing and proof format with a public verification API.
- Minimal Soroban Evidence Registry design and Testnet prototype (D5).
- Cryptographic provenance workbook and CSV export (D2a).
- MIT-licensed benchmark release and reproduction guide (D3).

SCF funds are not requested to redo this work. They fund hardening, audit,
Mainnet operations, and adoption. The baseline reduces technical risk and gives
reviewers working code to inspect.

## 3. Problem and beneficiaries

Methane conversion projects need bankable numbers and defensible records.
Spreadsheet models are opaque, and ESG claims are difficult to audit. Valoris
addresses both:

- Deterministic screening with published assumptions and warnings.
- Cryptographic evidence that a specific screening existed at a specific time.
- A regulator-facing workbook that consumes the same evidence.
- An open benchmark that lets third parties reproduce model behavior.

Beneficiaries: project developers, flare operators, permit holders, ESG auditors,
credit buyers, and regulators evaluating methane-abatement claims.

## 4. Scope of SCF-funded work

In scope:

1. Testnet and Mainnet anchoring of batch roots.
2. Evidence Registry hardening and independent audit.
3. Production key management and operational runbooks.
4. Provenance workbook adoption with permit holders.
5. Documentation, demo materials, and maintenance during the award period.

Out of scope:

- A full carbon-credit marketplace or secondary trading.
- Custody of user funds.
- Regulatory approval in any jurisdiction.
- Custom token logic outside the SAC.
- Predictive-maintenance ML features.

## 5. Milestones and tranches

The award is structured as four monthly tranches. Percentages are proposed and
will be normalized to the SCF template. XLM amounts are fixed at disbursement
according to the program's conversion rules.

### Milestone 1 — Testnet evidence anchoring and cryptographic provenance workbook (Month 1)

- Allocation: 25% (US$37,500).
- Deliverables:
  - D2 evidence chain running in the awarded repository.
  - D5 registry deployed to Testnet with `store_root` and `verify_hash`.
  - Anchor worker publishing at least one real batch root.
  - Cryptographic provenance workbook and export script validated against stored evidence.
- Acceptance:
  - A stored screening verifies off-chain and on-chain with the same result.
  - One Testnet transaction hash is published and independently checked.
  - Workbook opens with four pages and loads the export CSV.
  - Backend suite, `ruff`, and `mypy` pass.
- Evidence: Testnet contract ID, transaction hash, test output, workbook screenshots, tagged commit.

### Milestone 2 — Registry hardening and integration tests (Month 2)

- Allocation: 30% (US$45,000).
- Deliverables:
  - Completed Rust unit and integration test suite for the registry.
  - Shared proof test vectors used by Python and Rust.
  - Anchor worker retries, monitoring, and runbook.
  - Benchmark release available for reviewer reproduction.
- Acceptance:
  - Proof agreement across 1, 2, 3, 4, and 100 leaves.
  - Tampered leaf, sibling, root, index, count, and proof length are rejected.
  - Duplicate root and unauthorized caller are rejected.
  - CI runs both stacks on every change.
- Evidence: CI links, test reports, contract commit hash, runbook.

### Milestone 3 — Independent audit and demo (Month 3)

- Allocation: 25% (US$37,500).
- Deliverables:
  - SCF Audit Bank review completed with no unresolved critical findings.
  - Fixes for all accepted findings and a published audit summary.
  - Five-minute demo covering screening, evidence, anchor, and verification.
  - Regulator-facing documentation for the workbook and evidence model.
- Acceptance:
  - Audit report is public or shared with SCF reviewers.
  - Critical and high findings are closed or documented with accepted risk.
  - Demo reproduces a full screening-to-chain verification path.
- Evidence: audit report, remediation commit, demo link, documentation links.

### Milestone 4 — Mainnet launch and first ten batches (Month 4)

- Allocation: 20% (US$30,000).
- Deliverables:
  - Evidence Registry deployed to Mainnet.
  - First 10 real batch roots anchored.
  - End-to-end Excel-to-chain verification for at least one batch.
  - Onboarding materials and office hours for permit holders.
- Acceptance:
  - 10 Mainnet batches are publicly verifiable.
  - A third party verifies a proof without access to the internal database.
  - Three or more permit holders have used the workbook.
  - Incident and rollback procedures are exercised once.
- Evidence: Mainnet contract ID, 10 transaction hashes, verification log,
  adoption notes.

## 6. Proposed budget allocation

| Category | Share | Amount (USD) | Purpose |
|---|---:|---:|---|
| Engineering | 60% | 90,000 | Registry, anchor worker, API, workbook integration |
| Security audit | 20% | 30,000 | Independent review and remediation |
| Infrastructure and operations | 8% | 12,000 | Testnet/Mainnet accounts, monitoring, RPC access |
| Documentation and adoption | 12% | 18,000 | Guides, demo, permit-holder onboarding |

The split is a planning estimate. Final line items follow the SCF application
template and the program's eligible-cost rules.

## 7. Success metrics

- 10 or more Mainnet-anchored batches within the award period.
- End-to-end Excel-to-chain verification demonstrated.
- 3 or more permit holders actively using the workbook.
- 50 or more GitHub clones or stars on the benchmark release.
- Zero unresolved critical audit findings at award close.
- Anchor SLA met for 95% of batches after Mainnet launch.

## 8. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Audit finds a proof-handling defect | Schedule slip | Freeze the interface after Month 2; budget remediation time in Month 3. |
| Mainnet key compromise | Loss of trust | Multisig issuer, separate worker key, documented rotation, hardware signing. |
| Low permit-holder adoption | Weak outcome evidence | Start onboarding in Month 2 with workbook pilots; publish guides early. |
| Testnet instability | Delayed anchoring | Retry queue, idempotent writes, read-back verification, local root retention. |
| Scope creep into marketplace features | Missed milestones | Written out-of-scope list; change control with SCF reviewers. |
| Oracle or RPC outage | Anchor delay | Multiple RPC endpoints; alerting; no on-chain dependency in the screening path. |

## 9. Reporting and governance

- Monthly written update with milestone status, transaction hashes, and demo links.
- Public repository history is the primary evidence of work.
- All contract changes after the audit freeze require a documented review.
- Security incidents are reported to SCF within 48 hours with a remediation plan.
- Funds are used only for the activities in section 6.

## 10. Out of scope

- Mainnet deployment before audit completion.
- Carbon-credit trading, order books, or liquidity provision.
- Fiat on-ramps, custody, or payment processing.
- Jurisdiction-specific legal advice or regulatory filings.
- Custom token contracts that duplicate SAC behavior.

## 11. Submission checklist

- [ ] Confirm applicant entity and payout account.
- [ ] Attach `docs/STELLAR_INTEGRATION.md` and this plan.
- [ ] Link the public repository and Sprint 11 commit.
- [ ] Provide Testnet contract ID and sample transaction hash.
- [ ] Normalize tranche percentages to the SCF template.
- [ ] Convert the US$150,000 ask to XLM using the program's guidance.
- [ ] Confirm audit scope with the SCF Audit Bank.
- [ ] Submit before the year-end 2026 target.

## 12. Acceptance traceability

- AC-3: `docs/STELLAR_INTEGRATION.md` covers contract interface, data model, SAC
  integration, migration path, and audit readiness.
- AC-4: this document defines a four-month tranche structure and a US$150,000
  total ask.
- Sprint 11 does not deploy to Mainnet; Mainnet milestones begin only after an
  award and a passed audit.