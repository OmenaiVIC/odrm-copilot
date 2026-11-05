from __future__ import annotations

from typing import Protocol

import httpx
from pydantic import ValidationError

from odrm.api.schemas import TeaRequest, TeaResponse


class TeaClientError(RuntimeError):
    """Base class for typed TEA client failures."""


class TeaRejectedError(TeaClientError):
    """The TEA endpoint rejected an otherwise valid request."""


class TeaUnavailableError(TeaClientError):
    """The TEA endpoint is unreachable, timed out, or returned an invalid response."""


class TeaClient(Protocol):
    def calculate(self, request: TeaRequest) -> TeaResponse: ...


class HttpTeaClient:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        self._tea_url = f"{base_url.rstrip('/')}/tea"
        self._client = client or httpx.Client(timeout=timeout_seconds, trust_env=False)

    def calculate(self, request: TeaRequest) -> TeaResponse:
        try:
            response = self._client.post(
                self._tea_url,
                json=request.model_dump(mode="json"),
            )
        except httpx.HTTPError as exc:
            raise TeaUnavailableError("The TEA service is unavailable.") from exc

        if response.status_code == 422:
            raise TeaRejectedError("The TEA service rejected the request.")
        if 400 <= response.status_code < 500:
            raise TeaRejectedError("The TEA service rejected the request.")
        if response.status_code < 200 or response.status_code >= 300:
            raise TeaUnavailableError("The TEA service is unavailable.")

        try:
            payload = response.json()
        except ValueError as exc:
            raise TeaUnavailableError("The TEA service returned an invalid response.") from exc

        try:
            return TeaResponse.model_validate(payload)
        except ValidationError as exc:
            raise TeaUnavailableError("The TEA service returned an invalid response.") from exc

    def close(self) -> None:
        self._client.close()
