#![cfg(test)]

use crate::{
    leaf_hash, node_hash, Error, ValorisEvidence, ValorisEvidenceClient, LEAF_PREFIX, NODE_PREFIX,
};
use soroban_sdk::{testutils::Address as _, Address, Bytes, BytesN, Env, String as SorobanString};

// ---------------------------------------------------------------------------
// Normative golden vectors (docs/SPRINT_11[D5]_PLAN.md §5.3).
// These same constants are hardcoded in backend/tests/evidence/test_merkle_parity.py.
// Two independent copies must agree; drift in either implementation fails a test.
// ---------------------------------------------------------------------------
const SCREENING_A: &str = "35274990e3059ec308436bd335d24ccbd92649203875b240d578164904c62b63";
const LEAF_A: &str = "28948bcfccb8232bc936029f02625dd2bc36ea9558b3dc0dd8b70a628bc8308d";
const SCREENING_B: &str = "e43e7773fc29eb9f127363d27b647ad452dd229ce157abe4237cbc2c0319ca69";
const LEAF_B: &str = "8c919ab645efc21f602d716ca7d7fc8e14e8eb8a18a78cbd88617cb084eea992";
const NODE_AB: &str = "b0a458676959f25bf64fdbafd2ddeb89b1c903949eb46babeb53408f7d1ad546";

fn hex32(hex: &str) -> [u8; 32] {
    let bytes = hex.as_bytes();
    assert_eq!(bytes.len(), 64, "golden vectors must be 32 raw bytes");
    let mut out = [0u8; 32];
    for (index, pair) in bytes.chunks_exact(2).enumerate() {
        let high = (pair[0] as char).to_digit(16).expect("valid hex");
        let low = (pair[1] as char).to_digit(16).expect("valid hex");
        out[index] = ((high << 4) | low) as u8;
    }
    out
}

fn hash32(env: &Env, hex: &str) -> BytesN<32> {
    BytesN::from_array(env, &hex32(hex))
}

fn abi_hash(env: &Env, hex: &str) -> Bytes {
    Bytes::from_array(env, &hex32(hex))
}

fn id(env: &Env, value: &str) -> SorobanString {
    SorobanString::from_str(env, value)
}

fn setup(env: &Env) -> (ValorisEvidenceClient<'_>, Address) {
    env.mock_all_auths();
    let admin = Address::generate(env);
    let contract_id = env.register(ValorisEvidence, (admin.clone(),));
    (ValorisEvidenceClient::new(env, &contract_id), admin)
}

#[test]
fn leaf_matches_backend_vector_a() {
    let env = Env::default();
    let (client, _admin) = setup(&env);

    let commitment = client.leaf_commitment(&abi_hash(&env, SCREENING_A));
    assert_eq!(commitment, hash32(&env, LEAF_A));
}

#[test]
fn leaf_matches_backend_vector_b() {
    let env = Env::default();
    let (client, _admin) = setup(&env);

    let commitment = client.leaf_commitment(&abi_hash(&env, SCREENING_B));
    assert_eq!(commitment, hash32(&env, LEAF_B));
}

#[test]
fn node_matches_backend_vector() {
    let env = Env::default();

    let node = node_hash(&env, &hash32(&env, LEAF_A), &hash32(&env, LEAF_B));
    assert_eq!(node, hash32(&env, NODE_AB));
}

#[test]
fn prefixes_are_domain_separated() {
    let env = Env::default();
    let value = hash32(&env, SCREENING_A);

    let leaf = leaf_hash(&env, &value);

    // Same payload, wrong domain prefix: SHA-256(0x01 || x) must differ.
    let mut node_prefixed = [0u8; 33];
    node_prefixed[0] = NODE_PREFIX[0];
    node_prefixed[1..].copy_from_slice(&value.to_array());
    let wrong_domain = env
        .crypto()
        .sha256(&Bytes::from_slice(&env, &node_prefixed))
        .to_bytes();

    assert_ne!(LEAF_PREFIX, NODE_PREFIX);
    assert_ne!(leaf, wrong_domain);
    assert_ne!(leaf, node_hash(&env, &value, &value));
}

#[test]
fn register_then_verify_true() {
    let env = Env::default();
    let (client, admin) = setup(&env);
    let detection_id = id(&env, "det-golden-a");

    client.register_evidence(&detection_id, &abi_hash(&env, SCREENING_A));

    let auths = env.auths();
    assert_eq!(auths.len(), 1);
    for (recorded_admin, _invocation) in auths.iter() {
        assert_eq!(recorded_admin, &admin);
    }

    assert!(client.verify_evidence(&detection_id, &abi_hash(&env, SCREENING_A)));
}

#[test]
fn verify_unknown_id_false() {
    let env = Env::default();
    let (client, _admin) = setup(&env);

    assert!(!client.verify_evidence(&id(&env, "det-missing"), &abi_hash(&env, SCREENING_A)));
}

#[test]
fn verify_wrong_hash_false() {
    let env = Env::default();
    let (client, _admin) = setup(&env);
    let detection_id = id(&env, "det-golden-a");

    client.register_evidence(&detection_id, &abi_hash(&env, SCREENING_A));

    assert!(!client.verify_evidence(&detection_id, &abi_hash(&env, SCREENING_B)));
}

#[test]
fn duplicate_registration_rejected() {
    let env = Env::default();
    let (client, _admin) = setup(&env);
    let detection_id = id(&env, "det-golden-a");

    client.register_evidence(&detection_id, &abi_hash(&env, SCREENING_A));

    let duplicate = client.try_register_evidence(&detection_id, &abi_hash(&env, SCREENING_B));
    assert_eq!(duplicate, Err(Ok(Error::AlreadyRegistered)));

    // The stored commitment is unchanged: append-only, no overwrite path.
    assert!(client.verify_evidence(&detection_id, &abi_hash(&env, SCREENING_A)));
    assert!(!client.verify_evidence(&detection_id, &abi_hash(&env, SCREENING_B)));
}

#[test]
#[should_panic]
fn register_requires_admin_auth() {
    let env = Env::default();
    let admin = Address::generate(&env);
    let contract_id = env.register(ValorisEvidence, (admin,));
    let client = ValorisEvidenceClient::new(&env, &contract_id);

    // No mock_all_auths: require_auth() must trap before any write.
    client.register_evidence(&id(&env, "det-no-auth"), &abi_hash(&env, SCREENING_A));
}

#[test]
fn invalid_hash_length_rejected() {
    let env = Env::default();
    let (client, _admin) = setup(&env);
    let detection_id = id(&env, "det-bad-hash");
    let short = Bytes::from_array(&env, &[0u8; 31]);
    let long = Bytes::from_array(&env, &[0u8; 33]);

    assert_eq!(
        client.try_register_evidence(&detection_id, &short),
        Err(Ok(Error::InvalidHashLength))
    );
    assert_eq!(
        client.try_register_evidence(&detection_id, &long),
        Err(Ok(Error::InvalidHashLength))
    );

    // The read path never panics on malformed input.
    assert!(!client.verify_evidence(&detection_id, &short));
    assert!(!client.verify_evidence(&detection_id, &long));

    assert_eq!(
        client.try_leaf_commitment(&short),
        Err(Ok(Error::InvalidHashLength))
    );
}

#[test]
fn invalid_detection_id_rejected() {
    let env = Env::default();
    let (client, _admin) = setup(&env);
    let empty = id(&env, "");
    let too_long = id(
        &env,
        concat!(
            "aaaaaaaaaa",
            "aaaaaaaaaa",
            "aaaaaaaaaa",
            "aaaaaaaaaa",
            "aaaaaaaaaa",
            "aaaaaaaaaa",
            "aaaaa"
        ),
    );

    assert_eq!(
        client.try_register_evidence(&empty, &abi_hash(&env, SCREENING_A)),
        Err(Ok(Error::InvalidDetectionId))
    );
    assert_eq!(
        client.try_register_evidence(&too_long, &abi_hash(&env, SCREENING_A)),
        Err(Ok(Error::InvalidDetectionId))
    );
}

#[test]
fn verify_is_permissionless() {
    let env = Env::default();
    let (client, _admin) = setup(&env);
    let detection_id = id(&env, "det-public");

    client.register_evidence(&detection_id, &abi_hash(&env, SCREENING_A));

    // Drop every mocked authorization: verify_evidence must not require auth.
    env.mock_auths(&[]);
    assert!(client.verify_evidence(&detection_id, &abi_hash(&env, SCREENING_A)));
}
