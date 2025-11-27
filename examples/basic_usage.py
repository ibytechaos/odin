"""Basic usage example for Odin framework.

This example demonstrates:
1. Initializing the Odin framework
2. Registering the CrewAI plugin
3. Creating agents, tasks, and crews
4. Executing a simple crew workflow
"""

import asyncio

from odin import Odin
from odin.plugins.crewai import CrewAIPlugin


async def main() -> None:
    """Run basic Odin example."""
    # Initialize Odin framework
    app = Odin()
    await app.initialize()

    # Register CrewAI plugin
    crewai_plugin = CrewAIPlugin()
    await app.register_plugin(crewai_plugin)

    print("\n=== Registered Plugins ===")
    for plugin in app.list_plugins():
        print(f"- {plugin['name']} v{plugin['version']}: {plugin['description']}")
        print(f"  Tools: {plugin['tools']}")

    print("\n=== Available Tools ===")
    for tool in app.list_tools():
        print(f"- {tool['name']}: {tool['description']}")

    print("\n=== Creating Research Crew ===")

    # Create a researcher agent
    result = await app.execute_tool(
        "create_agent",
        agent_id="researcher",
        role="Senior Research Analyst",
        goal="Uncover cutting-edge developments in AI and data science",
        backstory="You are an expert at analyzing complex topics and providing comprehensive insights.",
    )
    print(f"Created agent: {result}")

    # Create a writer agent
    result = await app.execute_tool(
        "create_agent",
        agent_id="writer",
        role="Tech Content Writer",
        goal="Craft compelling content on tech advancements",
        backstory="You are a skilled writer who transforms complex technical topics into engaging narratives.",
    )
    print(f"Created agent: {result}")

    # Create research task
    result = await app.execute_tool(
        "create_task",
        task_id="research_task",
        description="Research the latest developments in large language models in 2024",
        agent_id="researcher",
        expected_output="A detailed report on LLM advancements",
    )
    print(f"Created task: {result}")

    # Create writing task
    result = await app.execute_tool(
        "create_task",
        task_id="writing_task",
        description="Write a blog post based on the research findings",
        agent_id="writer",
        expected_output="An engaging 500-word blog post",
    )
    print(f"Created task: {result}")

    # Create crew
    result = await app.execute_tool(
        "create_crew",
        crew_id="research_crew",
        agent_ids=["researcher", "writer"],
        task_ids=["research_task", "writing_task"],
    )
    print(f"Created crew: {result}")

    print("\n=== Executing Crew ===")
    print("Note: This will make LLM API calls and may take a minute...")

    # Execute the crew
    # Uncomment the following lines if you have LLM API keys configured
    # result = await app.execute_tool(
    #     "execute_crew",
    #     crew_id="research_crew",
    # )
    # print(f"\nCrew result:\n{result['result']}")

    print("\n=== Listing Resources ===")
    agents = await app.execute_tool("list_agents")
    print(f"Agents: {agents}")

    tasks = await app.execute_tool("list_tasks")
    print(f"Tasks: {tasks}")

    crews = await app.execute_tool("list_crews")
    print(f"Crews: {crews}")

    # Cleanup
    await app.shutdown()
    print("\n=== Odin framework shut down successfully ===")


if __name__ == "__main__":
    asyncio.run(main())
