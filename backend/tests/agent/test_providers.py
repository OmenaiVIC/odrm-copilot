from __future__ import annotations

import pytest
from langchain_openai import ChatOpenAI
from pydantic import SecretStr, ValidationError

from odrm.agents.providers import AgentConfigurationError, build_chat_model
from odrm.core.config import Settings


def make_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "env": "test",
        "llm_model": "test-model",
        "llm_api_key": SecretStr("sk-test-secret"),
    }
    values.update(overrides)
    return Settings(**values)


def test_openai_provider_uses_configured_model_and_key() -> None:
    model = build_chat_model(make_settings(llm_provider="openai"))

    assert isinstance(model, ChatOpenAI)
    assert model.model_name == "test-model"
    assert model.temperature == 0.0
    assert model.max_retries == 0
    assert model.openai_api_key is not None
    assert model.openai_api_key.get_secret_value() == "sk-test-secret"


def test_local_ollama_uses_dummy_key_and_default_base_url() -> None:
    model = build_chat_model(make_settings(llm_provider="ollama", llm_api_key=None))

    assert isinstance(model, ChatOpenAI)
    assert model.openai_api_base == "http://localhost:11434/v1"
    assert model.openai_api_key is not None
    assert model.openai_api_key.get_secret_value() == "ollama"


def test_gemini_uses_openai_compatible_default_base_url() -> None:
    model = build_chat_model(make_settings(llm_provider="gemini"))

    assert isinstance(model, ChatOpenAI)
    assert model.openai_api_base == "https://generativelanguage.googleapis.com/v1beta/openai/"


def test_explicit_base_url_overrides_provider_default() -> None:
    model = build_chat_model(
        make_settings(llm_provider="openai", llm_base_url="http://llm-proxy.internal/v1")
    )

    assert model.openai_api_base == "http://llm-proxy.internal/v1"


@pytest.mark.parametrize("provider", ["openai", "gemini"])
def test_missing_api_key_raises_without_exposing_secret(provider: str) -> None:
    with pytest.raises(AgentConfigurationError, match="ODRM_LLM_API_KEY"):
        build_chat_model(make_settings(llm_provider=provider, llm_api_key=None))


def test_missing_model_raises_configuration_error() -> None:
    with pytest.raises(AgentConfigurationError, match="ODRM_LLM_MODEL"):
        build_chat_model(make_settings(llm_model=None))


def test_blank_model_is_treated_as_missing() -> None:
    with pytest.raises(AgentConfigurationError, match="ODRM_LLM_MODEL"):
        build_chat_model(make_settings(llm_model="   "))


def test_settings_validate_llm_ranges() -> None:
    with pytest.raises(ValidationError):
        make_settings(llm_temperature=1.1)
    with pytest.raises(ValidationError):
        make_settings(llm_timeout_seconds=0)
    with pytest.raises(ValidationError):
        make_settings(chat_max_message_chars=8_001)
    with pytest.raises(ValidationError):
        make_settings(llm_provider="unknown")
