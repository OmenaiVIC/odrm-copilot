import uuid
import logging
from fastapi import APIRouter, HTTPException, Request

from odrm.api.schemas import ChatRequest, ChatResponse
from odrm.agents.orchestrator import AgentService
from odrm.agents.tea_client import HttpTeaClient
from odrm.agents.providers import build_chat_model

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
def handle_chat(payload: ChatRequest, request: Request) -> ChatResponse:
    request_id = str(uuid.uuid4())
    settings = request.app.state.settings
    
    # 1. Enforce message length from settings (Return structured dict for tests)
    if len(payload.message) > settings.chat_max_message_chars:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INVALID_ARGUMENTS",
                "field": "message",
                "message": f"Message must be at most {settings.chat_max_message_chars} characters.",
                "request_id": request_id,
            },
        )
    
    # 2. Get or build the Agent Service
    service = getattr(request.app.state, "agent_service", None)
    
    if service is None:
        tea_client = HttpTeaClient(
            base_url=settings.tea_api_base_url,
            timeout_seconds=settings.tea_timeout_seconds,
            client=None, 
        )
        def model_factory():
            return build_chat_model(settings)
        service = AgentService(tea_client=tea_client, model_factory=model_factory)

    # 3. Run the agent
    outcome = service.chat(payload.message, request_id)

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