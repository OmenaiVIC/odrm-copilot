# ODRM-Copilot - SCF Build Award Milestone Plan

| | |
|---|---|
| Status | Submission draft |
| Date | 2026-11-24 |
| Track | Stellar Community Fund Build Award, Integration Track |
| Duration | 4 months |
| Total ask | US$150,000 equivalent in XLM |
| Project | ODRM-Copilot public-good ESG evidence and carbon-credit infrastructure |

---

## 1. Summary

ODRM-Copilot is a surrogate-model and decision-support platform for Oxy-Dry Reforming of
Methane (ODRM) and flare-gas valorization. This award funds the public-good layer: a
tamper-evident screening evidence chain, a minimal on-chain Evidence Registry, and an
SAC-first carbon-credit path that regulators and NGFCP permit holders can verify without
trusting a vendor.

The 4-month plan moves from a working off-chain Merkle audit trail (D2, already
implemented) to a Testnet Soroban registry (D5), an audit-ready contract, and a
controlled Mainnet launch with real anchored batches. The existing benchmark, Excel
workbook, and dashboard work are supporting public goods, not substitutes for the
milestones below.

---

## 2. Why Stellar

- **SAC-first compliance.** Carbon credits remain classic Stellar assets. Native freeze,
  clawback, authorization, and transfer rules provide the controls regulators expect. No
  custom token logic and no new custody surface.
- **Minimal on-chain footprint.** Only a 32-byte Merkle root per batch is stored. The
  registry has two functions and no external calls, which keeps audit cost and risk low.
- **Low, predictable fees.** Anchoring batches is cheap enough to run continuously and
  transparently.
- **Audit-friendly.** The registry is small enough for a focused SCF Audit Bank review;
  the SAC is protocol-audited and out of the custom audit scope.

---

## 3. Scope

In scope across the award:

- D2 evidence chain hardening, documentation, and operational runbooks.
- D5 Soroban Evidence Registry (`store_root`, `verify_hash`) on Testnet.
- Anchor job, reconciliation, retry, and monitoring.
- Audit readiness, Audit Bank review, and remediation.
- Mainnet deployment and the first 10 production batches.
- Excel-to-chain verification for the regulatory reporting workflow.
- Public documentation and a demo video.

Out of scope:

- Custom token contracts or custom DeFi logic.
- Mainnet deployment before a completed audit cycle.
- Stellar asset issuance terms, pricing, or securities advice.
- Replacing the existing TEA model or the regulatory reporting standard.

---

## 4. Milestones and tranches

| Month | Tranche | Amount (US$) | Deliverable | Release criteria |
|---|---|---:|---|---|
| Month 1 | 25% | 37,500 | D2 evidence chain complete and documented; Stellar integration design frozen; first Testnet anchor spike | "Validated idea -> Prototype on Testnet" |
| Month 2 | 30% | 45,000 | D5 registry deployed to Testnet; anchor job and integration tests passing; demo environment | "Testnet ready" |
| Month 3 | 25% | 37,500 | SCF Audit Bank review passed or remediation complete; contract hardened; monitoring and runbooks; demo video published | "Audit passed" |
| Month 4 | 20% | 30,000 | Mainnet deployment; first 10 real batches anchored; Excel-to-chain verification tested with users | "Mainnet live" |
| **Total** | **100%** | **150,000** | | |

### Month 1 - Evidence foundation

- D2 off-chain Merkle audit trail: canonical hashing, batching, proof verification,
  authenticated verify endpoint, migration, and test coverage.
- `docs/STELLAR_INTEGRATION.md` frozen as the byte contract for D5.
- Testnet anchor spike using the D5 contract skeleton to validate the end-to-end path.
  This is early D5 work funded by the award, not part of D2 acceptance.

Evidence: merged commits, test results, design document, Testnet transaction hash.

### Month 2 - Testnet registry

- `contracts/valoris-evidence/` with `store_root` and `verify_hash` only.
- Batch identifier mapping, proof direction encoding, and authorization finalized.
- Anchor job reading `pending` batches, writing roots, recording transaction hashes, and
  retrying idempotently.
- Integration tests proving an off-chain root and proof verify on Testnet.

Evidence: deployed contract ID, Testnet transactions, test logs, demo environment.

### Month 3 - Audit and hardening

- SCF Audit Bank review, findings log, and remediation.
- Contract freeze candidate, key-management runbook, monitoring, and alerting.
- Demo video and operator documentation.
- No Mainnet deployment in this month.

Evidence: audit report or review sign-off, remediation commits, runbook, video link.

### Month 4 - Production launch

- Mainnet registry deployment and relayer operation.
- First 10 real batches anchored and independently verified.
- Excel workbook performs end-to-end verification against the Mainnet registry.
- Onboarding of at least 3 NGFCP permit holders to the reporting workflow.

Evidence: Mainnet contract ID, 10+ anchored batch transactions, verification screenshots,
user onboarding records.

---

## 5. Budget

| Category | Share | Amount (US$) | Purpose |
|---|---:|---:|---|
| Engineering and delivery | 60% | 90,000 | Contract, anchor job, backend, tests, documentation, integration |
| Security audit and Audit Bank readiness | 20% | 30,000 | External review, remediation, audit coordination |
| Infrastructure and operations | 8% | 12,000 | RPC providers, Testnet/Mainnet operations, monitoring, backups |
| Contingency | 12% | 18,000 | Schedule, audit, or deployment risk |
| **Total** | **100%** | **150,000** | |

The award is denominated in XLM at disbursement. USD figures are the planning reference
and may be converted at the prevailing rate. Contingency is released only with a written
change note and is reported in the monthly update.

---

## 6. Success metrics

- 10+ Mainnet-anchored evidence batches.
- End-to-end Excel-to-chain verification for a real screening.
- 3+ NGFCP permit holders using the reporting workbook.
- 50+ GitHub clones or stars on the open benchmark.
- Zero unverified roots reported as verified.
- Anchor job success rate above 99% after retry, with alerting on every terminal failure.

---

## 7. Reporting and governance

- Monthly written update covering progress, spend, risks, and next-month commitments.
- Every tranche release is tied to the evidence listed in section 4.
- Public repository commits and Testnet/Mainnet transaction references accompany each
  milestone claim.
- Material scope changes require written approval before work starts.
- Security incidents are disclosed to SCF within 24 hours and remediated before the next
  tranche request.

---

## 8. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Audit findings delay Month 3 | Tranche slip | Freeze scope in Month 2; reserve contingency; start audit scheduling early |
| Testnet or RPC instability | Anchor job failures | Multiple providers, retry with backoff, idempotent writes, reconciliation |
| Relayer or issuer key compromise | Unauthorized roots or issuance | Separate roles, secret manager, rotation runbook, least-privilege authorization |
| Batch identifier or proof-format mismatch | Unverifiable proofs | Freeze the D2 byte contract before D5 coding; integration tests across both sides |
| Mainnet cost or congestion | Launch delay | Measure Testnet costs, cap batch anchor frequency, batch roots rather than leaves |
| Scope creep into token design | Audit and schedule risk | SAC-first boundary; token economics explicitly out of scope |

---

## 9. Dependencies and assumptions

- SCF approval and tranche disbursement on the agreed schedule.
- Audit Bank capacity in Month 3.
- Access to Stellar Testnet and Mainnet RPC providers.
- At least 3 NGFCP permit holders willing to trial the workbook in Month 4.
- The D2 evidence chain remains the system of record; the chain stores commitments only.

---

## 10. Acceptance evidence checklist

- [ ] D2 design and implementation commit with green backend suite, ruff, and mypy.
- [ ] `docs/STELLAR_INTEGRATION.md` frozen before D5 implementation.
- [ ] Testnet contract ID and `store_root` / `verify_hash` transactions.
- [ ] Anchor job integration test output and retry evidence.
- [ ] Audit review sign-off or remediation closure.
- [ ] Mainnet contract ID and 10+ anchored batch transactions.
- [ ] Excel-to-chain verification artifact.
- [ ] Demo video and monthly reports for all four months.
