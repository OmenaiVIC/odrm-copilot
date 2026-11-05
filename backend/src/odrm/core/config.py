from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ODRM_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: str = "local"
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:3000"
    model_dir: str = "./models"
    data_dir: str = "./data"
    max_temperature_c: float = 1000.0
    market_data_ttl_seconds: int = Field(default=86_400, ge=0, le=604_800)
    llm_provider: Literal["openai", "ollama", "gemini"] = "openai"
    llm_model: str | None = None
    llm_api_key: SecretStr | None = None
    llm_base_url: str | None = None
    llm_temperature: float = Field(default=0.0, ge=0.0, le=1.0)
    llm_timeout_seconds: float = Field(default=30.0, gt=0.0)
    chat_max_message_chars: int = Field(default=2_000, ge=1, le=8_000)
    tea_api_base_url: str = "http://127.0.0.1:8000/api/v1"
    tea_timeout_seconds: float = Field(default=30.0, gt=0.0)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
