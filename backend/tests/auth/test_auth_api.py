from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from odrm.auth.models import User
from odrm.auth.passwords import PasswordHasher
from odrm.core.config import Settings
from odrm.main import create_app
from tests.auth.fakes import InMemoryUserRepository

_PASSWORD = "correct horse battery staple"


@pytest.fixture()
def password_hasher() -> PasswordHasher:
    return PasswordHasher()


@pytest.fixture()
def settings() -> Settings:
    return Settings(
        env="test",
        jwt_secret="test-secret-that-is-long-enough-for-tests",
        cors_origins="http://localhost:3000",
        rate_limit_enabled=False,
    )


@pytest.fixture()
def user(password_hasher: PasswordHasher) -> User:
    return User(
        id="11111111-1111-1111-1111-111111111111",
        email="engineer@example.com",
        password_hash=password_hasher.hash(_PASSWORD),
        role="engineer",
        is_active=True,
    )


@pytest.fixture()
def repository(user: User) -> InMemoryUserRepository:
    repository = InMemoryUserRepository()
    repository.add(user)
    return repository


@pytest.fixture()
def client(
    settings: Settings,
    repository: InMemoryUserRepository,
) -> Iterator[TestClient]:
    app = create_app(settings=settings, user_repository=repository)
    with TestClient(app) as test_client:
        yield test_client


def login(client: TestClient, email: str = "engineer@example.com", password: str = _PASSWORD):
    return client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )


def test_login_returns_token_user_and_http_only_cookie(
    client: TestClient,
    user: User,
) -> None:
    response = login(client, email="ENGINEER@example.com")

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 3600
    assert body["access_token"]
    assert body["user"] == {
        "id": user.id,
        "email": "engineer@example.com",
        "role": "engineer",
    }
    assert "password" not in body
    assert "password_hash" not in response.text

    set_cookie = response.headers["set-cookie"]
    assert "odrm_access_token=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Path=/api/v1" in set_cookie
    assert "Max-Age=3600" in set_cookie
    assert "SameSite=lax" in set_cookie
    assert response.headers["cache-control"] == "no-store"


def test_login_unknown_email_is_generic(client: TestClient) -> None:
    response = login(client, email="missing@example.com")

    assert response.status_code == 401
    assert response.json() == {
        "detail": {
            "code": "INVALID_CREDENTIALS",
            "message": "Invalid email or password.",
        }
    }
    assert "set-cookie" not in response.headers


def test_login_wrong_password_is_generic(client: TestClient) -> None:
    response = login(client, password="wrong-password")

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "INVALID_CREDENTIALS"
    assert "set-cookie" not in response.headers


def test_login_inactive_user_is_generic(
    client: TestClient,
    repository: InMemoryUserRepository,
    user: User,
) -> None:
    repository.users[user.id].is_active = False

    response = login(client)

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "INVALID_CREDENTIALS"


def test_login_rejects_invalid_email_shape(client: TestClient) -> None:
    response = login(client, email="not-an-email")

    assert response.status_code == 422


def test_me_returns_current_user_with_bearer(client: TestClient) -> None:
    token = login(client).json()["access_token"]

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": "11111111-1111-1111-1111-111111111111",
        "email": "engineer@example.com",
        "role": "engineer",
    }
    assert response.headers["cache-control"] == "no-store"


def test_me_returns_current_user_with_cookie(client: TestClient) -> None:
    assert login(client).status_code == 200

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json()["email"] == "engineer@example.com"


def test_me_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["detail"]["code"] == "UNAUTHORIZED"


def test_logout_clears_cookie_and_is_idempotent(client: TestClient) -> None:
    first = client.post("/api/v1/auth/logout")
    second = client.post("/api/v1/auth/logout")

    assert first.status_code == 204
    assert second.status_code == 204
    for response in (first, second):
        set_cookie = response.headers["set-cookie"]
        assert "odrm_access_token=" in set_cookie
        assert "Path=/api/v1" in set_cookie
        assert "Max-Age=0" in set_cookie


def test_openapi_declares_http_bearer_scheme(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()

    assert "HTTPBearer" in schema["components"]["securitySchemes"]
    assert schema["paths"]["/api/v1/auth/me"]["get"]["security"]
