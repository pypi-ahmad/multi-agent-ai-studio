from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["development", "staging", "production"] = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_secret_key: str = Field(
        default="replace-with-at-least-32-character-secret-key",
        min_length=32,
    )
    app_jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    refresh_token_minutes: int = 60 * 24 * 30
    allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "ai_studio"
    postgres_user: str = "ai_studio"
    postgres_password: str = "ai_studio"

    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"
    qdrant_timeout_seconds: int = 30
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minio"
    minio_secret_key: str = "minio123"
    minio_bucket: str = "ai-studio"

    ollama_base_url: str = "http://localhost:11434"
    ollama_request_timeout: int = 180
    ollama_health_timeout: int = 5
    ollama_bootstrap_models: str = "qwen3.5:4b,qwen3-embedding:4b"
    ollama_auto_pull_models: bool = True
    ollama_preferred_chat_model: str = ""
    ollama_preferred_embedding_model: str = ""
    ollama_disable_thinking: bool = True
    model_router_refresh_seconds: int = 60
    metrics_sample_interval_seconds: int = 5

    github_oauth_client_id: str = ""
    github_oauth_client_secret: str = ""
    github_oauth_callback: str = "http://localhost:8000/api/v1/auth/github/callback"

    langfuse_host: str = ""
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    otel_exporter_otlp_endpoint: str = ""

    rate_limit_rpm: int = 120
    tool_sandbox_image: str = "python:3.12-slim"
    tool_execution_mode: Literal["container_preferred", "host_only"] = "container_preferred"
    tool_container_network: str = "none"
    tool_container_cpus: float = 1.5
    tool_container_memory: str = "1g"

    @property
    def database_url(self) -> str:
        """Build async SQLAlchemy database URL."""
        return (
            "postgresql+asyncpg://"
            f"{self.postgres_user}:{self.postgres_password}@"
            f"{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def bootstrap_models(self) -> list[str]:
        """Return normalized bootstrap model list."""
        return [item.strip() for item in self.ollama_bootstrap_models.split(",") if item.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return singleton settings object."""
    return Settings()
