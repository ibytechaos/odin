"""Configuration settings using Pydantic."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Main configuration for Odin framework."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="ODIN_",
        case_sensitive=False,
        extra="ignore",
    )

    # General settings
    env: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # LLM Provider settings
    llm_provider: Literal["openai", "anthropic", "azure"] = "openai"
    openai_api_key: str | None = Field(None, validation_alias="OPENAI_API_KEY")
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str | None = Field(None, validation_alias="OPENAI_BASE_URL")
    anthropic_api_key: str | None = Field(None, validation_alias="ANTHROPIC_API_KEY")
    anthropic_model: str = "claude-sonnet-4-5-20250929"
    azure_openai_api_key: str | None = Field(None, validation_alias="AZURE_OPENAI_API_KEY")
    azure_openai_endpoint: str | None = Field(None, validation_alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_deployment: str | None = Field(None, validation_alias="AZURE_OPENAI_DEPLOYMENT")
    azure_openai_api_version: str = "2024-02-15-preview"

    # Agent Backend settings
    agent_backend: Literal["crewai", "langgraph", "custom"] = "crewai"
    agent_name: str = "odin_agent"
    agent_description: str = "AI assistant powered by Odin framework"
    custom_agent_path: str | None = None  # Path to custom agent class (e.g., "my_agents.CustomAgent")

    # Checkpointer settings
    checkpointer_type: Literal["memory", "sqlite", "postgres", "redis"] = "memory"
    checkpointer_uri: str | None = None  # Connection string for persistent checkpointers

    # Tracing settings
    otel_enabled: bool = True
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "odin"

    # Storage settings
    redis_url: str = "redis://localhost:6379/0"
    sqlite_path: Path = Path("./data/odin.db")
    postgres_url: str | None = None

    # Protocol settings
    http_host: str = "0.0.0.0"
    http_port: int = 8000
    mcp_enabled: bool = True
    mcp_port: int = 8001
    a2a_enabled: bool = False
    a2a_port: int = 8002

    # Plugin settings
    plugin_auto_discovery: bool = True
    plugin_dirs: list[Path] = Field(default_factory=lambda: [Path("./plugins")])

    # Security
    api_key: str | None = None
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:8000"]
    )

    # Performance
    token_limit_per_request: int = 100000
    enable_semantic_cache: bool = True
    rate_limit_requests_per_minute: int = 60

    @field_validator("plugin_dirs", mode="before")
    @classmethod
    def parse_plugin_dirs(cls, v: str | list[str] | list[Path]) -> list[Path]:
        """Parse plugin directories from string or list."""
        if isinstance(v, str):
            return [Path(p.strip()) for p in v.split(",")]
        if isinstance(v, list):
            return [Path(p) if isinstance(p, str) else p for p in v]
        return v

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    def is_production(self) -> bool:
        """Check if running in production."""
        return self.env == "production"

    def is_development(self) -> bool:
        """Check if running in development."""
        return self.env == "development"


_settings_instance: Settings | None = None


def get_settings(reload: bool = False) -> Settings:
    """Get settings instance with optional hot reload.

    Args:
        reload: If True, reload settings from environment/file

    Returns:
        Settings instance (singleton by default)
    """
    global _settings_instance

    if reload or _settings_instance is None:
        _settings_instance = Settings()

    return _settings_instance


def reload_settings() -> Settings:
    """Force reload settings from environment/file.

    Returns:
        Newly loaded Settings instance
    """
    return get_settings(reload=True)
