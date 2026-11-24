from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request

from odrm.auth.dependencies import get_current_user
from odrm.evidence.schemas import EvidenceVerifyResponse
from odrm.evidence.service import (
    EvidenceLedgerUnavailable,
    EvidenceNotBatchedError,
    EvidenceNotFoundError,
    EvidenceService,
)

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get(
    "/evidence/verify/{screening_hash}",
    response_model=EvidenceVerifyResponse,
)
def verify_evidence(
    req: Request,
    screening_hash: Annotated[str, Path(pattern=r"^[0-9a-f]{64}$")],
) -> EvidenceVerifyResponse:
    service: EvidenceService = req.app.state.evidence_service
    try:
        proof = service.verify(screening_hash)
    except EvidenceNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "EVIDENCE_NOT_FOUND",
                "message": "No evidence exists for this screening hash.",
            },
        ) from exc
    except EvidenceNotBatchedError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "EVIDENCE_NOT_BATCHED",
                "message": "Evidence exists but has not been batched.",
            },
        ) from exc
    except EvidenceLedgerUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "EVIDENCE_UNAVAILABLE",
                "message": "Evidence ledger unavailable.",
            },
        ) from exc

    return EvidenceVerifyResponse(
        screening_hash=proof.screening_hash,
        batch_id=proof.batch_id,
        merkle_root=proof.merkle_root,
        proof_path=proof.proof_path,
        leaf_index=proof.leaf_index,
        leaf_count=proof.leaf_count,
        verified=proof.verified,
    )
