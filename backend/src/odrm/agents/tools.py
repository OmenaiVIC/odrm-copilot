from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langchain_core.tools import BaseTool, StructuredTool

from odrm.agents.guardrails import GuardrailViolation, validate_tea_request
from odrm.agents.tea_client import TeaClient, TeaClientError, TeaRejectedError
from odrm.api.schemas import TeaRequest, TeaResponse

TOOL_NAME = "calculate_project_economics"

_DESCRIPTION = (
    "Calculate ODRM process predictions and project economics. This is the only permitted "
    "way to obtain process predictions or financial results; never calculate, estimate, or "
    "invent those values yourself. Extract every required condition and assumption first. "
    "If any required value or unit is missing or ambiguous, ask the user instead of guessing."
)


@dataclass
class AgentRunRecorder:
    tool_invoked: bool = False
    tool_arguments: TeaRequest | None = None
    result: TeaResponse | None = None
    guardrail_error: GuardrailViolation | None = None
    tea_error: TeaClientError | None = None
    tool_call_count: int = 0


class _GuardedStructuredTool(StructuredTool):
    def _parse_input(
        self,
        tool_input: str | dict[str, Any],
        tool_call_id: str | None,
    ) -> str | dict[str, Any]:
        return tool_input


def _guardrail_payload(error: GuardrailViolation) -> dict[str, Any]:
    return {key: value for key, value in error.to_detail("").items() if key != "request_id"}


def calculate_project_economics(
    tea_client: TeaClient,
    recorder: AgentRunRecorder,
) -> BaseTool:
    """Build the guarded TEA tool; alias kept for the documented tool name."""
    return create_tea_tool(tea_client, recorder)


def create_tea_tool(tea_client: TeaClient, recorder: AgentRunRecorder) -> BaseTool:
    def run(*args: Any, **kwargs: Any) -> dict[str, Any]:
        recorder.tool_invoked = True
        recorder.tool_call_count += 1

        if recorder.result is not None or recorder.tea_error is not None:
            return {
                "status": "error",
                "error": {
                    "code": "DUPLICATE_TOOL_CALL",
                    "message": "Only one TEA calculation is allowed per request.",
                },
            }

        if args:
            recorder.guardrail_error = GuardrailViolation(
                "INVALID_ARGUMENTS",
                "The tool arguments must be an object.",
            )
            return {
                "status": "rejected",
                "error": _guardrail_payload(recorder.guardrail_error),
            }

        try:
            request = validate_tea_request(kwargs)
        except GuardrailViolation as exc:
            recorder.guardrail_error = exc
            return {"status": "rejected", "error": _guardrail_payload(exc)}

        recorder.tool_arguments = request
        try:
            result = tea_client.calculate(request)
        except TeaRejectedError as exc:
            recorder.tea_error = exc
            return {
                "status": "rejected",
                "error": {
                    "code": "TEA_REJECTED",
                    "message": "The TEA service rejected the request.",
                },
            }
        except TeaClientError as exc:
            recorder.tea_error = exc
            return {
                "status": "unavailable",
                "error": {
                    "code": "TEA_UNAVAILABLE",
                    "message": "The TEA service is unavailable.",
                },
            }

        recorder.guardrail_error = None
        recorder.result = result
        return result.model_dump(mode="json")

    return _GuardedStructuredTool(
        name=TOOL_NAME,
        description=_DESCRIPTION,
        func=run,
        args_schema=TeaRequest,
    )
