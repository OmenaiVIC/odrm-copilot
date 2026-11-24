from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import uuid4

from odrm.api.schemas import TeaRequest, TeaResponse
from odrm.evidence.repository import EvidenceRepository, RecordedEvidence

logger = logging.getLogger(__name__)

LEAF_PREFIX = b"\x00"
NODE_PREFIX = b"\x01"
VOLATILE_FIELDS = frozenset({"report_id", "generated_at", "timestamp"})


class EvidenceNotFoundError(Exception):
    """Raised when no evidence exists for a screening hash."""


class EvidenceNotBatchedError(Exception):
    """Raised when evidence exists but is not attached to a batch."""


class EvidenceLedgerUnavailable(Exception):
    """Raised when the evidence ledger cannot persist a record."""


@dataclass(frozen=True)
class EvidenceProof:
    screening_hash: str
    batch_id: str
    merkle_root: str
    proof_path: list[str]
    leaf_index: int
    leaf_count: int
    verified: bool


def _strip_volatile(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _strip_volatile(item)
            for key, item in value.items()
            if key not in VOLATILE_FIELDS
        }
    if isinstance(value, list):
        return [_strip_volatile(item) for item in value]
    return value


def _canonical_json(payload: Any) -> bytes:
    canonical = json.dumps(
        _strip_volatile(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return canonical.encode("utf-8")


def compute_hashes(
    request: TeaRequest,
    response: TeaResponse,
) -> tuple[str, str, str]:
    input_hash = hashlib.sha256(
        _canonical_json(request.model_dump(mode="json"))
    ).hexdigest()
    output_hash = hashlib.sha256(
        _canonical_json(response.model_dump(mode="json"))
    ).hexdigest()
    screening_hash = hashlib.sha256(
        bytes.fromhex(input_hash) + bytes.fromhex(output_hash)
    ).hexdigest()
    return input_hash, output_hash, screening_hash


def _leaf_node(screening_hash: str) -> bytes:
    return hashlib.sha256(
        LEAF_PREFIX + bytes.fromhex(screening_hash)
    ).digest()


def _parent_node(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(NODE_PREFIX + left + right).digest()


def _next_level(level: list[bytes]) -> list[bytes]:
    parents = [
        _parent_node(level[index], level[index + 1])
        for index in range(0, len(level) - 1, 2)
    ]
    if len(level) % 2:
        parents.append(level[-1])
    return parents


def merkle_root(screening_hashes: Sequence[str]) -> str:
    if not screening_hashes:
        raise ValueError("Cannot build a Merkle root for an empty batch.")
    level = [_leaf_node(value) for value in screening_hashes]
    while len(level) > 1:
        level = _next_level(level)
    return level[0].hex()


def merkle_proof(screening_hashes: Sequence[str], leaf_index: int) -> list[str]:
    if not screening_hashes:
        raise ValueError("Cannot build a Merkle proof for an empty batch.")
    if not 0 <= leaf_index < len(screening_hashes):
        raise ValueError("leaf_index is outside the batch.")
    level = [_leaf_node(value) for value in screening_hashes]
    index = leaf_index
    proof: list[str] = []
    while len(level) > 1:
        if index % 2 == 0:
            if index + 1 < len(level):
                proof.append(level[index + 1].hex())
        else:
            proof.append(level[index - 1].hex())
        level = _next_level(level)
        index //= 2
    return proof


def verify_merkle_proof(
    screening_hash: str,
    proof_path: Sequence[str],
    root_hex: str,
    leaf_index: int,
    leaf_count: int,
) -> bool:
    if leaf_count < 1 or not 0 <= leaf_index < leaf_count:
        return False
    remaining = iter(proof_path)
    try:
        node = _leaf_node(screening_hash)
        index = leaf_index
        width = leaf_count
        while width > 1:
            if index % 2 == 0:
                if index + 1 < width:
                    node = _parent_node(node, bytes.fromhex(next(remaining)))
            else:
                node = _parent_node(bytes.fromhex(next(remaining)), node)
            width = (width + 1) // 2
            index //= 2
    except (StopIteration, ValueError):
        return False
    try:
        next(remaining)
    except StopIteration:
        return node.hex() == root_hex
    return False


class EvidenceService:
    def __init__(self, repository: EvidenceRepository) -> None:
        self._repository = repository

    def record_screening(
        self,
        request: TeaRequest,
        response: TeaResponse,
        *,
        now: datetime | None = None,
    ) -> RecordedEvidence:
        screening_id = str(uuid4())
        try:
            input_hash, output_hash, screening_hash = compute_hashes(
                request,
                response,
            )
            return self._repository.record_screening(
                screening_id=screening_id,
                input_hash=input_hash,
                output_hash=output_hash,
                screening_hash=screening_hash,
                now=now,
            )
        except Exception as exc:
            raise EvidenceLedgerUnavailable("Evidence ledger unavailable.") from exc

    def verify(self, screening_hash: str) -> EvidenceProof:
        record = self._repository.get_by_screening_hash(screening_hash)
        if record is None:
            raise EvidenceNotFoundError(
                "No evidence exists for this screening hash."
            )
        if record.batch is None:
            raise EvidenceNotBatchedError(
                "Evidence exists but has not been batched."
            )

        leaves = self._repository.list_leaves(record.batch.id)
        screening_hashes = [leaf.screening_hash for leaf in leaves]
        try:
            leaf_index = next(
                index
                for index, leaf in enumerate(leaves)
                if leaf.screening_hash == screening_hash
            )
        except StopIteration as exc:
            raise EvidenceNotFoundError(
                "No evidence exists for this screening hash."
            ) from exc

        proof_path = merkle_proof(screening_hashes, leaf_index)
        root = merkle_root(screening_hashes)
        verified = verify_merkle_proof(
            screening_hash,
            proof_path,
            root,
            leaf_index,
            len(screening_hashes),
        )
        if not verified:
            logger.error(
                "Merkle proof verification failed screening_hash=%s batch_id=%s",
                screening_hash,
                record.batch.id,
            )
        return EvidenceProof(
            screening_hash=screening_hash,
            batch_id=record.batch.id,
            merkle_root=root,
            proof_path=proof_path,
            leaf_index=leaf_index,
            leaf_count=len(screening_hashes),
            verified=verified,
        )
