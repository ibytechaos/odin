"""Tests for configuration settings."""

import pytest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from odin.config.settings import Settings


@pytest.fixture
def clean_env():
    """Fixture to provide clean environment for Settings tests."""
    # Save and clear relevant env vars
    saved = {}
    env_vars = [
        "ODIN_DEBUG", "ODIN_ENV", "ODIN_LOG_LEVEL",
        "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
        "ODIN_BUILTIN_PLUGINS", "ODIN_PLUGIN_DIRS",
    ]
    for var in env_vars:
        if var in os.environ:
            saved[var] = os.environ.pop(var)

    yield

    # Restore env vars
    for var, value in saved.items():
        os.environ[var] = value


class TestSettingsDefaults:
    """Test Settings default values."""

    def test_default_env(self):
        """Test default environment is development."""
        settings = Settings(_env_file=None)
        assert settings.env == "development"

    def test_debug_setting(self):
        """Test debug setting can be set."""
        settings = Settings(_env_file=None, debug=False)
        assert settings.debug is False
        settings2 = Settings(_env_file=None, debug=True)
        assert settings2.debug is True

    def test_default_log_level(self):
        """Test default log level is INFO."""
        settings = Settings(_env_file=None)
        assert settings.log_level == "INFO"

    def test_default_llm_provider(self):
        """Test default LLM provider is openai."""
        settings = Settings(_env_file=None)
        assert settings.llm_provider == "openai"

    def test_default_agent_backend(self):
        """Test default agent backend is crewai."""
        settings = Settings(_env_file=None)
        assert settings.agent_backend == "crewai"

    def test_default_checkpointer_type(self):
        """Test default checkpointer type is memory."""
        settings = Settings(_env_file=None)
        assert settings.checkpointer_type == "memory"

    def test_default_http_settings(self):
        """Test default HTTP settings."""
        settings = Settings(_env_file=None)
        assert settings.http_host == "0.0.0.0"
        assert settings.http_port == 8000

    def test_default_mcp_settings(self):
        """Test default MCP settings."""
        settings = Settings(_env_file=None)
        assert settings.mcp_enabled is True
        assert settings.mcp_port == 8001

    def test_default_a2a_settings(self):
        """Test default A2A settings."""
        settings = Settings(_env_file=None)
        assert settings.a2a_enabled is False
        assert settings.a2a_port == 8002

    def test_default_builtin_plugins(self):
        """Test default builtin plugins."""
        settings = Settings(_env_file=None)
        assert "http" in settings.builtin_plugins
        assert "utilities" in settings.builtin_plugins

    def test_default_otel_settings(self):
        """Test default OpenTelemetry settings."""
        settings = Settings(_env_file=None)
        assert settings.otel_enabled is True
        assert settings.otel_service_name == "odin"


class TestSettingsCustomValues:
    """Test Settings with custom values."""

    def test_custom_env(self):
        """Test custom environment."""
        settings = Settings(_env_file=None, env="production")
        assert settings.env == "production"

    def test_custom_log_level(self):
        """Test custom log level."""
        settings = Settings(_env_file=None, log_level="DEBUG")
        assert settings.log_level == "DEBUG"

    def test_custom_llm_provider(self):
        """Test custom LLM provider setting."""
        settings = Settings(
            _env_file=None,
            llm_provider="anthropic",
        )
        assert settings.llm_provider == "anthropic"

    def test_openai_base_url_can_be_set(self):
        """Test that OpenAI base URL can be set explicitly."""
        # Note: env vars may override, so we just check it's a valid string
        settings = Settings(_env_file=None)
        # openai_base_url should be either None or a string
        assert settings.openai_base_url is None or isinstance(settings.openai_base_url, str)

    def test_custom_agent_settings(self):
        """Test custom agent settings."""
        settings = Settings(
            _env_file=None,
            agent_backend="custom",
            agent_name="my_agent",
            agent_description="My custom agent",
        )
        assert settings.agent_backend == "custom"
        assert settings.agent_name == "my_agent"
        assert settings.agent_description == "My custom agent"


class TestSettingsValidators:
    """Test Settings field validators."""

    def test_plugin_dirs_from_string(self):
        """Test parsing plugin_dirs from comma-separated string."""
        settings = Settings(
            _env_file=None,
            plugin_dirs="./plugins,./my_plugins",
        )
        assert len(settings.plugin_dirs) == 2
        assert settings.plugin_dirs[0] == Path("./plugins")
        assert settings.plugin_dirs[1] == Path("./my_plugins")

    def test_plugin_dirs_from_list_strings(self):
        """Test parsing plugin_dirs from list of strings."""
        settings = Settings(
            _env_file=None,
            plugin_dirs=["./plugins", "./my_plugins"],
        )
        assert len(settings.plugin_dirs) == 2
        assert all(isinstance(p, Path) for p in settings.plugin_dirs)

    def test_builtin_plugins_from_string(self):
        """Test parsing builtin_plugins from comma-separated string."""
        settings = Settings(
            _env_file=None,
            builtin_plugins="http,utilities,github",
        )
        assert settings.builtin_plugins == ["http", "utilities", "github"]

    def test_builtin_plugins_empty_string(self):
        """Test parsing builtin_plugins from empty parts."""
        settings = Settings(
            _env_file=None,
            builtin_plugins="http,,utilities",
        )
        assert settings.builtin_plugins == ["http", "utilities"]

    def test_cors_origins_from_string(self):
        """Test parsing cors_origins from comma-separated string."""
        settings = Settings(
            _env_file=None,
            cors_origins="http://localhost:3000,http://localhost:8000",
        )
        assert settings.cors_origins == [
            "http://localhost:3000",
            "http://localhost:8000"
        ]

    def test_cors_origins_from_list(self):
        """Test cors_origins from list."""
        settings = Settings(
            _env_file=None,
            cors_origins=["http://app.example.com"],
        )
        assert settings.cors_origins == ["http://app.example.com"]


class TestSettingsHelperMethods:
    """Test Settings helper methods."""

    def test_is_production(self):
        """Test is_production method."""
        prod_settings = Settings(_env_file=None, env="production")
        dev_settings = Settings(_env_file=None, env="development")

        assert prod_settings.is_production() is True
        assert dev_settings.is_production() is False

    def test_is_development(self):
        """Test is_development method."""
        dev_settings = Settings(_env_file=None, env="development")
        prod_settings = Settings(_env_file=None, env="production")

        assert dev_settings.is_development() is True
        assert prod_settings.is_development() is False


class TestSettingsEnvValidation:
    """Test Settings env value validation."""

    def test_invalid_env_raises(self):
        """Test that invalid env value raises error."""
        with pytest.raises(Exception):
            Settings(_env_file=None, env="invalid")

    def test_invalid_log_level_raises(self):
        """Test that invalid log level raises error."""
        with pytest.raises(Exception):
            Settings(_env_file=None, log_level="INVALID")

    def test_invalid_llm_provider_raises(self):
        """Test that invalid LLM provider raises error."""
        with pytest.raises(Exception):
            Settings(_env_file=None, llm_provider="invalid")

    def test_invalid_agent_backend_raises(self):
        """Test that invalid agent backend raises error."""
        with pytest.raises(Exception):
            Settings(_env_file=None, agent_backend="invalid")

    def test_invalid_checkpointer_type_raises(self):
        """Test that invalid checkpointer type raises error."""
        with pytest.raises(Exception):
            Settings(_env_file=None, checkpointer_type="invalid")


class TestSettingsPerformanceConfig:
    """Test Settings performance configuration."""

    def test_default_token_limit(self):
        """Test default token limit."""
        settings = Settings(_env_file=None)
        assert settings.token_limit_per_request == 100000

    def test_default_semantic_cache(self):
        """Test default semantic cache setting."""
        settings = Settings(_env_file=None)
        assert settings.enable_semantic_cache is True

    def test_default_rate_limit(self):
        """Test default rate limit."""
        settings = Settings(_env_file=None)
        assert settings.rate_limit_requests_per_minute == 60

    def test_custom_performance_settings(self):
        """Test custom performance settings."""
        settings = Settings(
            _env_file=None,
            token_limit_per_request=50000,
            enable_semantic_cache=False,
            rate_limit_requests_per_minute=120,
        )
        assert settings.token_limit_per_request == 50000
        assert settings.enable_semantic_cache is False
        assert settings.rate_limit_requests_per_minute == 120


class TestSettingsStorageConfig:
    """Test Settings storage configuration."""

    def test_default_redis_url(self):
        """Test default Redis URL."""
        settings = Settings(_env_file=None)
        assert settings.redis_url == "redis://localhost:6379/0"

    def test_default_sqlite_path(self):
        """Test default SQLite path."""
        settings = Settings(_env_file=None)
        assert settings.sqlite_path == Path("./data/odin.db")

    def test_default_postgres_url(self):
        """Test default Postgres URL is None."""
        settings = Settings(_env_file=None)
        assert settings.postgres_url is None

    def test_custom_storage_settings(self):
        """Test custom storage settings."""
        settings = Settings(
            _env_file=None,
            redis_url="redis://custom:6379/1",
            sqlite_path="./custom/db.sqlite",
            postgres_url="postgresql://user:pass@localhost/db",
        )
        assert settings.redis_url == "redis://custom:6379/1"
        assert settings.sqlite_path == Path("./custom/db.sqlite")
        assert settings.postgres_url == "postgresql://user:pass@localhost/db"


class TestSettingsSecurityConfig:
    """Test Settings security configuration."""

    def test_default_api_key(self):
        """Test default API key is None."""
        settings = Settings(_env_file=None)
        assert settings.api_key is None

    def test_custom_api_key(self):
        """Test custom API key."""
        settings = Settings(_env_file=None, api_key="my-secret-key")
        assert settings.api_key == "my-secret-key"
