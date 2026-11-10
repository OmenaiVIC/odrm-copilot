import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request

from odrm.agents.orchestrator import AgentService
from odrm.agents.providers import build_chat_model
from odrm.agents.tea_client import InProcessTeaClient
from odrm.api.schemas import ChatRequest, ChatResponse
from odrm.auth.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])


def _invalid_messages(request_id: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=422,
        detail={
            "code": "INVALID_ARGUMENTS",
            "field": "messages",
            "message": message,
            "request_id": request_id,
        },
    )


@router.post("/chat", response_model=ChatResponse)
def handle_chat(payload: ChatRequest, request: Request) -> ChatResponse:
    request_id = str(uuid.uuid4())
    settings = request.app.state.settings

    if len(payload.messages) > settings.chat_max_messages:
        raise _invalid_messages(
            request_id,
            f"Conversation history must be at most {settings.chat_max_messages} messages.",
        )

    if payload.messages[-1].role != "user":
        raise _invalid_messages(request_id, "The last message must have role 'user'.")

    for message in payload.messages:
        if len(message.content) > settings.chat_max_message_chars:
            raise _invalid_messages(
                request_id,
                f"Each message must be at most {settings.chat_max_message_chars} characters.",
            )

    total_chars = sum(len(message.content) for message in payload.messages)
    if total_chars > settings.chat_max_history_chars:
        raise _invalid_messages(
            request_id,
            f"Conversation history must be at most {settings.chat_max_history_chars} characters.",
        )

    service = getattr(request.app.state, "agent_service", None)

    if service is None:
        tea_client = InProcessTeaClient(request.app.state.models)
        service = AgentService(
            tea_client=tea_client,
            model_factory=lambda: build_chat_model(settings),
            history_max_messages=settings.chat_history_max_messages,
            history_max_chars=settings.chat_history_max_chars,
        )

    outcome = service.chat(payload.messages, request_id)

    # 4. Map the outcome to HTTP responses
    if outcome.status == "ok":
        return ChatResponse(
            status="ok",
            reply=outcome.reply,
            result=outcome.result,
            request_id=request_id,
        )
        
    elif outcome.status == "needs_input":
        return ChatResponse(
            status="needs_input",
            reply=outcome.reply,
            result=None,
            request_id=request_id,
        )
        
    elif outcome.status == "rejected":
        detail = {
            "code": outcome.error_code,
            "message": outcome.error_message,
            "request_id": request_id,
        }
        # Safely extract fields from GuardrailViolation for the 422 response
        if outcome.guardrail_error:
            err = outcome.guardrail_error
            for attr in ["field", "value", "minimum", "maximum", "missing_fields"]:
                val = getattr(err, attr, None)
                if val is not None:
                    detail[attr] = val
                    
        raise HTTPException(status_code=422, detail=detail)
        
    elif outcome.status == "unavailable":
        raise HTTPException(
            status_code=503,
            detail={
                "code": outcome.error_code,
                "message": outcome.error_message,
                "request_id": request_id,
            },
        )
        
    else:
        raise HTTPException(
            status_code=500,
            detail={
                "code": outcome.error_code or "AGENT_ERROR",
                "message": outcome.error_message or "The screening assistant failed unexpectedly.",
                "request_id": request_id,
            },
        )