"""CopilotKit adapter for Odin framework.

Converts Odin tools to CopilotKit actions and provides FastAPI integration
with a LangGraph-based agent using the AG-UI protocol.

References:
- https://docs.copilotkit.ai/coagents/langgraph/langgraph-python
- https://pypi.org/project/ag-ui-langgraph/
"""

import os
from typing import Any, Annotated

from fastapi import FastAPI

from odin.core.odin import Odin
from odin.logging import get_logger

logger = get_logger(__name__)


def create_odin_langgraph_agent(odin_app: Odin):
    """Create a LangGraph agent that uses Odin tools.

    Args:
        odin_app: Odin framework instance

    Returns:
        Compiled LangGraph StateGraph
    """
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import SystemMessage, ToolMessage
    from langgraph.graph import StateGraph, START, END
    from langgraph.graph.message import add_messages
    from typing import TypedDict
    import json

    # Create tools from Odin
    odin_tools = []

    for tool_def in odin_app.list_tools():
        tool_name = tool_def["name"]

        # Create LangChain tool using StructuredTool
        from langchain_core.tools import StructuredTool
        import asyncio

        # Wrapper to handle async execution
        def make_sync_wrapper(t_name):
            async def async_tool(**kwargs):
                result = await odin_app.execute_tool(t_name, **kwargs)
                return json.dumps(result) if isinstance(result, dict) else str(result)

            def sync_wrapper(**kwargs):
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        future = pool.submit(asyncio.run, async_tool(**kwargs))
                        return future.result()
                return asyncio.run(async_tool(**kwargs))

            return sync_wrapper

        lc_tool = StructuredTool.from_function(
            func=make_sync_wrapper(tool_name),
            name=tool_name,
            description=tool_def.get("description", ""),
            args_schema=None,
        )
        odin_tools.append(lc_tool)

    # Get LLM configuration from environment
    model = os.getenv("OPENAI_MODEL", "gpt-4o")
    base_url = os.getenv("OPENAI_BASE_URL")

    llm_kwargs = {"model": model}
    if base_url:
        llm_kwargs["base_url"] = base_url

    llm = ChatOpenAI(**llm_kwargs)

    # Bind tools to LLM
    if odin_tools:
        llm_with_tools = llm.bind_tools(odin_tools)
    else:
        llm_with_tools = llm

    # Define state
    class AgentState(TypedDict):
        messages: Annotated[list, add_messages]

    # Define the agent node
    def agent_node(state: AgentState):
        messages = state["messages"]

        # Add system message if not present
        if not messages or not isinstance(messages[0], SystemMessage):
            system_msg = SystemMessage(content="""You are a helpful AI assistant with access to various tools.
Use the available tools to help answer user questions about weather, calendar events, and data analytics.
Always be helpful and provide clear, concise responses.""")
            messages = [system_msg] + list(messages)

        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    # Define tool execution node
    def tool_node(state: AgentState):
        messages = state["messages"]
        last_message = messages[-1]

        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            return {"messages": []}

        tool_results = []
        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            try:
                import asyncio
                result = asyncio.run(odin_app.execute_tool(tool_name, **tool_args))
                result_str = json.dumps(result) if isinstance(result, dict) else str(result)
            except Exception as e:
                result_str = f"Error executing tool: {str(e)}"

            tool_results.append(
                ToolMessage(content=result_str, tool_call_id=tool_call["id"])
            )

        return {"messages": tool_results}

    # Define routing
    def should_continue(state: AgentState):
        messages = state["messages"]
        last_message = messages[-1]

        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return END

    # Build graph
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)

    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    return graph.compile()


class CopilotKitAdapter:
    """Adapter to expose Odin tools via CopilotKit/AG-UI protocol.

    This adapter creates a LangGraph agent with Odin tools and exposes it
    via the AG-UI protocol using ag_ui_langgraph.

    Example:
        ```python
        from fastapi import FastAPI
        from odin import Odin
        from odin.protocols.copilotkit import CopilotKitAdapter

        app = FastAPI()
        odin = Odin()
        await odin.initialize()
        await odin.register_plugin(MyPlugin())

        # Create adapter and mount endpoints
        adapter = CopilotKitAdapter(odin)
        adapter.mount(app, "/copilotkit")
        ```
    """

    def __init__(self, odin_app: Odin):
        """Initialize CopilotKit adapter.

        Args:
            odin_app: Odin framework instance
        """
        self.odin_app = odin_app
        self._graph = None
        self._agent = None

    def get_graph(self):
        """Get LangGraph agent graph.

        Returns:
            Compiled LangGraph StateGraph
        """
        if self._graph is None:
            self._graph = create_odin_langgraph_agent(self.odin_app)
            logger.info("LangGraph agent created")
        return self._graph

    def get_agent(self):
        """Get AG-UI LangGraph agent.

        Returns:
            LangGraphAgent instance from ag_ui_langgraph
        """
        try:
            from ag_ui_langgraph import LangGraphAgent
        except ImportError:
            raise ImportError(
                "ag-ui-langgraph package is required. Install with: pip install ag-ui-langgraph"
            )

        if self._agent is None:
            graph = self.get_graph()
            self._agent = LangGraphAgent(
                name="odin_agent",
                description="AI assistant powered by Odin framework with weather, calendar, and data tools",
                graph=graph,
            )
            logger.info("AG-UI LangGraphAgent created", agent="odin_agent")

        return self._agent

    def mount(self, app: FastAPI, path: str = "/copilotkit"):
        """Mount AG-UI endpoint on FastAPI app.

        This uses the official ag_ui_langgraph package to create the endpoint,
        which properly implements the AG-UI protocol for CopilotKit.

        Args:
            app: FastAPI application
            path: Endpoint path (default: "/copilotkit")
        """
        try:
            from ag_ui_langgraph import add_langgraph_fastapi_endpoint
        except ImportError:
            raise ImportError(
                "ag-ui-langgraph package is required. Install with: pip install ag-ui-langgraph"
            )

        agent = self.get_agent()
        add_langgraph_fastapi_endpoint(app, agent, path)

        logger.info(
            "AG-UI endpoint mounted",
            path=path,
            agent="odin_agent",
            tools=len(self.odin_app.list_tools()),
        )
