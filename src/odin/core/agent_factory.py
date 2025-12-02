"""Agent factory for creating agent instances based on configuration."""

import importlib
from typing import Any

from odin.config import Settings, get_settings
from odin.core.agent_interface import IAgent
from odin.core.llm_factory import create_llm
from odin.logging import get_logger

logger = get_logger(__name__)


class AgentFactory:
    """Factory for creating agent instances.

    This factory creates the appropriate agent backend (CrewAI, LangGraph, or custom)
    based on configuration settings.

    Example:
        ```python
        # Create agent from default config
        agent = AgentFactory.create_agent()

        # Create specific agent type
        agent = AgentFactory.create_agent(agent_type="crewai")

        # Create with custom settings
        settings = get_settings()
        settings.agent_backend = "langgraph"
        agent = AgentFactory.create_agent(settings=settings)
        ```
    """

    @staticmethod
    def create_agent(
        agent_type: str | None = None,
        settings: Settings | None = None,
        **kwargs: Any,
    ) -> IAgent:
        """Create agent instance based on configuration.

        Args:
            agent_type: Agent backend type (crewai, langgraph, custom).
                       If None, reads from settings.
            settings: Settings instance. If None, uses global settings.
            **kwargs: Additional arguments passed to agent constructor.

        Returns:
            IAgent instance

        Raises:
            ValueError: If agent type is unknown or configuration is invalid
            ImportError: If required dependencies are not installed
        """
        if settings is None:
            settings = get_settings()

        backend = agent_type or settings.agent_backend

        logger.info(
            "Creating agent",
            backend=backend,
            name=settings.agent_name,
        )

        if backend == "crewai":
            return AgentFactory._create_crewai_agent(settings, **kwargs)
        elif backend == "langgraph":
            return AgentFactory._create_langgraph_agent(settings, **kwargs)
        elif backend == "custom":
            return AgentFactory._create_custom_agent(settings, **kwargs)
        else:
            raise ValueError(
                f"Unknown agent backend: {backend}. "
                f"Must be one of: crewai, langgraph, custom"
            )

    @staticmethod
    def _create_crewai_agent(settings: Settings, **kwargs: Any) -> IAgent:
        """Create CrewAI agent backend.

        Args:
            settings: Settings instance
            **kwargs: Additional arguments

        Returns:
            CrewAIAgentBackend instance

        Raises:
            ImportError: If crewai is not installed
        """
        try:
            from odin.core.agent_backends.crewai_backend import CrewAIAgentBackend
        except ImportError as e:
            raise ImportError(
                "CrewAI is required for crewai backend. "
                "Install with: pip install crewai"
            ) from e

        # Create LLM
        llm = create_llm(settings)

        # Create agent
        agent = CrewAIAgentBackend(
            name=settings.agent_name,
            description=settings.agent_description,
            llm=llm,
            **kwargs,
        )

        logger.info(
            "CrewAI agent created",
            name=settings.agent_name,
            llm_provider=settings.llm_provider,
        )

        return agent

    @staticmethod
    def _create_langgraph_agent(settings: Settings, **kwargs: Any) -> IAgent:
        """Create LangGraph agent backend.

        Args:
            settings: Settings instance
            **kwargs: Additional arguments

        Returns:
            LangGraphAgentBackend instance

        Raises:
            ImportError: If langgraph is not installed
            NotImplementedError: LangGraph backend is not yet implemented
        """
        # TODO: Implement LangGraph backend
        raise NotImplementedError(
            "LangGraph backend is not yet implemented. "
            "Use 'crewai' backend for now. "
            "To implement: create LangGraphAgentBackend in agent_backends/"
        )

    @staticmethod
    def _create_custom_agent(settings: Settings, **kwargs: Any) -> IAgent:
        """Create custom agent backend.

        Loads a custom agent class from the path specified in settings.

        Args:
            settings: Settings instance
            **kwargs: Additional arguments

        Returns:
            Custom IAgent instance

        Raises:
            ValueError: If custom_agent_path is not set
            ImportError: If custom agent module cannot be loaded
            TypeError: If custom agent class doesn't implement IAgent
        """
        if not settings.custom_agent_path:
            raise ValueError(
                "custom_agent_path must be set in settings to use custom agent backend. "
                "Example: ODIN_CUSTOM_AGENT_PATH=my_agents.MyCustomAgent"
            )

        try:
            # Parse module and class name
            # Format: "module.path.ClassName"
            parts = settings.custom_agent_path.rsplit(".", 1)
            if len(parts) != 2:
                raise ValueError(
                    f"Invalid custom_agent_path format: {settings.custom_agent_path}. "
                    "Expected format: 'module.path.ClassName'"
                )

            module_path, class_name = parts

            # Import module
            logger.debug("Importing custom agent", module=module_path, class_name=class_name)
            module = importlib.import_module(module_path)

            # Get class
            agent_class = getattr(module, class_name)

            # Verify it implements IAgent
            if not issubclass(agent_class, IAgent):
                raise TypeError(
                    f"Custom agent class {class_name} must implement IAgent interface"
                )

            # Create instance
            agent = agent_class(
                name=settings.agent_name,
                description=settings.agent_description,
                **kwargs,
            )

            logger.info(
                "Custom agent created",
                class_name=class_name,
                name=settings.agent_name,
            )

            return agent

        except ImportError as e:
            raise ImportError(
                f"Failed to import custom agent from {settings.custom_agent_path}: {e}"
            ) from e
        except AttributeError as e:
            raise ImportError(
                f"Custom agent class not found in module: {e}"
            ) from e


def create_agent(agent_type: str | None = None, **kwargs: Any) -> IAgent:
    """Convenience function to create agent.

    This is a shorthand for AgentFactory.create_agent().

    Args:
        agent_type: Agent backend type (crewai, langgraph, custom)
        **kwargs: Additional arguments

    Returns:
        IAgent instance

    Example:
        ```python
        from odin.core.agent_factory import create_agent

        # Create default agent (from config)
        agent = create_agent()

        # Create specific type
        agent = create_agent(agent_type="crewai")
        ```
    """
    return AgentFactory.create_agent(agent_type=agent_type, **kwargs)
