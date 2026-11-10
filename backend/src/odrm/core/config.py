from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEVELOPMENT_JWT_SECRET = "dev-only-insecure-jwt-secret-change-me"
_PRODUCTION_ENVS = {"staging", "production", "prod"}


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
    chat_max_messages: int = Field(default=20, ge=1, le=100)
    chat_max_history_chars: int = Field(default=30_000, ge=1_000, le=60_000)
    chat_history_max_messages: int = Field(default=10, ge=1, le=50)
    chat_history_max_chars: int = Field(default=16_000, ge=1_000, le=60_000)
    tea_api_base_url: str = "http://127.0.0.1:8000/api/v1"
    tea_timeout_seconds: float = Field(default=30.0, gt=0.0)

    jwt_secret: SecretStr = SecretStr(_DEVELOPMENT_JWT_SECRET)
    jwt_algorithm: Literal["HS256"] = "HS256"
    jwt_issuer: str = "odrm-copilot"
    jwt_audience: str = "odrm-api"
    jwt_access_token_minutes: int = Field(default=60, ge=5, le=1_440)
    database_url: str = "sqlite:///./odrm.db"
    auth_cookie_name: str = "odrm_access_token"
    auth_cookie_secure: bool = False
    auth_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    rate_limit_enabled: bool = True
    max_request_bytes: int = Field(default=65_536, ge=1_024, le=1_048_576)

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        secret = self.jwt_secret.get_secret_value()
        if self.env.lower() in _PRODUCTION_ENVS and (
            secret == _DEVELOPMENT_JWT_SECRET or len(secret) < 32
        ):
            raise ValueError(
                "jwt_secret must be a non-placeholder value of at least 32 characters "
                "in staging and production"
            )
        if self.auth_cookie_samesite == "none" and not self.auth_cookie_secure:
            raise ValueError(
                "auth_cookie_secure must be true when auth_cookie_samesite is 'none'"
            )
        if self.chat_history_max_messages > self.chat_max_messages:
            raise ValueError(
                "chat_history_max_messages must be less than or equal to chat_max_messages"
            )
        if self.chat_history_max_chars > self.chat_max_history_chars:
            raise ValueError(
                "chat_history_max_chars must be less than or equal to chat_max_history_chars"
            )
        if self.chat_max_history_chars >= self.max_request_bytes:
            raise ValueError(
                "chat_max_history_chars must be less than max_request_bytes"
            )
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
