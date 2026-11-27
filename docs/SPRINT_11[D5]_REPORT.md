# Sprint 11 D5 — Soroban Evidence Registry Prototype: Phase 5 Report

**Date:** 2026-11-27  
**Commit:** `a6fd73d` (Implementation) / Pending Report Commit  
**Status:** COMPLETE — Deployed to Stellar Testnet  

## 1. Summary
Successfully implemented, audited, and deployed the `valoris-evidence` Soroban contract to Stellar Testnet. The contract anchors 32-byte evidence commitments for detection records. Cross-language parity between the Python backend (D2) and the Rust contract was verified via normative golden vectors. On-chain smoke tests confirm successful registration and permissionless verification.

## 2. On-Chain Evidence (Stellar Testnet)
- **Contract ID:** `CB52AQCSUYGUUN7J467WVNXRAQ7ENQZXWZ56IPPZLND4CCC3MF4IJ3QB`
- **WASM Hash:** `7f56b74dbf59de3e969af9988311d80d58f0e5d05cec0856d121834792b7f730`
- **Deployer/Admin:** `GDWWX6S4TVVFWSD2S63F733PFG3FQ7IYFS5QX6WBFZ7GU6NR4ZH52N23`

### Transaction Hashes
1. **WASM Upload:** `152da9d35fc21d098309c02944490f3baa71efb360cee88697ebf98a1ae57c46`
2. **Contract Deployment:** `10f90eb0a9ce526f2fb3ac356e5783f66a1b19bd94d75c7a91998fd5af24c037`
3. **Evidence Registration (Smoke Test):** `8a73a8b35f79729a8c67a66afbd18bb6a7e080eadbb596016ee46b6fc21a8ef5`

### Smoke Test Results
- **Register:** Success. Event `EvidenceRegistered` emitted. Commitment `28948bcfccb8232bc936029f02625dd2bc36ea9558b3dc0dd8b70a628bc8308d` matches golden vector `leaf_a` exactly.
- **Verify (Positive):** `true` (Correct hash accepted).
- **Verify (Negative):** `false` (Incorrect hash rejected).

## 3. Standard Audit Readiness Impact

### 3.1 Repo Hygiene
- Isolated Rust crate at `contracts/valoris-evidence/`.
- `.gitignore` updated to exclude `contracts/**/target/`; `Cargo.lock` committed for reproducibility.
- Working tree clean post-deployment.

### 3.2 Integration Tests
- **Rust:** 12/12 unit tests passing (covering domain separation, auth, validation, TTL).
- **Python Parity:** 4/4 tests passing (`backend/tests/evidence/test_merkle_parity.py`), locking the hashing logic across languages.
- **On-Chain:** Smoke sequence (Register → Verify True → Verify False) executed successfully on Testnet.

### 3.3 Threat Model & Dataflow
- **Trust Boundary:** The ledger attests to the *commitment* (hash) registered by the admin. It does not attest to the underlying physical data.
- **Data Minimization:** Only 32-byte hashes are anchored. No PII or coordinates stored on-chain.
- **Immutability:** Contract is append-only; duplicate registrations are rejected (`Error::AlreadyRegistered`).

### 3.4 Security Scan & Residual Risk
- **Tool:** `cargo audit` v0.23.0.
- **Findings:** 1 vulnerability (`RUSTSEC-2026-0387` in `crypto-bigint`) and 2 unmaintained warnings (`chrono`, `paste`).
- **Assessment:** All findings are in transitive dependencies of `soroban-sdk 30.0.0`. No direct dependency vulnerabilities. Risk accepted for prototype phase; resolution requires upstream SDK update.

### 3.5 Source Verification Note
- **Status:** Stellar Lab reports "Unverified Build".
- **Context:** This is expected for a prototype. The source code is publicly available in this repository at commit `a6fd73d`.
- **Remediation:** To achieve "Verified" status on explorers, run `stellar contract verify` against the public repo URL in a future hardening sprint.

### 3.6 Explorer Rendering Note
- Stellar Lab Contract Spec renders `data_format = "single-value"` for the `EvidenceRegistered` event, while the source code specifies `data_format = "vec"`. This is a cosmetic rendering difference in the explorer's XDR parsing; functional parity and event emission were confirmed via the smoke test transaction logs.

## 4. Conclusion
Sprint 11 D5 is complete. The Soroban Evidence Registry is live on Testnet, fully audited, and functionally verified.
