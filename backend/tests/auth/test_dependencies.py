from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from odrm.auth.dependencies import get_current_user
from odrm.auth.models import User
from odrm.auth.service import AuthService
from odrm.auth.tokens import TokenService
from odrm.core.config import Settings
from tests.auth.fakes import InMemoryUserRepository, RecordingHasher

_NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
_NOW_TS = _NOW.timestamp()
_LATER_TS = (_NOW + timedelta(hours=2)).timestamp()


def make_user(*, is_active: bool = True) -> User:
    return User(
        id="11111111-1111-1111-1111-111111111111",
        email="engineer@example.com",
        password_hash="argon2-hash",
        role="engineer",
        is_active=is_active,
    )


@pytest.fixture()
def settings() -> Settings:
    return Settings(
        env="test",
        jwt_secret="test-secret-that-is-long-enough-for-tests",
        cors_origins="http://localhost:3000",
    )


@pytest.fixture()
def repository() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.fixture()
def service(
    settings: Settings,
    repository: InMemoryUserRepository,
) -> AuthService:
    return AuthService(
        repository,
        RecordingHasher(),
        TokenService(settings, clock=lambda: _NOW_TS),
    )


@pytest.fixture()
def app(settings: Settings, service: AuthService) -> FastAPI:
    test_app = FastAPI()
    test_app.state.settings = settings
    test_app.state.auth_service = service

    @test_app.get("/protected")
    def protected(user: Annotated[User, Depends(get_current_user)]) -> dict[str, str]:
        return {"email": user.email}

    @test_app.post("/protected")
    def protected_post(user: Annotated[User, Depends(get_current_user)]) -> dict[str, str]:
        return {"email": user.email}

    return test_app


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


def token_for(service: AuthService, repository: InMemoryUserRepository) -> str:
    user = repository.add(make_user())
    return service.issue_access_token(user)


def test_missing_credentials_return_generic_401(client: TestClient) -> None:
    response = client.get("/protected")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {
        "detail": {
            "code": "UNAUTHORIZED",
            "message": "Authentication required.",
        }
    }


def test_bearer_token_authenticates(
    client: TestClient,
    service: AuthService,
    repository: InMemoryUserRepository,
) -> None:
    token = token_for(service, repository)

    response = client.get("/protected", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {"email": "engineer@example.com"}


def test_invalid_bearer_does_not_fall_back_to_valid_cookie(
    client: TestClient,
    service: AuthService,
    repository: InMemoryUserRepository,
    settings: Settings,
) -> None:
    token = token_for(service, repository)
    client.cookies.set(settings.auth_cookie_name, token, path="/")

    response = client.get(
        "/protected",
        headers={"Authorization": "Bearer not-a-jwt"},
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_malformed_authorization_scheme_is_rejected(
    client: TestClient,
    service: AuthService,
    repository: InMemoryUserRepository,
) -> None:
    token = token_for(service, repository)

    response = client.get(
        "/protected",
        headers={"Authorization": f"Basic {token}"},
    )

    assert response.status_code == 401


def test_cookie_authenticates_safe_method_without_origin(
    client: TestClient,
    service: AuthService,
    repository: InMemoryUserRepository,
    settings: Settings,
) -> None:
    token = token_for(service, repository)
    client.cookies.set(settings.auth_cookie_name, token, path="/")

    response = client.get("/protected")

    assert response.status_code == 200


def test_cookie_post_requires_allowed_origin(
    client: TestClient,
    service: AuthService,
    repository: InMemoryUserRepository,
    settings: Settings,
) -> None:
    token = token_for(service, repository)
    client.cookies.set(settings.auth_cookie_name, token, path="/")

    response = client.post("/protected")

    assert response.status_code == 403
    assert response.json() == {
        "detail": {
            "code": "CSRF_ORIGIN_REJECTED",
            "message": "Request origin is not allowed.",
        }
    }


def test_cookie_post_rejects_disallowed_origin(
    client: TestClient,
    service: AuthService,
    repository: InMemoryUserRepository,
    settings: Settings,
) -> None:
    token = token_for(service, repository)
    client.cookies.set(settings.auth_cookie_name, token, path="/")

    response = client.post(
        "/protected",
        headers={"Origin": "https://evil.example.com"},
    )

    assert response.status_code == 403


def test_cookie_post_accepts_allowed_origin(
    client: TestClient,
    service: AuthService,
    repository: InMemoryUserRepository,
    settings: Settings,
) -> None:
    token = token_for(service, repository)
    client.cookies.set(settings.auth_cookie_name, token, path="/")

    response = client.post(
        "/protected",
        headers={"Origin": "http://localhost:3000"},
    )

    assert response.status_code == 200


def test_bearer_post_does_not_require_origin(
    client: TestClient,
    service: AuthService,
    repository: InMemoryUserRepository,
) -> None:
    token = token_for(service, repository)

    response = client.post(
        "/protected",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200


def test_expired_token_returns_401(
    settings: Settings,
    repository: InMemoryUserRepository,
) -> None:
    user = repository.add(make_user())
    issuing_service = AuthService(
        repository,
        RecordingHasher(),
        TokenService(settings, clock=lambda: _NOW_TS),
    )
    token = issuing_service.issue_access_token(user)
    expired_service = AuthService(
        repository,
        RecordingHasher(),
        TokenService(settings, clock=lambda: _LATER_TS),
    )
    test_app = FastAPI()
    test_app.state.settings = settings
    test_app.state.auth_service = expired_service

    @test_app.get("/protected")
    def protected(user: Annotated[User, Depends(get_current_user)]) -> dict[str, str]:
        return {"email": user.email}

    response = TestClient(test_app).get(
        "/protected",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
