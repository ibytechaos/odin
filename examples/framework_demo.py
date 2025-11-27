"""Simple framework demonstration without LLM dependencies.

This example demonstrates core Odin capabilities:
1. Plugin registration
2. Tool discovery and listing
3. Tool execution
4. Framework lifecycle management
"""

import asyncio

from odin import Odin
from odin.plugins.crewai import CrewAIPlugin


async def main() -> None:
    """Run framework demonstration."""
    print("=" * 60)
    print("Odin Agent Framework - Demonstration")
    print("=" * 60)

    # Initialize Odin framework
    print("\n[1/4] Initializing framework...")
    app = Odin()
    await app.initialize()
    print("✓ Framework initialized successfully")

    # Register CrewAI plugin
    print("\n[2/4] Registering CrewAI plugin...")
    crewai_plugin = CrewAIPlugin()
    await app.register_plugin(crewai_plugin)
    print("✓ CrewAI plugin registered")

    # List registered plugins
    print("\n[3/4] Registered plugins:")
    for idx, plugin in enumerate(app.list_plugins(), 1):
        print(f"  {idx}. {plugin['name']} v{plugin['version']}")
        print(f"     Description: {plugin['description']}")
        print(f"     Status: {'✓ Initialized' if plugin['initialized'] else '✗ Not initialized'}")
        print(f"     Tools: {plugin['tools']}")

    # List available tools
    print("\n[4/4] Available tools:")
    tools = app.list_tools()
    print(f"  Total tools available: {len(tools)}")
    for idx, tool in enumerate(tools, 1):
        print(f"\n  {idx}. {tool['name']}")
        print(f"     {tool['description']}")
        if tool['parameters']:
            print(f"     Parameters:")
            for param in tool['parameters']:
                required = " (required)" if param['required'] else ""
                print(f"       - {param['name']}: {param['type']}{required}")
                print(f"         {param['description']}")

    # Demonstrate tool execution (without LLM calls)
    print("\n" + "=" * 60)
    print("Tool Execution Examples")
    print("=" * 60)

    # List agents (should be empty initially)
    result = await app.execute_tool("list_agents")
    print(f"\n1. List agents: {result}")

    result = await app.execute_tool("list_tasks")
    print(f"2. List tasks: {result}")

    result = await app.execute_tool("list_crews")
    print(f"3. List crews: {result}")

    # Cleanup
    print("\n" + "=" * 60)
    await app.shutdown()
    print("✓ Framework shut down successfully")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
