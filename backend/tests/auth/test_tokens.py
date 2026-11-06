from __future__ import annotations

import time

import jwt
import pytest

from odrm.auth.tokens import TokenError, TokenService
from odrm.core.config import Settings


class Clock:
    def __init__(self, now: float | None = None) -> None:
        self.now = time.time() if now is None else now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture()
def clock() -> Clock:
    return Clock()


@pytest.fixture()
def settings() -> Settings:
    return Settings(
        env="test",
        jwt_secret="unit-test-secret-that-is-long-enough",
        jwt_issuer="odrm-test",
        jwt_audience="odrm-test-api",
        jwt_access_token_minutes=60,
    )


@pytest.fixture()
def service(settings: Settings, clock: Clock) -> TokenService:
    return TokenService(settings, clock=clock)


def issue(service: TokenService) -> str:
    return service.issue_access_token(
        user_id="00000000-0000-0000-0000-000000000001",
        email="engineer@example.com",
        role="engineer",
    )


def test_issued_token_has_expected_claims_and_expiry(service: TokenService, clock: Clock) -> None:
    token = issue(service)
    payload = jwt.decode(
        token,
        "unit-test-secret-that-is-long-enough",
        algorithms=["HS256"],
        audience="odrm-test-api",
        issuer="odrm-test",
    )

    assert payload["iss"] == "odrm-test"
    assert payload["aud"] == "odrm-test-api"
    assert payload["sub"] == "00000000-0000-0000-0000-000000000001"
    assert payload["email"] == "engineer@example.com"
    assert payload["role"] == "engineer"
    assert payload["iat"] == int(clock.now)
    assert payload["exp"] == int(clock.now) + 3_600
    assert payload["jti"]


def test_valid_token_round_trips_to_claims(service: TokenService) -> None:
    claims = service.decode_access_token(issue(service))

    assert claims.sub == "00000000-0000-0000-0000-000000000001"
    assert claims.email == "engineer@example.com"
    assert claims.role == "engineer"


def test_expired_token_fails(service: TokenService, clock: Clock) -> None:
    token = issue(service)
    clock.advance(3_601)

    with pytest.raises(TokenError):
        service.decode_access_token(token)


def test_wrong_secret_fails(settings: Settings, clock: Clock, service: TokenService) -> None:
    token = issue(service)
    other = TokenService(
        Settings(
            env="test",
            jwt_secret="different-secret-that-is-long-enough",
            jwt_issuer="odrm-test",
            jwt_audience="odrm-test-api",
        ),
        clock=clock,
    )

    with pytest.raises(TokenError):
        other.decode_access_token(token)


def test_wrong_issuer_fails(settings: Settings, clock: Clock, service: TokenService) -> None:
    token = issue(service)
    other = TokenService(settings.model_copy(update={"jwt_issuer": "other"}), clock=clock)

    with pytest.raises(TokenError):
        other.decode_access_token(token)


def test_wrong_audience_fails(settings: Settings, clock: Clock, service: TokenService) -> None:
    token = issue(service)
    other = TokenService(settings.model_copy(update={"jwt_audience": "other"}), clock=clock)

    with pytest.raises(TokenError):
        other.decode_access_token(token)


def test_malformed_token_fails(service: TokenService) -> None:
    with pytest.raises(TokenError):
        service.decode_access_token("not-a-jwt")


def test_missing_required_claim_fails(service: TokenService, clock: Clock) -> None:
    token = jwt.encode(
        {
            "iss": "odrm-test",
            "aud": "odrm-test-api",
            "iat": int(clock.now),
            "exp": int(clock.now) + 3_600,
            "sub": "user",
        },
        "unit-test-secret-that-is-long-enough",
        algorithm="HS256",
    )

    with pytest.raises(TokenError):
        service.decode_access_token(token)


def test_alg_none_token_fails(service: TokenService, clock: Clock) -> None:
    token = jwt.encode(
        {
            "iss": "odrm-test",
            "aud": "odrm-test-api",
            "iat": int(clock.now),
            "exp": int(clock.now) + 3_600,
            "jti": "jti",
            "sub": "user",
            "email": "engineer@example.com",
            "role": "engineer",
        },
        key="",
        algorithm="none",
    )

    with pytest.raises(TokenError):
        service.decode_access_token(token)


def test_jti_is_unique_per_issue(service: TokenService) -> None:
    first = service.decode_access_token(issue(service))
    second = service.decode_access_token(issue(service))

    assert first.jti != second.jti


def test_token_service_accepts_an_injected_clock(service: TokenService, clock: Clock) -> None:
    clock.advance(5)
    claims = service.decode_access_token(issue(service))

    assert claims.iat == int(clock.now)


def test_expiry_uses_the_injected_clock(settings: Settings) -> None:
    clock = Clock()
    service = TokenService(settings, clock=clock)
    token = service.issue_access_token(
        user_id="00000000-0000-0000-0000-000000000001",
        email="engineer@example.com",
        role="engineer",
    )

    clock.advance(3_600)
    with pytest.raises(TokenError):
        service.decode_access_token(token)
