"""Application configuration for Odin agents.

Defines the app.yaml configuration schema for agent applications.
"""

from enum import Enum
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field


class ProtocolType(str, Enum):
    """Supported protocol types."""

    AGUI = "ag-ui"  # For frontend (CopilotKit compatible)
    A2A = "a2a"  # For agent-to-agent
    MCP = "mcp"  # For Claude Desktop
    HTTP = "http"  # Raw HTTP/REST


class AgentEngineType(str, Enum):
    """Supported agent engine types."""

    CREWAI = "crewai"
    LANGGRAPH = "langgraph"
    CUSTOM = "custom"  # Direct LLM calls


class ProtocolConfig(BaseModel):
    """Protocol endpoint configuration."""

    type: ProtocolType
    enabled: bool = True
    path: str = "/"
    port: int | None = None  # If None, uses main server port


class AgentEngineConfig(BaseModel):
    """Agent engine configuration."""

    type: AgentEngineType
    config: dict[str, Any] = Field(default_factory=dict)


class LLMConfig(BaseModel):
    """LLM provider configuration."""

    provider: Literal["openai", "anthropic", "azure", "local"]
    model: str
    api_key_env: str = "OPENAI_API_KEY"  # Environment variable name
    temperature: float = 0.7
    max_tokens: int | None = None


class ToolConfig(BaseModel):
    """Tool configuration."""

    name: str
    enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)


class PluginConfig(BaseModel):
    """Plugin configuration."""

    name: str
    enabled: bool = True
    module: str  # Python module path
    config: dict[str, Any] = Field(default_factory=dict)


class ServerConfig(BaseModel):
    """Server configuration."""

    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])


class AppConfig(BaseModel):
    """Main application configuration.

    Example app.yaml:
    ```yaml
    name: my-agent
    description: My AI Assistant
    version: "1.0.0"

    server:
      host: "0.0.0.0"
      port: 8000
      cors_origins:
        - "http://localhost:3000"

    protocols:
      - type: ag-ui
        enabled: true
        path: /
      - type: a2a
        enabled: true
        path: /a2a
      - type: mcp
        enabled: false

    agent:
      type: crewai
      config:
        verbose: true

    llm:
      provider: openai
      model: gpt-4
      api_key_env: OPENAI_API_KEY

    plugins:
      - name: weather
        module: odin.plugins.weather
        enabled: true
      - name: calendar
        module: odin.plugins.calendar
        enabled: true
    ```
    """

    name: str
    description: str = ""
    version: str = "1.0.0"

    server: ServerConfig = Field(default_factory=ServerConfig)
    protocols: list[ProtocolConfig] = Field(default_factory=list)
    agent: AgentEngineConfig | None = None
    llm: LLMConfig | None = None
    plugins: list[PluginConfig] = Field(default_factory=list)
    tools: list[ToolConfig] = Field(default_factory=list)

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "AppConfig":
        """Load configuration from YAML file.

        Args:
            path: Path to YAML file

        Returns:
            Parsed AppConfig
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path) as f:
            data = yaml.safe_load(f)

        return cls(**data)

    def to_yaml(self, path: str | Path) -> None:
        """Save configuration to YAML file.

        Args:
            path: Path to YAML file
        """
        path = Path(path)
        data = self.model_dump(exclude_none=True)

        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def get_enabled_protocols(self) -> list[ProtocolConfig]:
        """Get list of enabled protocols.

        Returns:
            List of enabled protocol configurations
        """
        return [p for p in self.protocols if p.enabled]

    def get_enabled_plugins(self) -> list[PluginConfig]:
        """Get list of enabled plugins.

        Returns:
            List of enabled plugin configurations
        """
        return [p for p in self.plugins if p.enabled]


def load_app_config(path: str | Path = "app.yaml") -> AppConfig:
    """Load application configuration.

    Args:
        path: Path to config file (default: app.yaml)

    Returns:
        Parsed AppConfig
    """
    return AppConfig.from_yaml(path)
