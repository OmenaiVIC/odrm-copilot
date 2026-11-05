from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from odrm.core.config import Settings

_DEFAULT_BASE_URLS: dict[str, str] = {
    "ollama": "http://localhost:11434/v1",
}
_OLLAMA_DUMMY_KEY = "ollama"


class AgentConfigurationError(RuntimeError):
    """Raised when the configured chat provider cannot be constructed."""


def build_chat_model(settings: Settings) -> BaseChatModel:
    model_name = (settings.llm_model or "").strip()
    if not model_name:
        raise AgentConfigurationError("ODRM_LLM_MODEL is not configured.")

    provider = settings.llm_provider
    api_key = settings.llm_api_key

    # 1. Native Gemini Integration
    if provider == "gemini":
        if api_key is None:
            raise AgentConfigurationError("ODRM_LLM_API_KEY is required for the gemini provider.")
        
        key_str = api_key.get_secret_value() if isinstance(api_key, SecretStr) else api_key
        
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=key_str,
            temperature=settings.llm_temperature,
            max_retries=0,
            timeout=settings.llm_timeout_seconds,
        )

    # 2. OpenAI and Ollama Integration (using ChatOpenAI)
    if provider == "ollama":
        api_key = api_key or SecretStr(_OLLAMA_DUMMY_KEY)
    elif api_key is None:
        raise AgentConfigurationError(f"ODRM_LLM_API_KEY is required for the {provider} provider.")

    base_url = settings.llm_base_url or _DEFAULT_BASE_URLS.get(provider)

    return ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=settings.llm_temperature,
        timeout=settings.llm_timeout_seconds,
        max_retries=0,
    )