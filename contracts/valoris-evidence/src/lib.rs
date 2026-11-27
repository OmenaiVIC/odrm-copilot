#![no_std]

use soroban_sdk::{
    contract, contracterror, contractevent, contractimpl, contracttype, Address, Bytes, BytesN,
    Env, String,
};

#[cfg(test)]
mod test;

/// Domain-separation prefix for leaf nodes, byte-identical to the backend D2
/// `LEAF_PREFIX = b"\x00"` in `backend/src/odrm/evidence/service.py`.
pub const LEAF_PREFIX: [u8; 1] = [0x00];
/// Domain-separation prefix for internal nodes, byte-identical to D2 `NODE_PREFIX = b"\x01"`.
pub const NODE_PREFIX: [u8; 1] = [0x01];

const MAX_DETECTION_ID_LEN: u32 = 64;

const INSTANCE_TTL_THRESHOLD: u32 = 518_400;
const INSTANCE_TTL_EXTEND_TO: u32 = 3_110_400;
const PERSISTENT_TTL_THRESHOLD: u32 = 518_400;
const PERSISTENT_TTL_EXTEND_TO: u32 = 3_110_400;

#[contracttype]
#[derive(Clone)]
pub enum DataKey {
    Admin,
    Evidence(String),
}

#[contracttype]
#[derive(Clone)]
pub struct EvidenceRecord {
    pub commitment: BytesN<32>,
    pub registered_at: u64,
    pub registered_ledger: u32,
}

#[contracterror]
#[derive(Copy, Clone, Debug, Eq, PartialEq)]
#[repr(u32)]
pub enum Error {
    AlreadyRegistered = 1,
    InvalidHashLength = 2,
    InvalidDetectionId = 3,
    NotInitialized = 4,
}

/// leaf(x) = SHA-256(0x00 || x_raw32), matching D2 `_leaf_node`.
pub fn leaf_hash(env: &Env, hash: &BytesN<32>) -> BytesN<32> {
    let mut buf = [0u8; 33];
    buf[0] = LEAF_PREFIX[0];
    buf[1..].copy_from_slice(&hash.to_array());
    env.crypto()
        .sha256(&Bytes::from_slice(env, &buf))
        .to_bytes()
}

/// node(l, r) = SHA-256(0x01 || l || r), matching D2 `_parent_node`.
pub fn node_hash(env: &Env, left: &BytesN<32>, right: &BytesN<32>) -> BytesN<32> {
    let mut buf = [0u8; 65];
    buf[0] = NODE_PREFIX[0];
    buf[1..33].copy_from_slice(&left.to_array());
    buf[33..].copy_from_slice(&right.to_array());
    env.crypto()
        .sha256(&Bytes::from_slice(env, &buf))
        .to_bytes()
}

fn to_hash(env: &Env, value: &Bytes) -> Result<BytesN<32>, Error> {
    if value.len() != 32 {
        return Err(Error::InvalidHashLength);
    }
    let mut buf = [0u8; 32];
    value.copy_into_slice(&mut buf);
    Ok(BytesN::from_array(env, &buf))
}

fn validate_detection_id(detection_id: &String) -> Result<(), Error> {
    let len = detection_id.len();
    if len == 0 || len > MAX_DETECTION_ID_LEN {
        return Err(Error::InvalidDetectionId);
    }
    Ok(())
}

fn read_admin(env: &Env) -> Result<Address, Error> {
    env.storage()
        .instance()
        .get(&DataKey::Admin)
        .ok_or(Error::NotInitialized)
}

#[contractevent(topics = ["evidence", "register"], data_format = "vec")]
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct EvidenceRegistered {
    pub detection_id: String,
    pub commitment: BytesN<32>,
}

#[contract]
pub struct ValorisEvidence;

#[contractimpl]
impl ValorisEvidence {
    /// The host runs this atomically at deploy, so there is no initializer to front-run.
    pub fn __constructor(env: Env, admin: Address) {
        env.storage().instance().set(&DataKey::Admin, &admin);
        env.storage()
            .instance()
            .extend_ttl(INSTANCE_TTL_THRESHOLD, INSTANCE_TTL_EXTEND_TO);
    }

    /// Anchor a 32-byte evidence commitment for `detection_id`. Admin-authorized, append-only.
    pub fn register_evidence(
        env: Env,
        detection_id: String,
        evidence_hash: Bytes,
    ) -> Result<(), Error> {
        let admin = read_admin(&env)?;
        admin.require_auth();

        validate_detection_id(&detection_id)?;
        let hash = to_hash(&env, &evidence_hash)?;

        let key = DataKey::Evidence(detection_id.clone());
        if env.storage().persistent().has(&key) {
            return Err(Error::AlreadyRegistered);
        }

        let commitment = leaf_hash(&env, &hash);
        let record = EvidenceRecord {
            commitment: commitment.clone(),
            registered_at: env.ledger().timestamp(),
            registered_ledger: env.ledger().sequence(),
        };
        env.storage().persistent().set(&key, &record);
        env.storage().persistent().extend_ttl(
            &key,
            PERSISTENT_TTL_THRESHOLD,
            PERSISTENT_TTL_EXTEND_TO,
        );

        EvidenceRegistered {
            detection_id,
            commitment,
        }
        .publish(&env);

        Ok(())
    }

    /// Permissionless verification. Never panics on malformed or unknown input.
    pub fn verify_evidence(env: Env, detection_id: String, expected_hash: Bytes) -> bool {
        let Ok(hash) = to_hash(&env, &expected_hash) else {
            return false;
        };

        let key = DataKey::Evidence(detection_id);
        let stored: Option<EvidenceRecord> = env.storage().persistent().get(&key);
        let Some(record) = stored else {
            return false;
        };

        env.storage().persistent().extend_ttl(
            &key,
            PERSISTENT_TTL_THRESHOLD,
            PERSISTENT_TTL_EXTEND_TO,
        );

        record.commitment == leaf_hash(&env, &hash)
    }

    /// Read-only helper: returns the leaf commitment for a 32-byte hash.
    pub fn leaf_commitment(env: Env, evidence_hash: Bytes) -> Result<BytesN<32>, Error> {
        let hash = to_hash(&env, &evidence_hash)?;
        Ok(leaf_hash(&env, &hash))
    }
}
