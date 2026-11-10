from __future__ import annotations

import logging

import pytest
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from odrm.agents.orchestrator import AgentService
from odrm.agents.providers import AgentConfigurationError
from odrm.agents.tea_client import TeaRejectedError, TeaUnavailableError
from odrm.api.schemas import ChatMessage

from .fakes import (
    FakeTeaClient,
    ScriptedChatModel,
    final_message,
    make_tea_request,
    make_tea_response,
    tool_call_message,
)


def user(content: str) -> ChatMessage:
    return ChatMessage(role="user", content=content)


def assistant(content: str) -> ChatMessage:
    return ChatMessage(role="assistant", content=content)


def build_service(
    responses: list,
    tea: FakeTeaClient | None = None,
    fail_on_call: int | None = None,
    history_max_messages: int = 10,
    history_max_chars: int = 16_000,
) -> tuple[AgentService, FakeTeaClient]:
    tea_client = tea or FakeTeaClient()
    service = AgentService(
        tea_client=tea_client,
        model_factory=lambda: ScriptedChatModel(
            responses=responses,
            fail_on_call=fail_on_call,
        ),
        history_max_messages=history_max_messages,
        history_max_chars=history_max_chars,
    )
    return service, tea_client


def conversation_messages(messages: list[BaseMessage]) -> list[BaseMessage]:
    return [message for message in messages if isinstance(message, (HumanMessage, AIMessage))]


def test_tool_call_is_used_and_model_reply_is_returned() -> None:
    service, tea = build_service(
        [
            tool_call_message(make_tea_request().model_dump(mode="python")),
            final_message("The screening completed successfully."),
        ]
    )

    outcome = service.chat([user("run the screening")], "req-1")

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

    outcome = service.chat([user("run the screening")], "req-1")

    assert outcome.status == "ok"
    assert outcome.result == make_tea_response()
    assert len(tea.requests) == 1


def test_no_tool_call_returns_needs_input_with_agent_reply() -> None:
    service, tea = build_service([final_message("Please provide the CH4 feed rate and capex.")])

    outcome = service.chat([user("run it")], "req-1")

    assert outcome.status == "needs_input"
    assert outcome.result is None
    assert outcome.reply == "Please provide the CH4 feed rate and capex."
    assert tea.requests == []


def test_empty_final_message_without_tool_uses_safe_needs_input_fallback() -> None:
    service, _ = build_service([final_message("   ")])

    outcome = service.chat([user("run it")], "req-1")

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

    outcome = service.chat([user("run it")], "req-1")

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

    outcome = service.chat([user("run it")], "req-1")

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

    outcome = service.chat([user("run it")], "req-1")

    assert outcome.status == "unavailable"
    assert outcome.error_code == "TEA_UNAVAILABLE"
    assert outcome.result is None


def test_provider_configuration_error_maps_to_agent_unavailable() -> None:
    def factory() -> ScriptedChatModel:
        raise AgentConfigurationError("missing key")

    service = AgentService(tea_client=FakeTeaClient(), model_factory=factory)

    outcome = service.chat([user("run it")], "req-1")

    assert outcome.status == "unavailable"
    assert outcome.error_code == "AGENT_UNAVAILABLE"
    assert outcome.result is None


def test_model_failure_after_successful_tool_returns_fallback_reply() -> None:
    service, tea = build_service(
        [tool_call_message(make_tea_request().model_dump(mode="python"))],
        fail_on_call=1,
    )

    outcome = service.chat([user("run it")], "req-1")

    assert outcome.status == "ok"
    assert outcome.result == make_tea_response()
    assert "86.2%" in outcome.reply
    assert len(tea.requests) == 1


def test_unexpected_model_failure_without_result_maps_to_error() -> None:
    service, _ = build_service([], fail_on_call=0)

    outcome = service.chat([user("run it")], "req-1")

    assert outcome.status == "error"
    assert outcome.error_code == "AGENT_ERROR"
    assert outcome.result is None

def test_dependent_follow_up_receives_the_full_conversation() -> None:
    first_request = make_tea_request().model_dump(mode="python")
    second_request = make_tea_request().model_dump(mode="python")
    second_request["conditions"]["temperature_c"] = 800.0
    tea = FakeTeaClient()
    model = ScriptedChatModel(
        responses=[
            tool_call_message(first_request, "call-1"),
            final_message("First result."),
            tool_call_message(second_request, "call-2"),
            final_message("Second result."),
        ]
    )
    service = AgentService(tea_client=tea, model_factory=lambda: model)

    first = service.chat([user("Run the screening at 750 C.")], "req-1")
    second = service.chat(
        [
            user("Run the screening at 750 C."),
            assistant("First result."),
            user("Now raise the temperature to 800 C and rerun."),
        ],
        "req-2",
    )

    assert first.status == "ok"
    assert second.status == "ok"
    assert len(tea.requests) == 2
    second_turn_seen = conversation_messages(model.seen_messages[2])
    assert [message.content for message in second_turn_seen] == [
        "Run the screening at 750 C.",
        "First result.",
        "Now raise the temperature to 800 C and rerun.",
    ]


def test_follow_up_that_only_restates_a_prior_result_needs_no_tool_call() -> None:
    tea = FakeTeaClient()
    model = ScriptedChatModel(
        responses=[
            tool_call_message(make_tea_request().model_dump(mode="python")),
            final_message("First result."),
            final_message("The prior payback was 10,958.9 years."),
        ]
    )
    service = AgentService(tea_client=tea, model_factory=lambda: model)

    service.chat([user("Run the screening.")], "req-1")
    outcome = service.chat(
        [
            user("Run the screening."),
            assistant("The prior payback was 10,958.9 years."),
            user("What was the payback?"),
        ],
        "req-2",
    )

    assert outcome.status == "needs_input"
    assert outcome.result is None
    assert len(tea.requests) == 1


def test_history_is_trimmed_to_the_configured_message_window() -> None:
    model = ScriptedChatModel(responses=[final_message("Unused.")])
    service = AgentService(
        tea_client=FakeTeaClient(),
        model_factory=lambda: model,
        history_max_messages=2,
    )

    outcome = service.chat(
        [
            user("first question"),
            assistant("first answer"),
            user("second question"),
        ],
        "req-1",
    )

    assert outcome.status == "needs_input"
    assert [message.content for message in conversation_messages(model.seen_messages[0])] == [
        "second question"
    ]

def test_history_logging_records_counts_only(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="odrm.agents.orchestrator")
    model = ScriptedChatModel(responses=[final_message("Unused.")])
    service = AgentService(
        tea_client=FakeTeaClient(),
        model_factory=lambda: model,
        history_max_messages=2,
    )

    service.chat(
        [
            user("sensitive first question"),
            assistant("sensitive first answer"),
            user("sensitive second question"),
        ],
        "req-1",
    )

    assert "history_received=3 history_sent=1 history_dropped=2" in caplog.text
    assert "sensitive" not in caplog.text