from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from odrm.auth.models import User
from odrm.auth.service import AuthenticationError, AuthService
from odrm.auth.tokens import TokenService
from odrm.core.config import Settings
from tests.auth.fakes import InMemoryUserRepository, RecordingHasher

_NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
_NOW_TS = _NOW.timestamp()
_LATER_TS = (_NOW + timedelta(hours=2)).timestamp()


def make_user(
    *,
    user_id: str = "11111111-1111-1111-1111-111111111111",
    email: str = "engineer@example.com",
    password_hash: str = "argon2-hash",
    role: str = "engineer",
    is_active: bool = True,
) -> User:
    return User(
        id=user_id,
        email=email,
        password_hash=password_hash,
        role=role,
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
def tokens(settings: Settings) -> TokenService:
    return TokenService(settings, clock=lambda: _NOW_TS)


@pytest.fixture()
def repository() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.fixture()
def hasher() -> RecordingHasher:
    return RecordingHasher()


@pytest.fixture()
def service(
    repository: InMemoryUserRepository,
    hasher: RecordingHasher,
    tokens: TokenService,
) -> AuthService:
    return AuthService(repository, hasher, tokens)


def test_authenticate_returns_active_user(
    repository: InMemoryUserRepository,
    service: AuthService,
) -> None:
    user = repository.add(make_user())

    authenticated = service.authenticate("ENGINEER@example.com", "correct-password")

    assert authenticated.id == user.id


def test_authenticate_unknown_email_uses_dummy_hash_and_generic_error(
    service: AuthService,
    hasher: RecordingHasher,
) -> None:
    with pytest.raises(AuthenticationError, match=r"Invalid email or password\."):
        service.authenticate("missing@example.com", "wrong-password")

    assert hasher.dummy_calls == 1


def test_authenticate_wrong_password_is_generic(
    repository: InMemoryUserRepository,
    service: AuthService,
    hasher: RecordingHasher,
) -> None:
    repository.add(make_user())
    hasher.valid = False

    with pytest.raises(AuthenticationError, match=r"Invalid email or password\."):
        service.authenticate("engineer@example.com", "wrong-password")

    assert hasher.dummy_calls == 0
    assert hasher.verify_calls == [("wrong-password", "argon2-hash")]


def test_authenticate_inactive_user_is_generic(
    repository: InMemoryUserRepository,
    service: AuthService,
) -> None:
    repository.add(make_user(is_active=False))

    with pytest.raises(AuthenticationError, match=r"Invalid email or password\."):
        service.authenticate("engineer@example.com", "correct-password")


def test_issue_token_contains_user_claims(
    repository: InMemoryUserRepository,
    service: AuthService,
    tokens: TokenService,
) -> None:
    user = repository.add(make_user(role="admin"))

    token = service.issue_access_token(user)
    claims = tokens.decode_access_token(token)

    assert claims.sub == user.id
    assert claims.email == user.email
    assert claims.role == "admin"


def test_resolve_token_returns_current_active_user(
    repository: InMemoryUserRepository,
    service: AuthService,
) -> None:
    user = repository.add(make_user())
    token = service.issue_access_token(user)

    resolved = service.resolve_access_token(token)

    assert resolved.id == user.id


def test_resolve_token_rejects_unknown_user(
    repository: InMemoryUserRepository,
    service: AuthService,
    tokens: TokenService,
) -> None:
    token = tokens.issue_access_token(
        user_id="22222222-2222-2222-2222-222222222222",
        email="missing@example.com",
        role="engineer",
    )

    with pytest.raises(AuthenticationError, match=r"Authentication required\."):
        service.resolve_access_token(token)


def test_resolve_token_rejects_inactive_user(
    repository: InMemoryUserRepository,
    service: AuthService,
) -> None:
    user = repository.add(make_user(is_active=False))
    token = service.issue_access_token(user)

    with pytest.raises(AuthenticationError, match=r"Authentication required\."):
        service.resolve_access_token(token)


def test_resolve_token_rejects_expired_token(
    repository: InMemoryUserRepository,
    settings: Settings,
    hasher: RecordingHasher,
    tokens: TokenService,
) -> None:
    user = repository.add(make_user())
    token = tokens.issue_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
    )
    future_service = AuthService(
        repository,
        hasher,
        TokenService(settings, clock=lambda: _LATER_TS),
    )

    with pytest.raises(AuthenticationError, match=r"Authentication required\."):
        future_service.resolve_access_token(token)


def test_resolve_token_rejects_invalid_token(service: AuthService) -> None:
    with pytest.raises(AuthenticationError, match=r"Authentication required\."):
        service.resolve_access_token("not-a-jwt")
