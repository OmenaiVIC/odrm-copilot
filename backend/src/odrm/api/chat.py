from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from odrm.agents.orchestrator import AgentOutcome, AgentService
from odrm.api.schemas import ChatErrorDetail, ChatRequest, ChatResponse

router = APIRouter()


def _error_detail(
    code: str,
    message: str,
    request_id: str,
    **extra: Any,
) -> dict[str, Any]:
    detail = ChatErrorDetail(
        code=code,
        message=message,
        request_id=request_id,
        **extra,
    )
    return detail.model_dump(exclude_none=True)


def _rejection_detail(outcome: AgentOutcome, request_id: str) -> dict[str, Any]:
    if outcome.guardrail_error is not None:
        return outcome.guardrail_error.to_detail(request_id)
    return _error_detail(
        outcome.error_code or "TEA_REJECTED",
        outcome.error_message or "The request was rejected.",
        request_id,
    )


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, req: Request) -> ChatResponse:
    request_id = str(uuid.uuid4())
    service: AgentService = req.app.state.agent_service
    outcome = service.chat(request.message, request_id)

    if outcome.status == "ok":
        if outcome.result is None:
            raise HTTPException(
                status_code=500,
                detail=_error_detail(
                    "AGENT_ERROR",
                    "The screening assistant failed unexpectedly.",
                    request_id,
                ),
            )
        return ChatResponse(
            status="ok",
            reply=outcome.reply,
            result=outcome.result,
            request_id=request_id,
        )

    if outcome.status == "needs_input":
        return ChatResponse(
            status="needs_input",
            reply=outcome.reply,
            result=None,
            request_id=request_id,
        )

    if outcome.status == "rejected":
        raise HTTPException(status_code=422, detail=_rejection_detail(outcome, request_id))

    if outcome.status == "unavailable":
        raise HTTPException(
            status_code=503,
            detail=_error_detail(
                outcome.error_code or "AGENT_UNAVAILABLE",
                outcome.error_message or "The screening assistant is unavailable.",
                request_id,
            ),
        )

    raise HTTPException(
        status_code=500,
        detail=_error_detail(
            "AGENT_ERROR",
            "The screening assistant failed unexpectedly.",
            request_id,
        ),
    )
