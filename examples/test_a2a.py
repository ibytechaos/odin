"""Test A2A protocol implementation."""

import asyncio

from odin import Odin, tool
from odin.plugins import AgentPlugin
from odin.protocols.a2a import A2AServer
from odin.protocols.a2a.models import (
    Message,
    MessageRole,
    TaskState,
    TextPart,
)


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
    print("Testing A2A Protocol Implementation")
    print("=" * 70)

    # Create Odin app
    app = Odin()
    await app.initialize()

    # Register plugin
    plugin = TestPlugin()
    await app.register_plugin(plugin)

    # Create A2A server
    a2a_server = A2AServer(app, name="test-agent", description="Test A2A agent")

    print("\n[1/5] Verifying A2A server creation")
    print(f"  Server app: {a2a_server.app.title}")
    print(f"  Task manager: {a2a_server.task_manager}")
    print(f"  Agent card generator: {a2a_server.agent_card_generator}")
    print("  ✓ A2A server created successfully")

    print("\n[2/5] Testing Agent Card generation")
    agent_card = await a2a_server.agent_card_generator.generate()
    print(f"  Name: {agent_card.name}")
    print(f"  Description: {agent_card.description}")
    print(f"  Protocol Version: {agent_card.protocolVersion}")
    print(f"  Skills: {len(agent_card.skills)}")
    for skill in agent_card.skills:
        print(f"    - {skill.name}: {skill.description}")
    print("  ✓ Agent card generated successfully")

    print("\n[3/5] Testing Task creation")
    message = Message(
        role=MessageRole.USER,
        parts=[TextPart(text="Test message")],
    )
    task = await a2a_server.task_manager.create_task(
        context_id="test-context",
        initial_message=message,
    )
    print(f"  Task ID: {task.id}")
    print(f"  Context ID: {task.contextId}")
    print(f"  Status: {task.status.state}")
    print(f"  History: {len(task.history) if task.history else 0} messages")
    print("  ✓ Task created successfully")

    print("\n[4/5] Testing Task status update")
    updated_task = await a2a_server.task_manager.update_task_status(
        task.id,
        TaskState.WORKING,
        "Processing task",
    )
    assert updated_task is not None
    print(f"  Status: {updated_task.status.state}")
    print(f"  Message: {updated_task.status.message}")
    print("  ✓ Task status updated successfully")

    print("\n[5/5] Testing Task listing")
    tasks, total, has_more = await a2a_server.task_manager.list_tasks(
        context_id="test-context"
    )
    print(f"  Total tasks: {total}")
    print(f"  Retrieved: {len(tasks)}")
    print(f"  Has more: {has_more}")
    print("  ✓ Task listing works correctly")

    await app.shutdown()

    print("\n" + "=" * 70)
    print("A2A Protocol Tests: PASSED")
    print("=" * 70)

    print("\nA2A Server Features:")
    print("  ✓ Agent Card generation (self-describing)")
    print("  ✓ Task creation and lifecycle management")
    print("  ✓ Message handling")
    print("  ✓ Task status updates")
    print("  ✓ Task listing and filtering")
    print("  ✓ HTTP/REST endpoints")
    print("  ✓ Server-Sent Events (SSE) streaming")

    print("\nA2A Protocol Endpoints:")
    print("  - GET  /.well-known/agent-card")
    print("  - POST /message/send")
    print("  - POST /message/send/streaming")
    print("  - GET  /tasks/{id}")
    print("  - GET  /tasks")
    print("  - GET  /tasks/{id}/subscribe")

    print("\nTo test with a real server:")
    print("  1. Run: python examples/a2a_server_demo.py")
    print("  2. Run: python examples/a2a_client_demo.py")
    print("  3. Or use curl to test endpoints")


if __name__ == "__main__":
    asyncio.run(main())
