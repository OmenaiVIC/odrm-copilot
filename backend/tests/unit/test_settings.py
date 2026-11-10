from __future__ import annotations

import pytest
from pydantic import ValidationError

from odrm.core.config import Settings


def test_security_defaults_are_safe_for_local_development() -> None:
    settings = Settings(env="test")

    assert settings.jwt_algorithm == "HS256"
    assert settings.jwt_issuer == "odrm-copilot"
    assert settings.jwt_audience == "odrm-api"
    assert settings.jwt_access_token_minutes == 60
    assert settings.database_url == "sqlite:///./odrm.db"
    assert settings.auth_cookie_name == "odrm_access_token"
    assert settings.auth_cookie_secure is False
    assert settings.auth_cookie_samesite == "lax"
    assert settings.rate_limit_enabled is True
    assert settings.max_request_bytes == 65_536
    assert len(settings.jwt_secret.get_secret_value()) >= 32


@pytest.mark.parametrize("env", ["staging", "production", "prod"])
@pytest.mark.parametrize(
    "secret",
    [
        None,
        "short-secret",
        "dev-only-insecure-jwt-secret-change-me",
    ],
)
def test_production_rejects_missing_short_or_placeholder_jwt_secret(
    env: str, secret: str | None
) -> None:
    kwargs = {"env": env}
    if secret is not None:
        kwargs["jwt_secret"] = secret

    with pytest.raises(ValidationError, match="jwt_secret"):
        Settings(**kwargs)


@pytest.mark.parametrize("env", ["staging", "production", "prod"])
def test_production_accepts_a_long_non_placeholder_jwt_secret(env: str) -> None:
    settings = Settings(env=env, jwt_secret="x" * 32)

    assert settings.jwt_secret.get_secret_value() == "x" * 32


def test_local_and_test_environments_allow_the_development_secret() -> None:
    assert Settings(env="local").jwt_secret.get_secret_value()
    assert Settings(env="test").jwt_secret.get_secret_value()


def test_samesite_none_requires_a_secure_cookie() -> None:
    with pytest.raises(ValidationError, match="auth_cookie_secure"):
        Settings(env="test", auth_cookie_samesite="none", auth_cookie_secure=False)

    settings = Settings(env="test", auth_cookie_samesite="none", auth_cookie_secure=True)
    assert settings.auth_cookie_samesite == "none"


@pytest.mark.parametrize("minutes", [4, 1_441])
def test_jwt_access_token_minutes_are_bounded(minutes: int) -> None:
    with pytest.raises(ValidationError, match="jwt_access_token_minutes"):
        Settings(env="test", jwt_access_token_minutes=minutes)


def test_jwt_algorithm_is_fixed_to_hs256() -> None:
    with pytest.raises(ValidationError, match="jwt_algorithm"):
        Settings(env="test", jwt_algorithm="none")


def test_cors_origins_are_trimmed_and_empty_values_ignored() -> None:
    settings = Settings(
        env="test",
        cors_origins=" http://localhost:3000, https://odrm.example ,, ",
    )

    assert settings.cors_origin_list == [
        "http://localhost:3000",
        "https://odrm.example",
    ]


def test_chat_history_defaults_are_configured() -> None:
    settings = Settings(env="test")

    assert settings.chat_max_message_chars == 2_000
    assert settings.chat_max_messages == 20
    assert settings.chat_max_history_chars == 30_000
    assert settings.chat_history_max_messages == 10
    assert settings.chat_history_max_chars == 16_000


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("chat_max_messages", 0),
        ("chat_max_messages", 101),
        ("chat_max_history_chars", 999),
        ("chat_max_history_chars", 60_001),
        ("chat_history_max_messages", 0),
        ("chat_history_max_messages", 51),
        ("chat_history_max_chars", 999),
        ("chat_history_max_chars", 60_001),
    ],
)
def test_chat_history_settings_are_bounded(field: str, value: int) -> None:
    with pytest.raises(ValidationError, match=field):
        Settings(env="test", **{field: value})


def test_chat_history_model_message_window_cannot_exceed_the_request_window() -> None:
    with pytest.raises(ValidationError, match="chat_history_max_messages"):
        Settings(env="test", chat_max_messages=5, chat_history_max_messages=6)


def test_chat_history_model_character_window_cannot_exceed_the_request_window() -> None:
    with pytest.raises(ValidationError, match="chat_history_max_chars"):
        Settings(
            env="test",
            chat_max_history_chars=1_000,
            chat_history_max_chars=1_001,
        )


def test_chat_history_request_window_must_fit_the_body_limit() -> None:
    with pytest.raises(ValidationError, match="chat_max_history_chars"):
        Settings(env="test", max_request_bytes=20_000)