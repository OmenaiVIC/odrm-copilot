from __future__ import annotations

from typing import Any

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import BaseTool

from odrm.agents.tea_client import TeaClient, TeaClientError
from odrm.api.schemas import TeaRequest, TeaResponse


def make_tea_response() -> TeaResponse:
    return TeaResponse.model_validate(
        {
            "predictions": {
                "ch4_conversion": 0.862,
                "syngas_yield_mol_per_mol_ch4": 2.31,
            },
            "model_versions": {
                "ch4_conversion": "xgb-test-conversion",
                "syngas_yield_mol_per_mol_ch4": "xgb-test-yield",
            },
            "financials": {
                "syngas_kmol_per_day": 1.0,
                "syngas_nm3_per_day": 1.0,
                "syngas_revenue_usd_per_day": 1.0,
                "co2_consumed_tonnes_per_day": 1.0,
                "carbon_credit_value_usd_per_day": 1.0,
                "total_revenue_usd_per_day": 2.0,
                "feed_cost_usd_per_day": 0.5,
                "opex_usd_per_day": 0.25,
                "net_cash_flow_usd_per_day": 1.25,
                "annual_net_cash_flow_usd": 456.25,
                "roi_pct": 0.00009125,
                "payback_years": 10_958.9,
                "currency": "USD",
            },
            "warnings": [],
        }
    )


def make_tea_request() -> TeaRequest:
    return TeaRequest.model_validate(
        {
            "conditions": {
                "temperature_c": 750.0,
                "pressure_bar": 5.0,
                "ch4_o2_ratio": 2.0,
                "co2_ch4_ratio": 0.5,
                "h2o_ch4_ratio": 0.3,
                "ghsv_per_h": 20_000.0,
                "catalyst": "Ni/Al2O3",
                "catalyst_loading_wt_pct": 10.0,
                "n2_dilution_mol_pct": 0.0,
            },
            "assumptions": {
                "ch4_feed_kmol_per_h": 100.0,
                "natural_gas_price_usd_per_mmbtu": 3.25,
                "syngas_price_usd_per_kmol": 4.10,
                "carbon_credit_price_usd_per_tonne_co2e": 28.50,
                "capex_usd": 5_000_000.0,
            },
        }
    )


class FakeTeaClient(TeaClient):
    def __init__(
        self,
        response: TeaResponse | None = None,
        error: TeaClientError | None = None,
    ) -> None:
        self.response = response or make_tea_response()
        self.error = error
        self.requests: list[TeaRequest] = []

    def calculate(self, request: TeaRequest) -> TeaResponse:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return self.response


def tool_call_message(payload: dict[str, Any], call_id: str = "call-1") -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": "calculate_project_economics",
                "args": payload,
                "id": call_id,
                "type": "tool_call",
            }
        ],
    )


def final_message(text: str) -> AIMessage:
    return AIMessage(content=text)


class ScriptedChatModel(BaseChatModel):
    responses: list[AIMessage]
    index: int = 0
    fail_on_call: int | None = None

    @property
    def _llm_type(self) -> str:
        return "scripted-chat-model"

    def bind_tools(
        self, tools: list[dict[str, Any] | type | BaseTool], **kwargs: Any
    ) -> BaseChatModel:
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        if self.fail_on_call is not None and self.index == self.fail_on_call:
            raise RuntimeError("scripted model failure")
        message = self.responses[self.index]
        self.index += 1
        return ChatResult(generations=[ChatGeneration(message=message)])
