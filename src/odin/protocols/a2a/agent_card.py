"""Agent Card generation for A2A protocol."""

from odin.core.odin import Odin
from odin.logging import get_logger
from odin.protocols.a2a.models import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    ProviderInfo,
    SecurityScheme,
)

logger = get_logger(__name__)


class AgentCardGenerator:
    """Generates Agent Cards from Odin framework state."""

    def __init__(
        self,
        odin_app: Odin,
        agent_name: str,
        agent_description: str,
        provider_info: ProviderInfo | None = None,
    ):
        """Initialize agent card generator.

        Args:
            odin_app: Odin framework instance
            agent_name: Agent name
            agent_description: Agent description
            provider_info: Optional provider information
        """
        self.odin_app = odin_app
        self.agent_name = agent_name
        self.agent_description = agent_description
        self.provider_info = provider_info
        self._security_schemes: list[SecurityScheme] = []
        self._capabilities = AgentCapabilities(
            streaming=True,  # A2A server supports streaming
            pushNotifications=False,  # Not implemented yet
        )

    def add_security_scheme(self, scheme: SecurityScheme):
        """Add authentication scheme to agent card.

        Args:
            scheme: Security scheme to add
        """
        self._security_schemes.append(scheme)
        logger.info(
            "Security scheme added to agent card",
            type=scheme.type,
            scheme=scheme.scheme,
        )

    def set_capabilities(self, capabilities: AgentCapabilities):
        """Set agent capabilities.

        Args:
            capabilities: Agent capabilities
        """
        self._capabilities = capabilities

    async def generate(self) -> AgentCard:
        """Generate Agent Card from current Odin state.

        Returns:
            Generated Agent Card
        """
        # Extract skills from registered tools
        skills = await self._extract_skills_from_tools()

        agent_card = AgentCard(
            name=self.agent_name,
            description=self.agent_description,
            protocolVersion="1.0",
            capabilities=self._capabilities,
            securitySchemes=self._security_schemes,
            skills=skills,
            provider=self.provider_info,
            supportsAuthenticatedExtendedCard=False,  # Not implemented yet
            metadata={
                "odin_version": self.odin_app.version,
                "total_tools": len(self.odin_app.list_tools()),
            },
        )

        logger.info(
            "Agent card generated",
            name=agent_card.name,
            skills=len(agent_card.skills),
            security_schemes=len(agent_card.securitySchemes),
        )

        return agent_card

    async def _extract_skills_from_tools(self) -> list[AgentSkill]:
        """Extract agent skills from registered tools.

        Returns:
            List of agent skills
        """
        skills = []
        tools = self.odin_app.list_tools()

        # Group tools by plugin to create skill categories
        plugin_tools: dict[str, list[dict]] = {}
        for tool in tools:
            plugin_name = tool.get("plugin", "unknown")
            if plugin_name not in plugin_tools:
                plugin_tools[plugin_name] = []
            plugin_tools[plugin_name].append(tool)

        # Create a skill for each plugin
        for plugin_name, tools_list in plugin_tools.items():
            # Get plugin info
            plugin_info = None
            for plugin_dict in self.odin_app.list_plugins():
                if plugin_dict["name"] == plugin_name:
                    plugin_info = plugin_dict
                    break

            # Create skill description
            tool_names = [t["name"] for t in tools_list]
            skill_description = (
                plugin_info["description"]
                if plugin_info
                else f"Tools: {', '.join(tool_names)}"
            )

            # Create examples from tool descriptions
            examples = []
            for tool in tools_list[:3]:  # Limit to first 3 tools
                example = f"{tool['name']}: {tool['description']}"
                examples.append(example)

            skill = AgentSkill(
                name=plugin_name,
                description=skill_description,
                examples=examples if examples else None,
                metadata={
                    "tool_count": len(tools_list),
                    "tools": tool_names,
                },
            )
            skills.append(skill)

        return skills


def create_default_agent_card(
    odin_app: Odin,
    name: str | None = None,
    description: str | None = None,
) -> AgentCardGenerator:
    """Create a default agent card generator with sensible defaults.

    Args:
        odin_app: Odin framework instance
        name: Optional agent name (defaults to "odin-agent")
        description: Optional description

    Returns:
        Configured agent card generator
    """
    generator = AgentCardGenerator(
        odin_app=odin_app,
        agent_name=name or "odin-agent",
        agent_description=description or "AI agent powered by Odin framework",
        provider_info=ProviderInfo(
            organization="Odin Framework",
            url="https://github.com/yourusername/odin",
        ),
    )

    # Add API key authentication by default
    generator.add_security_scheme(
        SecurityScheme(
            type="apiKey",
            name="X-API-Key",
            in_="header",
        )
    )

    return generator
