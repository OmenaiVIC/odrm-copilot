from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class EvidenceVerifyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    screening_hash: str
    batch_id: str
    merkle_root: str
    proof_path: list[str]
    leaf_index: int
    leaf_count: int
    verified: bool
