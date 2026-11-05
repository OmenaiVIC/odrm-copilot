from __future__ import annotations

import json
from collections.abc import Callable

import httpx
import pytest

from odrm.agents.tea_client import HttpTeaClient, TeaRejectedError, TeaUnavailableError

from .fakes import make_tea_request, make_tea_response


def make_client(
    handler: Callable[[httpx.Request], httpx.Response],
) -> HttpTeaClient:
    return HttpTeaClient(
        base_url="http://tea.internal/api/v1/",
        timeout_seconds=5.0,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


def test_posts_valid_request_and_parses_response() -> None:
    captured: list[httpx.Request] = []
    response = make_tea_response()

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=response.model_dump(mode="json"))

    result = make_client(handler).calculate(make_tea_request())

    assert result == response
    assert len(captured) == 1
    request = captured[0]
    assert request.method == "POST"
    assert str(request.url) == "http://tea.internal/api/v1/tea"
    assert request.headers["content-type"] == "application/json"
    assert json.loads(request.content) == make_tea_request().model_dump(mode="json")


def test_http_422_maps_to_rejected_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"detail": "domain rejection"})

    with pytest.raises(TeaRejectedError):
        make_client(handler).calculate(make_tea_request())


@pytest.mark.parametrize("status_code", [500, 502, 503])
def test_http_5xx_maps_to_unavailable_without_retry(status_code: int) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(status_code, json={"detail": "down"})

    with pytest.raises(TeaUnavailableError):
        make_client(handler).calculate(make_tea_request())
    assert calls == 1


def test_connect_error_maps_to_unavailable_without_retry() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ConnectError("connection refused", request=request)

    with pytest.raises(TeaUnavailableError):
        make_client(handler).calculate(make_tea_request())
    assert calls == 1


def test_timeout_maps_to_unavailable_without_retry() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("timed out", request=request)

    with pytest.raises(TeaUnavailableError):
        make_client(handler).calculate(make_tea_request())
    assert calls == 1


@pytest.mark.parametrize(
    "body",
    [
        {"unexpected": True},
        {"predictions": {}, "model_versions": {}, "financials": {}, "warnings": []},
        {
            "predictions": {"x": "not-a-number"},
            "model_versions": {},
            "financials": {},
            "warnings": [],
        },
    ],
)
def test_invalid_response_body_maps_to_unavailable(body: dict[str, object]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=body)

    with pytest.raises(TeaUnavailableError):
        make_client(handler).calculate(make_tea_request())


def test_non_json_response_maps_to_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not json")

    with pytest.raises(TeaUnavailableError):
        make_client(handler).calculate(make_tea_request())
