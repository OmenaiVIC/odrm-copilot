from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage

from odrm.agents.guardrails import GuardrailViolation
from odrm.agents.prompts import SYSTEM_PROMPT
from odrm.agents.providers import AgentConfigurationError
from odrm.agents.tea_client import TeaClient, TeaRejectedError
from odrm.agents.tools import AgentRunRecorder, create_tea_tool
from odrm.api.schemas import TeaResponse

logger = logging.getLogger(__name__)

AgentStatus = Literal["ok", "needs_input", "rejected", "unavailable", "error"]

_NEEDS_INPUT_FALLBACK = (
    "I need more information before I can run the screening. Please provide the "
    "conditions, catalyst, feed rate, prices, and capex, with units."
)


@dataclass(frozen=True)
class AgentOutcome:
    status: AgentStatus
    reply: str = ""
    result: TeaResponse | None = None
    error_code: str | None = None
    error_message: str | None = None
    guardrail_error: GuardrailViolation | None = None


def _ok(result: TeaResponse, reply: str) -> AgentOutcome:
    return AgentOutcome(
        status="ok",
        reply=reply,
        result=result,
    )


def _rejected(
    code: str,
    message: str,
    guardrail_error: GuardrailViolation | None = None,
) -> AgentOutcome:
    return AgentOutcome(
        status="rejected",
        error_code=code,
        error_message=message,
        guardrail_error=guardrail_error,
    )


def _unavailable(code: str, message: str) -> AgentOutcome:
    return AgentOutcome(status="unavailable", error_code=code, error_message=message)


def _error() -> AgentOutcome:
    return AgentOutcome(
        status="error",
        error_code="AGENT_ERROR",
        error_message="The screening assistant failed unexpectedly.",
    )


def _format_money(value: float) -> str:
    return f"${value:,.0f}"


def fallback_reply(result: TeaResponse) -> str:
    conversion = result.predictions["ch4_conversion"] * 100.0
    syngas_yield = result.predictions["syngas_yield_mol_per_mol_ch4"]
    financials = result.financials
    payback = financials.payback_years
    payback_text = f"{payback:.2f} years" if payback is not None else "not reached"
    return (
        f"Screening completed. CH4 conversion is {conversion:.1f}%, syngas yield is "
        f"{syngas_yield:.2f} mol/mol CH4, annual net cash flow is "
        f"{_format_money(financials.annual_net_cash_flow_usd)}, ROI is "
        f"{financials.roi_pct:.1f}%, and payback is {payback_text}. This is a screening "
        "result, not investment advice."
    )


def _final_reply(state: object) -> str:
    if not isinstance(state, dict):
        return ""
    messages = state.get("messages")
    if not isinstance(messages, list) or not messages:
        return ""
    final = messages[-1]
    if not isinstance(final, AIMessage):
        return ""
    text = final.text
    return text.strip() if isinstance(text, str) else ""


class AgentService:
    def __init__(
        self,
        tea_client: TeaClient,
        model_factory: Callable[[], BaseChatModel],
    ) -> None:
        self._tea_client = tea_client
        self._model_factory = model_factory

    def chat(self, message: str, request_id: str) -> AgentOutcome:
        recorder = AgentRunRecorder()
        tool = create_tea_tool(self._tea_client, recorder)

        try:
            model = self._model_factory()
        except AgentConfigurationError as exc:
            logger.warning(
                "agent configuration unavailable request_id=%s error=%s",
                request_id,
                type(exc).__name__,
            )
            return _unavailable("AGENT_UNAVAILABLE", "The screening assistant is not configured.")

        try:
            agent = create_agent(
                model=model,
                tools=[tool],
                system_prompt=SYSTEM_PROMPT,
            )
            state = agent.invoke(
                {"messages": [{"role": "user", "content": message}]},
                config={"recursion_limit": 6},
            )
        except Exception as exc:
            logger.warning(
                "agent invocation failed request_id=%s error=%s",
                request_id,
                type(exc).__name__,
            )
            return self._failure_outcome(recorder)

        reply = _final_reply(state)
        if recorder.result is not None:
            return _ok(recorder.result, reply or fallback_reply(recorder.result))
        if recorder.guardrail_error is not None:
            error = recorder.guardrail_error
            return _rejected(error.code, error.message, error)
        if recorder.tea_error is not None:
            if isinstance(recorder.tea_error, TeaRejectedError):
                return _rejected("TEA_REJECTED", "The TEA service rejected the request.")
            return _unavailable("TEA_UNAVAILABLE", "The TEA service is unavailable.")
        if recorder.tool_invoked and recorder.result is None and recorder.guardrail_error is None:
            return _unavailable("TEA_UNAVAILABLE", "The TEA service is unavailable.")
        return AgentOutcome(
            status="needs_input",
            reply=reply or _NEEDS_INPUT_FALLBACK,
        )

    def _failure_outcome(self, recorder: AgentRunRecorder) -> AgentOutcome:
        if recorder.result is not None:
            return _ok(recorder.result, fallback_reply(recorder.result))
        if recorder.guardrail_error is not None:
            error = recorder.guardrail_error
            return _rejected(error.code, error.message, error)
        if recorder.tea_error is not None:
            if isinstance(recorder.tea_error, TeaRejectedError):
                return _rejected("TEA_REJECTED", "The TEA service rejected the request.")
            return _unavailable("TEA_UNAVAILABLE", "The TEA service is unavailable.")
        return _error()
