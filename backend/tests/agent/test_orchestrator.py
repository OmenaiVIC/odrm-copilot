from __future__ import annotations

from odrm.agents.orchestrator import AgentService
from odrm.agents.providers import AgentConfigurationError
from odrm.agents.tea_client import TeaRejectedError, TeaUnavailableError

from .fakes import (
    FakeTeaClient,
    ScriptedChatModel,
    final_message,
    make_tea_request,
    make_tea_response,
    tool_call_message,
)


def build_service(
    responses: list,
    tea: FakeTeaClient | None = None,
    fail_on_call: int | None = None,
) -> tuple[AgentService, FakeTeaClient]:
    tea_client = tea or FakeTeaClient()
    service = AgentService(
        tea_client=tea_client,
        model_factory=lambda: ScriptedChatModel(
            responses=responses,
            fail_on_call=fail_on_call,
        ),
    )
    return service, tea_client


def test_tool_call_is_used_and_model_reply_is_returned() -> None:
    service, tea = build_service(
        [
            tool_call_message(make_tea_request().model_dump(mode="python")),
            final_message("The screening completed successfully."),
        ]
    )

    outcome = service.chat("run the screening", "req-1")

    assert outcome.status == "ok"
    assert outcome.result == make_tea_response()
    assert outcome.reply == "The screening completed successfully."
    assert len(tea.requests) == 1


def test_second_successful_tool_call_is_ignored_after_first_result() -> None:
    arguments = make_tea_request().model_dump(mode="python")
    service, tea = build_service(
        [
            tool_call_message(arguments, "call-1"),
            tool_call_message(arguments, "call-2"),
            final_message("Done."),
        ]
    )

    outcome = service.chat("run the screening", "req-1")

    assert outcome.status == "ok"
    assert outcome.result == make_tea_response()
    assert len(tea.requests) == 1


def test_no_tool_call_returns_needs_input_with_agent_reply() -> None:
    service, tea = build_service([final_message("Please provide the CH4 feed rate and capex.")])

    outcome = service.chat("run it", "req-1")

    assert outcome.status == "needs_input"
    assert outcome.result is None
    assert outcome.reply == "Please provide the CH4 feed rate and capex."
    assert tea.requests == []


def test_empty_final_message_without_tool_uses_safe_needs_input_fallback() -> None:
    service, _ = build_service([final_message("   ")])

    outcome = service.chat("run it", "req-1")

    assert outcome.status == "needs_input"
    assert outcome.result is None
    assert outcome.reply


def test_guardrail_rejection_maps_to_rejected_without_tea_call() -> None:
    payload = make_tea_request().model_dump(mode="python")
    payload["conditions"]["catalyst"] = "Unobtainium"
    service, tea = build_service(
        [
            tool_call_message(payload),
            final_message("The catalyst is unsupported."),
        ]
    )

    outcome = service.chat("run it", "req-1")

    assert outcome.status == "rejected"
    assert outcome.result is None
    assert outcome.error_code == "UNKNOWN_CATALYST"
    assert tea.requests == []


def test_tea_rejection_maps_to_rejected() -> None:
    tea = FakeTeaClient(error=TeaRejectedError("rejected"))
    service, _ = build_service(
        [
            tool_call_message(make_tea_request().model_dump(mode="python")),
            final_message("The model rejected it."),
        ],
        tea=tea,
    )

    outcome = service.chat("run it", "req-1")

    assert outcome.status == "rejected"
    assert outcome.error_code == "TEA_REJECTED"
    assert outcome.result is None


def test_tea_unavailable_maps_to_unavailable() -> None:
    tea = FakeTeaClient(error=TeaUnavailableError("down"))
    service, _ = build_service(
        [
            tool_call_message(make_tea_request().model_dump(mode="python")),
            final_message("The service is down."),
        ],
        tea=tea,
    )

    outcome = service.chat("run it", "req-1")

    assert outcome.status == "unavailable"
    assert outcome.error_code == "TEA_UNAVAILABLE"
    assert outcome.result is None


def test_provider_configuration_error_maps_to_agent_unavailable() -> None:
    def factory() -> ScriptedChatModel:
        raise AgentConfigurationError("missing key")

    service = AgentService(tea_client=FakeTeaClient(), model_factory=factory)

    outcome = service.chat("run it", "req-1")

    assert outcome.status == "unavailable"
    assert outcome.error_code == "AGENT_UNAVAILABLE"
    assert outcome.result is None


def test_model_failure_after_successful_tool_returns_fallback_reply() -> None:
    service, tea = build_service(
        [tool_call_message(make_tea_request().model_dump(mode="python"))],
        fail_on_call=1,
    )

    outcome = service.chat("run it", "req-1")

    assert outcome.status == "ok"
    assert outcome.result == make_tea_response()
    assert "86.2%" in outcome.reply
    assert len(tea.requests) == 1


def test_unexpected_model_failure_without_result_maps_to_error() -> None:
    service, _ = build_service([], fail_on_call=0)

    outcome = service.chat("run it", "req-1")

    assert outcome.status == "error"
    assert outcome.error_code == "AGENT_ERROR"
    assert outcome.result is None
