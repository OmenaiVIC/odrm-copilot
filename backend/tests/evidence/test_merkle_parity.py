from __future__ import annotations

import hashlib

from odrm.evidence.service import LEAF_PREFIX, NODE_PREFIX, _leaf_node, _parent_node

# Normative golden vectors (docs/SPRINT_11[D5]_PLAN.md §5.3).
# The same constants are hardcoded in contracts/valoris-evidence/src/test.rs.
SCREENING_A = "35274990e3059ec308436bd335d24ccbd92649203875b240d578164904c62b63"
LEAF_A = "28948bcfccb8232bc936029f02625dd2bc36ea9558b3dc0dd8b70a628bc8308d"
SCREENING_B = "e43e7773fc29eb9f127363d27b647ad452dd229ce157abe4237cbc2c0319ca69"
LEAF_B = "8c919ab645efc21f602d716ca7d7fc8e14e8eb8a18a78cbd88617cb084eea992"
NODE_AB = "b0a458676959f25bf64fdbafd2ddeb89b1c903949eb46babeb53408f7d1ad546"


def test_leaf_node_matches_golden_vector_a() -> None:
    assert _leaf_node(SCREENING_A).hex() == LEAF_A


def test_leaf_node_matches_golden_vector_b() -> None:
    assert _leaf_node(SCREENING_B).hex() == LEAF_B


def test_parent_node_matches_golden_vector() -> None:
    assert _parent_node(bytes.fromhex(LEAF_A), bytes.fromhex(LEAF_B)).hex() == NODE_AB


def test_prefixes_are_domain_separated() -> None:
    raw = bytes.fromhex(SCREENING_A)
    leaf = _leaf_node(SCREENING_A)

    assert leaf == hashlib.sha256(LEAF_PREFIX + raw).digest()
    assert leaf != hashlib.sha256(NODE_PREFIX + raw).digest()
    assert LEAF_PREFIX != NODE_PREFIX
