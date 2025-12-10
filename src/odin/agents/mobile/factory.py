"""Factory for creating mobile agents."""

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from openai import AsyncOpenAI

    from odin.agents.mobile.base import MobileAgentBase
    from odin.plugins.builtin.mobile.controllers.base import BaseController
    from odin.plugins.builtin.mobile.interaction import HumanInteractionHandler

from odin.agents.mobile.hierarchical import MobileHierarchicalAgent
from odin.agents.mobile.plan_execute import MobilePlanExecuteAgent
from odin.agents.mobile.react import MobileReActAgent
from odin.plugins.builtin.mobile.controllers.adb import ADBConfig, ADBController
from odin.plugins.builtin.mobile.interaction import (
    CLIInteractionHandler,
    NoOpInteractionHandler,
)
from odin.plugins.builtin.mobile.plugin import MobilePlugin

AgentMode = Literal["react", "plan_execute", "hierarchical"]
ControllerType = Literal["adb", "hdc", "ios"]
InteractionType = Literal["cli", "gui", "callback", "noop"]


def create_controller(
    controller_type: ControllerType = "adb",
    device_id: str | None = None,
    adb_path: str = "adb",
    hdc_path: str = "hdc",  # noqa: ARG001
) -> BaseController:
    """Create a device controller.

    Args:
        controller_type: Type of controller (adb, hdc, ios)
        device_id: Device serial number
        adb_path: Path to adb executable
        hdc_path: Path to hdc executable (for future HDC support)

    Returns:
        Configured controller instance

    Raises:
        ValueError: If controller type is not supported
    """
    if controller_type == "adb":
        config = ADBConfig(device_id=device_id, adb_path=adb_path)
        return ADBController(config)
    elif controller_type == "hdc":
        raise NotImplementedError("HDC controller not yet implemented")
    elif controller_type == "ios":
        raise NotImplementedError("iOS controller not yet implemented")
    else:
        raise ValueError(f"Unknown controller type: {controller_type}")


def create_interaction_handler(
    interaction_type: InteractionType = "cli",
) -> HumanInteractionHandler:
    """Create an interaction handler.

    Args:
        interaction_type: Type of interaction handler

    Returns:
        Configured interaction handler
    """
    if interaction_type == "cli":
        return CLIInteractionHandler()
    elif interaction_type == "noop":
        return NoOpInteractionHandler()
    elif interaction_type == "gui":
        raise NotImplementedError("GUI interaction handler not yet implemented")
    elif interaction_type == "callback":
        raise NotImplementedError("Callback handler requires custom setup")
    else:
        return NoOpInteractionHandler()


def create_mobile_plugin(
    controller: BaseController | None = None,
    interaction_handler: HumanInteractionHandler | None = None,
    tool_delay_ms: int = 400,
) -> MobilePlugin:
    """Create a mobile plugin.

    Args:
        controller: Device controller (optional, can be set later)
        interaction_handler: Interaction handler
        tool_delay_ms: Delay after each tool execution

    Returns:
        Configured MobilePlugin instance
    """
    return MobilePlugin(
        controller=controller,
        interaction_handler=interaction_handler,
        tool_delay_ms=tool_delay_ms,
    )


def create_mobile_agent(
    mode: AgentMode = "react",
    plugin: MobilePlugin | None = None,
    llm_client: AsyncOpenAI | None = None,
    vlm_client: AsyncOpenAI | None = None,
    llm_model: str = "gpt-4o",
    vlm_model: str = "gpt-4o",
    max_rounds: int = 50,
    **kwargs,
) -> MobileAgentBase:
    """Create a mobile agent with specified mode.

    Args:
        mode: Agent mode (react, plan_execute, hierarchical)
        plugin: MobilePlugin instance (required)
        llm_client: OpenAI-compatible client for LLM
        vlm_client: OpenAI-compatible client for VLM (defaults to llm_client)
        llm_model: Model name for text generation
        vlm_model: Model name for vision
        max_rounds: Maximum execution rounds
        **kwargs: Additional arguments passed to agent constructor

    Returns:
        Configured mobile agent instance

    Raises:
        ValueError: If plugin or llm_client not provided
    """
    if plugin is None:
        raise ValueError("plugin is required")
    if llm_client is None:
        raise ValueError("llm_client is required")

    common_args = {
        "plugin": plugin,
        "llm_client": llm_client,
        "vlm_client": vlm_client,
        "llm_model": llm_model,
        "vlm_model": vlm_model,
        "max_rounds": max_rounds,
    }

    if mode == "react":
        return MobileReActAgent(**common_args, **kwargs)
    elif mode == "plan_execute":
        return MobilePlanExecuteAgent(**common_args, **kwargs)
    elif mode == "hierarchical":
        return MobileHierarchicalAgent(**common_args, **kwargs)
    else:
        raise ValueError(f"Unknown agent mode: {mode}")


def create_mobile_agent_from_settings(
    llm_client: AsyncOpenAI,
    vlm_client: AsyncOpenAI | None = None,
) -> MobileAgentBase:
    """Create a mobile agent from Odin settings.

    Args:
        llm_client: OpenAI-compatible client for LLM
        vlm_client: Optional VLM client (defaults to llm_client)

    Returns:
        Configured mobile agent based on settings
    """
    from odin.config.settings import get_settings

    settings = get_settings()

    # Create controller
    controller = create_controller(
        controller_type=settings.mobile_controller,
        device_id=settings.mobile_device_id,
        adb_path=settings.mobile_adb_path,
        hdc_path=settings.mobile_hdc_path,
    )

    # Create interaction handler
    interaction_handler = create_interaction_handler(settings.mobile_interaction)

    # Create plugin
    plugin = create_mobile_plugin(
        controller=controller,
        interaction_handler=interaction_handler,
        tool_delay_ms=settings.mobile_tool_delay_ms,
    )

    # Create agent
    return create_mobile_agent(
        mode=settings.mobile_agent_mode,
        plugin=plugin,
        llm_client=llm_client,
        vlm_client=vlm_client,
        max_rounds=settings.mobile_max_rounds,
    )
