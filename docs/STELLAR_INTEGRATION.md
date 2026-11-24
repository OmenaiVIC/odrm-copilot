# ODRM-Copilot - Stellar Integration Design

| | |
|---|---|
| Status | Design complete (D2); implementation deferred to D5 |
| Date | 2026-11-24 |
| Scope | Off-chain Merkle evidence contract, minimal Soroban registry, SAC-first asset model, migration path |
| Depends on | D2 `screening_evidence` / `evidence_batches` schema and hashing convention |
| Not in scope | Contract deployment, anchor job, asset issuance, mainnet operations |

This document is the byte-exact contract between the D2 off-chain evidence chain and the
D5 on-chain Evidence Registry. D2 makes no Stellar calls. D5 must implement this document
without redefining the Merkle convention.

---

## 1. Design principles

1. **Off-chain evidence, on-chain commitment.** Screening inputs and outputs never leave
   the platform database. Only a 32-byte Merkle root per batch is written on chain.
2. **Minimal registry.** The Soroban contract stores roots and verifies proofs. It does
   not hold balances, move value, or contain token logic.
3. **SAC-first compliance.** Carbon credits are classic Stellar assets. The native
   Stellar Asset Contract provides issuance, transfer, freeze, clawback, and
   authorization. No custom token contract.
4. **Deterministic bytes.** Hashing and tree construction are fixed here so an
   independent verifier, the Excel workbook, and the Soroban contract agree.
5. **Fail-open writes, fail-closed verification.** A failed evidence write must not lose
   a screening result. An unverifiable hash must never be reported as verified.
6. **Testnet before mainnet.** Audit readiness is demonstrated on Testnet before any
   production anchoring.

---

## 2. Off-chain evidence chain (D2)

### 2.1 Records

`screening_evidence` stores one row per successful screening:

| Column | Meaning |
|---|---|
| `id` | Row identity; proof lookup uses this, never the hash |
| `screening_id` | Service-minted UUID for the screening attempt |
| `input_hash` | SHA-256 of canonical request JSON, 64 lowercase hex |
| `output_hash` | SHA-256 of canonical response JSON, 64 lowercase hex |
| `screening_hash` | `SHA-256(raw_input_hash_bytes || raw_output_hash_bytes)` |
| `batch_id` | Owning `evidence_batches` row, `NOT NULL` |
| `created_at` | UTC timestamp; part of canonical leaf order |

`evidence_batches` stores the commitment:

| Column | Meaning |
|---|---|
| `id` | Batch UUID |
| `merkle_root` | Root over the batch leaves, 64 lowercase hex |
| `leaf_count` | Number of leaves, `>= 1` |
| `created_at` | UTC timestamp |
| `anchor_status` | `pending`, `anchored_on_soroban`, or `verified` |

D2 writes only `pending`. D5 owns every transition out of `pending`.

### 2.2 Canonical hashing

- Canonical JSON: `json.dumps(value, sort_keys=True, separators=(",", ":"),
  ensure_ascii=True).encode("utf-8")`.
- Volatile keys are removed recursively before serialization: `report_id`,
  `generated_at`, `timestamp`. An identical screening therefore hashes identically
  through `/api/v1/tea` and `/api/v1/report`.
- `input_hash` and `output_hash` are lowercase hex SHA-256 digests.
- `screening_hash` is SHA-256 over the raw 32-byte concatenation
  `bytes.fromhex(input_hash) + bytes.fromhex(output_hash)`, not over the hex text.

### 2.3 Merkle convention

The convention is part of the public contract and must be reproduced by D5.

- Hash function: SHA-256.
- Domain separation: leaf nodes are prefixed with `0x00`, internal nodes with `0x01`.
- Leaf: `SHA-256(0x00 || screening_hash_bytes)`.
- Parent: `SHA-256(0x01 || left_child || right_child)`.
- Odd node promotion: when a level has an odd number of nodes, the final node is
  promoted unchanged to the next level.
- A single-leaf batch has `merkle_root = leaf_node`.
- Leaf order is ascending `(created_at, id)` within the batch.
- Duplicate screening hashes are legal; leaves are distinct by row identity.
- An empty batch is invalid. `leaf_count >= 1` is enforced in the database.

The root is recomputed from all ordered leaves on every append. With a 100-leaf cap this
is at most 100 SHA-256 operations per write and avoids incremental-tree drift.

### 2.4 Batching and rollover

A new batch opens when no batch exists, when the open batch reaches 100 leaves, or on the
first leaf of a new UTC day. The open batch is selected by
`ORDER BY created_at DESC, id DESC LIMIT 1`. PostgreSQL adds `pg_advisory_xact_lock` and
`FOR UPDATE`; SQLite skips locking because the app is single-writer there. The same
transaction inserts the leaf, re-reads ordered leaves, recomputes the root and count, and
commits.

Rollover uses `now.date() > latest.created_at.astimezone(UTC).date()`. A backwards clock
never reopens a closed day; a forwards jump rolls over once.

### 2.5 Verification

`GET /api/v1/evidence/verify/{screening_hash}` returns `screening_hash`, `batch_id`,
`merkle_root`, `proof_path`, `leaf_index`, `leaf_count`, and `verified`. The server loads
the owning batch, locates the leaf by row identity, rebuilds the sibling path bottom-up,
recomputes the root, and checks that the proof folds to that root. Unknown hashes return
404 `EVIDENCE_NOT_FOUND`; unbatched rows return 409 `EVIDENCE_NOT_BATCHED`. Verification
is fail-closed.

`leaf_index` and `leaf_count` are required for independent proof verification: a flat
sibling list cannot be folded without the leaf position and the level widths.

---

## 3. On-chain Evidence Registry (D5)

### 3.1 Contract interface

Planned location: `contracts/valoris-evidence/` (Rust, Soroban).

```rust
fn store_root(
    env: Env,
    batch_id: Symbol,
    merkle_root: BytesN<32>,
) -> Result<(), Error>;

fn verify_hash(
    env: Env,
    batch_id: Symbol,
    leaf_hash: BytesN<32>,
    proof: Vec<BytesN<32>>,
) -> Result<bool, Error>;
```

`leaf_hash` is the 32-byte `screening_hash`, not the prefixed leaf node.

### 3.2 Data model

```rust
batch_roots: Map<Symbol, BytesN<32>>
```

No balances, no transfers, no allowances, no custom token state. A batch root is written
once and is immutable. `verify_hash` is a view-style computation over the stored root.

### 3.3 Proof direction

The two-function interface above does not carry `leaf_index` or `leaf_count`, so a proof
vector alone does not encode whether each sibling is left or right, nor how many
promotions occurred. D5 must resolve this before deployment. Acceptable options:

1. **Add position arguments (recommended).** Extend `verify_hash` with
   `leaf_index: u32` and `leaf_count: u32`. This mirrors the D2 API response and keeps
   the proof vector unencoded.
2. **Encode direction in the proof.** Each entry carries a direction bit, or a separate
   direction bitmap is passed. This keeps the argument count but complicates independent
   verifiers.
3. **Store per-batch metadata.** Store leaf count on chain and still pass direction or
   index. Leaf count alone is not sufficient.

D2 returns `leaf_index` and `leaf_count` precisely so option 1 is available. The chosen
encoding must be documented here before D5 implementation and must not change the D2
hash/tree convention.

### 3.4 Batch identifier mapping

D2 batch IDs are UUID strings. Soroban `Symbol` is restricted to a short alphanumeric
character set and does not accept hyphens. D5 must pick one mapping and document it:

- a Symbol-safe encoding of the UUID (for example, hyphens removed), or
- a change to `BytesN<16>` or `String` in the contract interface.

Collisions and reversibility must be addressed. The off-chain `batch_id` remains the
system of record; the chain key is a derived identifier.

### 3.5 Anchor job

The D5 anchor job runs outside the request path:

1. Select `evidence_batches` where `anchor_status = 'pending'`, oldest first.
2. Call `store_root(batch_id, merkle_root)` from the authorized relayer account.
3. On success, set `anchor_status = 'anchored_on_soroban'` and persist the transaction
   hash. Do not clear the root.
4. A separate verification pass reads the stored root and, when it matches, sets
   `anchor_status = 'verified'`.
5. On failure, leave the batch `pending`, retry with exponential backoff, and alert after
   the retry budget. Anchoring is idempotent: re-submitting the same root for the same
   batch must succeed without changing state or creating a second commitment.

The job must never mark a batch anchored before the transaction is confirmed.

### 3.6 Authorization and key management

`store_root` is restricted to a dedicated relayer account. The relayer key is held in a
secret manager, not in the repository or application image. The issuer account for the
SAC is separate from the relayer. Key rotation requires a contract authorization update
and is treated as an operational event with an audit record.

---

## 4. SAC integration

Carbon credits are issued as a classic Stellar asset (`G...` issuer, asset code, trust
lines). The native Stellar Asset Contract exposes the same asset on Soroban.

- **Issuance:** credits are minted through the SAC `mint` path only after the underlying
  screening evidence is verified. The registry is the technical gate; the issuance
  policy is the business gate.
- **Transfer:** standard SAC transfers. No custom transfer restrictions in application
  code.
- **Compliance controls:** issuer-controlled freeze, clawback, and authorization handle
  sanctions, reversals, and regulated transfers. These are native asset controls, not
  registry logic.
- **No custom token logic:** the registry never mints, burns, transfers, or holds
  credits. A registry bug cannot move funds.
- **Audit surface:** the SAC is protocol-audited. The SCF Audit Bank reviews the small
  registry contract, not the asset contract.

---

## 5. Migration path

| Stage | Evidence state | Chain state | Reversibility |
|---|---|---|---|
| D2 (current) | Off-chain Merkle batches, `pending` | None | Local tables only |
| D5 Testnet | Anchored batches | Testnet registry stores roots | Re-anchor on a fresh Testnet deployment |
| SCF audit | Frozen contract candidate | Testnet roots and verification traces | Contract upgrade or redeploy before mainnet |
| Mainnet (post-SCF) | Production batches anchored | Mainnet registry | Append-only; no root deletion |

Mainnet deployment is deliberately outside D2 and follows a successful audit. Testnet
anchoring is a rehearsal, not a production commitment.

---

## 6. Security and audit readiness

- The registry is deliberately small: one map, two entry points, no external calls, no
  reentrancy surface, no value custody.
- `store_root` rejects a second, different root for an existing batch. Replaying the same
  root is a no-op success.
- `verify_hash` bounds proof length, validates hash sizes, and rejects malformed input
  without panicking.
- The contract emits an event for every accepted root so off-chain reconciliation does
  not depend on RPC log scraping alone.
- Off-chain, evidence writes are fail-open and logged; verification reads are fail-closed.
- Audit Bank scope: registry contract, anchor job, key management, and the D2-to-D5 byte
  contract. The SAC is out of scope because it is protocol-maintained.

---

## 7. Open D5 decisions

These are recorded rather than silently deferred:

1. Proof direction encoding (section 3.3). Recommended: add `leaf_index` and
   `leaf_count` to `verify_hash`.
2. Batch identifier type and UUID mapping (section 3.4).
3. Whether the contract is upgradeable or immutable with redeploy-and-reanchor.
4. Event schema and indexer/RPC provider for reconciliation.
5. Testnet contract ID, relayer account, and deployment runbook.
6. Mainnet timing and whether the first production batches are anchored before or after
   the first external audit cycle.

Any change to the hashing or tree convention is a breaking change and requires a new
version of this document before D5 code is written.
