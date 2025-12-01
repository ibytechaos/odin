"""Configuration settings using Pydantic."""

import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_and_load_env_file() -> str | None:
    """Find .env file and load it, prioritizing current directory."""
    cwd = Path.cwd()
    env_path = cwd / ".env"
    if env_path.exists():
        # Load .env with override=True to override existing env vars
        load_dotenv(env_path, override=True)
        return str(env_path)
    return ".env"


# Load .env file immediately on module import
_env_file_path = _find_and_load_env_file()


class Settings(BaseSettings):
    """Main configuration for Odin framework."""

    model_config = SettingsConfigDict(
        env_file=None,  # We already loaded via dotenv with override
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
    openai_model: str = Field("gpt-4o-mini", validation_alias="OPENAI_MODEL")
    openai_base_url: str | None = Field(None, validation_alias="OPENAI_BASE_URL")
    anthropic_api_key: str | None = Field(None, validation_alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field("claude-sonnet-4-5-20250929", validation_alias="ANTHROPIC_MODEL")
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
    otel_console_metrics: bool = False  # Disable console metrics output by default

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
    builtin_plugins: list[str] = Field(
        default_factory=lambda: ["http", "utilities"],
        description="List of builtin plugins to load (e.g., http, utilities, github, google, trending)",
    )

    # Security
    api_key: str | None = None
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:8000"]
    )

    # Performance
    token_limit_per_request: int = 100000
    enable_semantic_cache: bool = True
    rate_limit_requests_per_minute: int = 60

    # Browser automation settings (for NotebookLM, etc.)
    browser_debug_url: str | None = Field(None, validation_alias="BROWSER_DEBUG_URL")
    browser_download_dir: str | None = Field(None, validation_alias="BROWSER_DOWNLOAD_DIR")

    @field_validator("plugin_dirs", mode="before")
    @classmethod
    def parse_plugin_dirs(cls, v: str | list[str] | list[Path]) -> list[Path]:
        """Parse plugin directories from string or list."""
        if isinstance(v, str):
            return [Path(p.strip()) for p in v.split(",")]
        if isinstance(v, list):
            return [Path(p) if isinstance(p, str) else p for p in v]
        return v

    @field_validator("builtin_plugins", mode="before")
    @classmethod
    def parse_builtin_plugins(cls, v: str | list[str]) -> list[str]:
        """Parse builtin plugins from string or list."""
        if isinstance(v, str):
            return [p.strip() for p in v.split(",") if p.strip()]
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
_settings_logged: bool = False


def _log_settings(settings: Settings) -> None:
    """Log key configuration settings on first load."""
    global _settings_logged
    if _settings_logged:
        return
    _settings_logged = True

    # Use print for immediate visibility during startup
    print("\n" + "=" * 60)
    print("  Odin Configuration")
    print("=" * 60)
    print(f"  ENV_FILE: {_env_file_path}")
    print(f"  CWD: {Path.cwd()}")
    print("-" * 60)
    print(f"  LLM_PROVIDER: {settings.llm_provider}")
    print(f"  OPENAI_MODEL: {settings.openai_model}")
    print(f"  OPENAI_BASE_URL: {settings.openai_base_url or '(default)'}")
    print(f"  OPENAI_API_KEY: {'***' + settings.openai_api_key[-4:] if settings.openai_api_key else '(not set)'}")
    print("-" * 60)
    print(f"  AGENT_BACKEND: {settings.agent_backend}")
    print(f"  CHECKPOINTER: {settings.checkpointer_type}")
    print("=" * 60 + "\n")


def get_settings(reload: bool = False) -> Settings:
    """Get settings instance with optional hot reload.

    Args:
        reload: If True, reload settings from environment/file

    Returns:
        Settings instance (singleton by default)
    """
    global _settings_instance, _settings_logged

    if reload or _settings_instance is None:
        if reload:
            _settings_logged = False  # Re-log on reload
        _settings_instance = Settings()
        _log_settings(_settings_instance)

    return _settings_instance


def reload_settings() -> Settings:
    """Force reload settings from environment/file.

    Returns:
        Newly loaded Settings instance
    """
    return get_settings(reload=True)


# Auto-initialize settings on module import
settings = get_settings()
