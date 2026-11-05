from __future__ import annotations

from typing import Any

from odrm.agents.guardrails import GuardrailViolation
from odrm.agents.tea_client import TeaRejectedError, TeaUnavailableError
from odrm.agents.tools import AgentRunRecorder, create_tea_tool
from odrm.api.schemas import TeaRequest

from .fakes import FakeTeaClient, make_tea_request, make_tea_response


def invalid_payload(**overrides: Any) -> dict[str, Any]:
    payload = make_tea_request().model_dump(mode="python")
    payload["conditions"].update(overrides)
    return payload


def test_tool_exposes_tea_request_schema_and_safety_description() -> None:
    tool = create_tea_tool(FakeTeaClient(), AgentRunRecorder())

    assert tool.name == "calculate_project_economics"
    assert tool.args_schema is TeaRequest
    assert "only permitted way" in tool.description
    assert "never calculate" in tool.description.lower()


def test_valid_call_invokes_tea_once_and_records_everything() -> None:
    tea = FakeTeaClient()
    recorder = AgentRunRecorder()
    tool = create_tea_tool(tea, recorder)

    output = tool.invoke(make_tea_request().model_dump(mode="python"))

    assert output == make_tea_response().model_dump(mode="json")
    assert tea.requests == [make_tea_request()]
    assert recorder.tool_invoked is True
    assert recorder.tool_call_count == 1
    assert recorder.tool_arguments == make_tea_request()
    assert recorder.result == make_tea_response()
    assert recorder.guardrail_error is None
    assert recorder.tea_error is None


def test_guardrail_violation_does_not_call_tea_and_is_recorded() -> None:
    tea = FakeTeaClient()
    recorder = AgentRunRecorder()
    tool = create_tea_tool(tea, recorder)

    output = tool.invoke(invalid_payload(temperature_c=1500.0))

    assert isinstance(output, dict)
    assert output["status"] == "rejected"
    assert output["error"]["code"] == "BOUNDS_VIOLATION"
    assert output["error"]["field"] == "conditions.temperature_c"
    assert tea.requests == []
    assert recorder.tool_invoked is True
    assert recorder.tool_call_count == 1
    assert recorder.tool_arguments is None
    assert recorder.result is None
    assert isinstance(recorder.guardrail_error, GuardrailViolation)
    assert recorder.guardrail_error.code == "BOUNDS_VIOLATION"
    assert recorder.guardrail_error.field == "conditions.temperature_c"


def test_second_tool_call_is_refused_without_another_tea_call() -> None:
    tea = FakeTeaClient()
    recorder = AgentRunRecorder()
    tool = create_tea_tool(tea, recorder)
    arguments = make_tea_request().model_dump(mode="python")

    first = tool.invoke(arguments)
    second = tool.invoke(arguments)

    assert first["predictions"]["ch4_conversion"] == 0.862
    assert second["status"] == "error"
    assert second["error"]["code"] == "DUPLICATE_TOOL_CALL"
    assert len(tea.requests) == 1
    assert recorder.tool_call_count == 2


def test_tea_rejection_is_recorded_and_returned_as_tool_error() -> None:
    tea = FakeTeaClient(error=TeaRejectedError("rejected"))
    recorder = AgentRunRecorder()
    tool = create_tea_tool(tea, recorder)

    output = tool.invoke(make_tea_request().model_dump(mode="python"))

    assert output["status"] == "rejected"
    assert output["error"]["code"] == "TEA_REJECTED"
    assert recorder.tool_arguments == make_tea_request()
    assert recorder.result is None
    assert isinstance(recorder.tea_error, TeaRejectedError)
    assert len(tea.requests) == 1


def test_tea_unavailable_is_recorded_and_returned_as_tool_error() -> None:
    tea = FakeTeaClient(error=TeaUnavailableError("down"))
    recorder = AgentRunRecorder()
    tool = create_tea_tool(tea, recorder)

    output = tool.invoke(make_tea_request().model_dump(mode="python"))

    assert output["status"] == "unavailable"
    assert output["error"]["code"] == "TEA_UNAVAILABLE"
    assert recorder.tool_arguments == make_tea_request()
    assert recorder.result is None
    assert isinstance(recorder.tea_error, TeaUnavailableError)
    assert len(tea.requests) == 1
