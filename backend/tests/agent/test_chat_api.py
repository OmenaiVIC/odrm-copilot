from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from odrm.agents.orchestrator import AgentOutcome, AgentService
from odrm.agents.tea_client import TeaRejectedError, TeaUnavailableError
from odrm.api.schemas import ChatRequest, ChatResponse
from odrm.core.config import Settings
from odrm.main import create_app

from .fakes import (
    FakeTeaClient,
    ScriptedChatModel,
    final_message,
    make_tea_request,
    make_tea_response,
    tool_call_message,
)


def service_with(
    responses: list[Any],
    tea: FakeTeaClient | None = None,
    fail_on_call: int | None = None,
) -> tuple[AgentService, FakeTeaClient]:
    tea_client = tea or FakeTeaClient()
    return (
        AgentService(
            tea_client=tea_client,
            model_factory=lambda: ScriptedChatModel(
                responses=responses,
                fail_on_call=fail_on_call,
            ),
        ),
        tea_client,
    )


def client_for(service: AgentService, settings: Settings) -> TestClient:
    return TestClient(create_app(settings, agent_service=service))


def test_ok_response_returns_authoritative_result_and_request_id(
    test_settings: Settings,
) -> None:
    service, tea = service_with(
        [
            tool_call_message(make_tea_request().model_dump(mode="python")),
            final_message("The screening completed."),
        ]
    )

    with client_for(service, test_settings) as client:
        response = client.post("/api/v1/chat", json={"message": "run the screening"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["reply"] == "The screening completed."
    assert body["result"] == make_tea_response().model_dump(mode="json")
    assert uuid.UUID(body["request_id"])
    assert len(tea.requests) == 1


def test_needs_input_returns_null_result(test_settings: Settings) -> None:
    service, tea = service_with([final_message("Please provide capex.")])

    with client_for(service, test_settings) as client:
        response = client.post("/api/v1/chat", json={"message": "run it"})

    assert response.status_code == 200
    assert response.json()["status"] == "needs_input"
    assert response.json()["result"] is None
    assert tea.requests == []


def test_guardrail_error_returns_structured_422_without_tea_call(
    test_settings: Settings,
) -> None:
    payload = make_tea_request().model_dump(mode="python")
    payload["conditions"]["temperature_c"] = 1_500.0
    service, tea = service_with(
        [tool_call_message(payload), final_message("Temperature is too high.")]
    )

    with client_for(service, test_settings) as client:
        response = client.post("/api/v1/chat", json={"message": "run at 1500 C"})

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "BOUNDS_VIOLATION"
    assert detail["field"] == "conditions.temperature_c"
    assert detail["value"] == 1_500.0
    assert detail["minimum"] == 500.0
    assert detail["maximum"] == 1_000.0
    assert detail["message"] == "conditions.temperature_c must be between 500 and 1000."
    assert uuid.UUID(detail["request_id"])
    assert tea.requests == []


def test_unknown_catalyst_returns_422(test_settings: Settings) -> None:
    payload = make_tea_request().model_dump(mode="python")
    payload["conditions"]["catalyst"] = "Unobtainium"
    service, tea = service_with([tool_call_message(payload), final_message("Unknown catalyst.")])

    with client_for(service, test_settings) as client:
        response = client.post("/api/v1/chat", json={"message": "use Unobtainium"})

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "UNKNOWN_CATALYST"
    assert detail["field"] == "conditions.catalyst"
    assert "Unobtainium" in response.text
    assert tea.requests == []


def test_missing_arguments_returns_422_with_paths(test_settings: Settings) -> None:
    payload = make_tea_request().model_dump(mode="python")
    del payload["conditions"]["pressure_bar"]
    del payload["assumptions"]["capex_usd"]
    service, tea = service_with(
        [tool_call_message(payload), final_message("Which values are missing?")]
    )

    with client_for(service, test_settings) as client:
        response = client.post("/api/v1/chat", json={"message": "run it"})

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "MISSING_ARGUMENTS"
    assert detail["missing_fields"] == [
        "conditions.pressure_bar",
        "assumptions.capex_usd",
    ]
    assert tea.requests == []


def test_tea_unavailable_returns_503_with_request_id(test_settings: Settings) -> None:
    tea = FakeTeaClient(error=TeaUnavailableError("down"))
    service, _ = service_with(
        [
            tool_call_message(make_tea_request().model_dump(mode="python")),
            final_message("TEA is down."),
        ],
        tea=tea,
    )

    with client_for(service, test_settings) as client:
        response = client.post("/api/v1/chat", json={"message": "run it"})

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["code"] == "TEA_UNAVAILABLE"
    assert uuid.UUID(detail["request_id"])
    assert "api_key" not in response.text.lower()


def test_tea_rejected_returns_422(test_settings: Settings) -> None:
    tea = FakeTeaClient(error=TeaRejectedError("rejected"))
    service, _ = service_with(
        [
            tool_call_message(make_tea_request().model_dump(mode="python")),
            final_message("Rejected."),
        ],
        tea=tea,
    )

    with client_for(service, test_settings) as client:
        response = client.post("/api/v1/chat", json={"message": "run it"})

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "TEA_REJECTED"


def test_unconfigured_provider_returns_agent_unavailable(
    test_settings: Settings,
) -> None:
    app = create_app(test_settings)

    with TestClient(app) as client:
        response = client.post("/api/v1/chat", json={"message": "run it"})

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "AGENT_UNAVAILABLE"


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"message": ""},
        {"message": "   "},
        {"message": "x" * 2_001},
        {"message": "run it", "history": []},
    ],
)
def test_invalid_chat_request_is_rejected_by_validation(
    test_settings: Settings,
    body: dict[str, Any],
) -> None:
    class RecordingService:
        def __init__(self) -> None:
            self.calls = 0

        def chat(self, message: str, request_id: str) -> AgentOutcome:
            self.calls += 1
            return AgentOutcome(status="needs_input", reply="unused")

    service = RecordingService()
    app = create_app(test_settings)
    app.state.agent_service = service

    with TestClient(app) as client:
        response = client.post("/api/v1/chat", json=body)

    assert response.status_code == 422
    assert service.calls == 0


def test_configured_message_limit_is_enforced(test_settings: Settings) -> None:
    settings = test_settings.model_copy(update={"chat_max_message_chars": 5})
    service, tea = service_with([final_message("unused")])

    with client_for(service, settings) as client:
        response = client.post("/api/v1/chat", json={"message": "123456"})

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "INVALID_ARGUMENTS"
    assert detail["field"] == "message"
    assert "at most 5 characters" in detail["message"]
    assert tea.requests == []


def test_message_is_trimmed_before_reaching_service(test_settings: Settings) -> None:
    captured: list[str] = []

    class RecordingService:
        def chat(self, message: str, request_id: str) -> AgentOutcome:
            captured.append(message)
            return AgentOutcome(status="needs_input", reply="Please provide inputs.")

    app = create_app(test_settings)
    app.state.agent_service = RecordingService()

    with TestClient(app) as client:
        response = client.post("/api/v1/chat", json={"message": "  run it  "})

    assert response.status_code == 200
    assert captured == ["run it"]


def test_chat_request_strips_before_applying_the_length_limit() -> None:
    request = ChatRequest(message="  " + "x" * 2_000 + "  ")

    assert request.message == "x" * 2_000


def test_chat_response_rejects_inconsistent_status_and_result() -> None:
    with pytest.raises(ValidationError):
        ChatResponse(
            status="ok",
            reply="x",
            result=None,
            request_id="req-1",
        )
    with pytest.raises(ValidationError):
        ChatResponse(
            status="needs_input",
            reply="x",
            result=make_tea_response(),
            request_id="req-1",
        )


def test_chat_route_is_additive_in_openapi(test_settings: Settings) -> None:
    app = create_app(test_settings)
    paths = app.openapi()["paths"]

    assert "/api/v1/chat" in paths
    assert "/api/v1/predict" in paths
    assert "/api/v1/tea" in paths
    assert "/api/v1/market-prices" in paths
