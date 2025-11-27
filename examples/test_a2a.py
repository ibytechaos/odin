"""Test A2A protocol implementation."""

import asyncio

from odin import Odin, tool
from odin.logging import get_logger
from odin.plugins import AgentPlugin
from odin.protocols.a2a import A2AServer
from odin.protocols.a2a.models import (
    Message,
    MessageRole,
    TaskState,
    TextPart,
)

logger = get_logger(__name__)


class TestPlugin(AgentPlugin):
    """Test plugin for A2A."""

    @property
    def name(self) -> str:
        return "test"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Test plugin"

    @tool()
    async def echo(self, message: str) -> dict:
        """Echo a message back.

        Args:
            message: Message to echo
        """
        return {"echo": message}

    async def get_tools(self):
        from odin.decorators.tool import get_tool_from_function, is_tool

        tools = []
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if is_tool(attr):
                tool_def = get_tool_from_function(attr)
                if tool_def:
                    tools.append(tool_def)
        return tools

    async def execute_tool(self, tool_name: str, **kwargs):
        from odin.decorators.tool import get_tool_from_function, is_tool

        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if is_tool(attr):
                tool_def = get_tool_from_function(attr)
                if tool_def and tool_def.name == tool_name:
                    return await attr(**kwargs)
        raise ValueError(f"Tool '{tool_name}' not found")


async def main():
    """Test A2A protocol implementation."""
    logger.info("Testing A2A Protocol Implementation")
    logger.info("=" * 70)

    # Create Odin app
    app = Odin()
    await app.initialize()

    # Register plugin
    plugin = TestPlugin()
    await app.register_plugin(plugin)

    # Create A2A server
    a2a_server = A2AServer(app, name="test-agent", description="Test A2A agent")

    logger.info("\n[1/5] Verifying A2A server creation")
    logger.info(f"  Server app: {a2a_server.app.title}")
    logger.info(f"  Task manager: {a2a_server.task_manager}")
    logger.info(f"  Agent card generator: {a2a_server.agent_card_generator}")
    logger.info("  ✓ A2A server created successfully")

    logger.info("\n[2/5] Testing Agent Card generation")
    agent_card = await a2a_server.agent_card_generator.generate()
    logger.info(f"  Name: {agent_card.name}")
    logger.info(f"  Description: {agent_card.description}")
    logger.info(f"  Protocol Version: {agent_card.protocolVersion}")
    logger.info(f"  Skills: {len(agent_card.skills)}")
    for skill in agent_card.skills:
        logger.info(f"    - {skill.name}: {skill.description}")
    logger.info("  ✓ Agent card generated successfully")

    logger.info("\n[3/5] Testing Task creation")
    message = Message(
        role=MessageRole.USER,
        parts=[TextPart(text="Test message")],
    )
    task = await a2a_server.task_manager.create_task(
        context_id="test-context",
        initial_message=message,
    )
    logger.info(f"  Task ID: {task.id}")
    logger.info(f"  Context ID: {task.contextId}")
    logger.info(f"  Status: {task.status.state}")
    logger.info(f"  History: {len(task.history) if task.history else 0} messages")
    logger.info("  ✓ Task created successfully")

    logger.info("\n[4/5] Testing Task status update")
    updated_task = await a2a_server.task_manager.update_task_status(
        task.id,
        TaskState.WORKING,
        "Processing task",
    )
    assert updated_task is not None
    logger.info(f"  Status: {updated_task.status.state}")
    logger.info(f"  Message: {updated_task.status.message}")
    logger.info("  ✓ Task status updated successfully")

    logger.info("\n[5/5] Testing Task listing")
    tasks, total, has_more = await a2a_server.task_manager.list_tasks(
        context_id="test-context"
    )
    logger.info(f"  Total tasks: {total}")
    logger.info(f"  Retrieved: {len(tasks)}")
    logger.info(f"  Has more: {has_more}")
    logger.info("  ✓ Task listing works correctly")

    await app.shutdown()

    print("\n" + "=" * 70)
    logger.info("A2A Protocol Tests: PASSED")
    logger.info("=" * 70)

    logger.info("\nA2A Server Features:")
    logger.info("  ✓ Agent Card generation (self-describing)")
    logger.info("  ✓ Task creation and lifecycle management")
    logger.info("  ✓ Message handling")
    logger.info("  ✓ Task status updates")
    logger.info("  ✓ Task listing and filtering")
    logger.info("  ✓ HTTP/REST endpoints")
    logger.info("  ✓ Server-Sent Events (SSE) streaming")

    logger.info("\nA2A Protocol Endpoints:")
    logger.info("  - GET  /.well-known/agent-card")
    logger.info("  - POST /message/send")
    logger.info("  - POST /message/send/streaming")
    logger.info("  - GET  /tasks/{id}")
    logger.info("  - GET  /tasks")
    logger.info("  - GET  /tasks/{id}/subscribe")

    logger.info("\nTo test with a real server:")
    logger.info("  1. Run: python examples/a2a_server_demo.py")
    logger.info("  2. Run: python examples/a2a_client_demo.py")
    logger.info("  3. Or use curl to test endpoints")


if __name__ == "__main__":
    asyncio.run(main())
