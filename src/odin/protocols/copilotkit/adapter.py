"""CopilotKit adapter for Odin framework.

Converts Odin tools to CopilotKit actions and provides FastAPI integration
with a LangGraph-based agent.

Note: CopilotKit has a design issue where:
1. CopilotKitRemoteEndpoint requires LangGraphAGUIAgent (raises error for LangGraphAgent)
2. LangGraphAGUIAgent inherits from ag_ui_langgraph.LangGraphAgent which only has run() method
3. But CopilotKitRemoteEndpoint.execute_agent() calls agent.execute()

We work around this by creating OdinLangGraphAgent that:
- Inherits from LangGraphAGUIAgent to pass SDK validation
- Adds execute() method that bridges to parent's functionality
- Also adds dict_repr() and get_state() methods for SDK compatibility
"""


import uuid
from typing import TYPE_CHECKING, Annotated, Any

from odin.logging import get_logger

if TYPE_CHECKING:
    from fastapi import FastAPI

    from odin.core.odin import Odin

logger = get_logger(__name__)


class OdinLangGraphAgent:
    """Custom LangGraph agent wrapper for CopilotKit compatibility.

    This class wraps a LangGraph compiled graph and provides the interface
    expected by CopilotKit SDK, specifically:
    - execute() method for running the agent
    - dict_repr() method for info endpoint
    - get_state() method for state retrieval

    We don't inherit from LangGraphAGUIAgent because:
    1. ag_ui_langgraph has Python 3.14 compatibility issues with Pydantic aliases
    2. LangGraphAGUIAgent.run() expects RunAgentInput Pydantic model which fails validation

    Instead, we implement the execute() interface directly using LangGraph's native API.
    """

    def __init__(self, name: str, description: str, graph: Any):
        self.name = name
        self.description = description
        self.graph = graph
        self._thread_states = {}

    def dict_repr(self) -> dict:
        """Return dictionary representation for CopilotKit info endpoint."""
        return {
            "name": self.name,
            "description": self.description or "",
            "type": "langgraph",
        }

    async def get_state(self, *, thread_id: str) -> dict:
        """Get agent state for a thread."""
        if not thread_id:
            return {
                "threadId": "",
                "threadExists": False,
                "state": {},
                "messages": []
            }

        try:
            from langchain_core.runnables import ensure_config
            config = ensure_config({})
            config["configurable"] = {"thread_id": thread_id}

            state = await self.graph.aget_state(config)
            if not state or not state.values:
                return {
                    "threadId": thread_id,
                    "threadExists": False,
                    "state": {},
                    "messages": []
                }

            messages = self._convert_messages_to_copilotkit(state.values.get("messages", []))
            state_copy = dict(state.values)
            state_copy.pop("messages", None)

            return {
                "threadId": thread_id,
                "threadExists": True,
                "state": state_copy,
                "messages": messages
            }
        except Exception as e:
            logger.error("Failed to get agent state", error=str(e))
            return {
                "threadId": thread_id,
                "threadExists": False,
                "state": {},
                "messages": []
            }

    def _convert_messages_to_copilotkit(self, messages: list) -> list:
        """Convert LangChain messages to CopilotKit format."""
        result = []
        for msg in messages:
            msg_dict = {
                "id": getattr(msg, "id", str(uuid.uuid4())),
                "role": getattr(msg, "type", "assistant"),
                "content": getattr(msg, "content", ""),
            }
            # Map LangChain message types to CopilotKit roles
            if msg_dict["role"] == "human":
                msg_dict["role"] = "user"
            elif msg_dict["role"] == "ai":
                msg_dict["role"] = "assistant"
            result.append(msg_dict)
        return result

    def _convert_copilotkit_messages_to_langchain(self, messages: list) -> list:
        """Convert CopilotKit messages to LangChain format."""
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        result = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            msg_id = msg.get("id", str(uuid.uuid4()))

            if role == "user":
                result.append(HumanMessage(content=content, id=msg_id))
            elif role == "assistant":
                result.append(AIMessage(content=content, id=msg_id))
            elif role == "system":
                result.append(SystemMessage(content=content, id=msg_id))
            else:
                # Default to human message for unknown roles
                result.append(HumanMessage(content=content, id=msg_id))

        return result

    def execute(
        self,
        *,
        thread_id: str,
        state: dict,
        messages: list[dict],
        actions: list[dict] | None = None,
        config: dict | None = None,
        meta_events: list[dict] | None = None,
        **kwargs
    ):
        """Execute the agent and yield streaming events.

        This method is called by CopilotKitRemoteEndpoint.execute_agent().
        It converts CopilotKit messages to LangChain format and runs the graph.
        """
        return self._stream_events(
            thread_id=thread_id,
            state=state,
            messages=messages,
            actions=actions,
            config=config,
            **kwargs
        )

    async def _stream_events(
        self,
        *,
        thread_id: str,
        state: dict,
        messages: list[dict],
        actions: list[dict] | None = None,
        config: dict | None = None,
        **kwargs
    ):
        """Stream events from graph execution."""
        from langchain_core.load import dumps as langchain_dumps
        from langchain_core.runnables import ensure_config

        # Setup config
        run_config = ensure_config(config or {})
        run_config["configurable"] = run_config.get("configurable", {})
        run_config["configurable"]["thread_id"] = thread_id or str(uuid.uuid4())

        # Convert messages to LangChain format
        langchain_messages = self._convert_copilotkit_messages_to_langchain(messages)

        # Prepare input state
        input_state = {
            **state,
            "messages": langchain_messages,
        }

        # Get current graph state
        current_state = {}
        node_name = kwargs.get("node_name")

        try:
            agent_state = await self.graph.aget_state(run_config)
            if agent_state and agent_state.values:
                current_state = dict(agent_state.values)
                # Merge new messages with existing
                existing_messages = current_state.get("messages", [])
                existing_ids = {getattr(m, "id", None) for m in existing_messages}
                new_messages = [m for m in langchain_messages if getattr(m, "id", None) not in existing_ids]
                input_state["messages"] = new_messages
        except Exception as e:
            logger.debug("No existing state", error=str(e))

        # Stream events from graph
        try:
            async for event in self.graph.astream_events(input_state, run_config, version="v2"):
                event_type = event.get("event")
                current_node = event.get("name")

                # Track node name
                if current_node and current_node in self.graph.nodes:
                    node_name = current_node

                # Update current state from chain_end events
                if event_type == "on_chain_end":
                    output = event.get("data", {}).get("output")
                    if isinstance(output, dict):
                        current_state.update(output)

                # Emit state sync events for node transitions
                if node_name:
                    yield langchain_dumps({
                        "event": "on_copilotkit_state_sync",
                        "thread_id": thread_id,
                        "run_id": event.get("run_id", str(uuid.uuid4())),
                        "agent_name": self.name,
                        "node_name": node_name,
                        "active": True,
                        "state": {k: v for k, v in current_state.items() if k != "messages"},
                        "running": True,
                        "role": "assistant"
                    }) + "\n"

                # Yield raw event
                yield langchain_dumps(event) + "\n"

            # Final state sync
            final_state = await self.graph.aget_state(run_config)
            final_values = final_state.values if final_state else {}

            yield langchain_dumps({
                "event": "on_copilotkit_state_sync",
                "thread_id": thread_id,
                "run_id": str(uuid.uuid4()),
                "agent_name": self.name,
                "node_name": "__end__",
                "active": False,
                "state": {k: v for k, v in final_values.items() if k != "messages"},
                "messages": self._convert_messages_to_copilotkit(final_values.get("messages", [])),
                "running": False,
                "role": "assistant"
            }) + "\n"

        except Exception as e:
            logger.error("Error streaming events", error=str(e))
            yield langchain_dumps({
                "event": "error",
                "data": {
                    "message": f"Error: {e!s}",
                    "thread_id": thread_id,
                    "agent_name": self.name,
                }
            }) + "\n"
            raise


def create_odin_langgraph_agent(odin_app: Odin):
    """Create a LangGraph agent that uses Odin tools.

    Args:
        odin_app: Odin framework instance

    Returns:
        Compiled LangGraph StateGraph
    """
    import json
    from typing import TypedDict

    from langchain_core.messages import SystemMessage, ToolMessage
    from langgraph.graph import END, START, StateGraph
    from langgraph.graph.message import add_messages

    # Create tools from Odin
    odin_tools = []

    for tool_def in odin_app.list_tools():
        tool_name = tool_def["name"]

        # Create LangChain tool using StructuredTool
        import asyncio

        from langchain_core.tools import StructuredTool

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

    # Create LLM using factory (supports OpenAI, Anthropic, Azure)
    from odin.core.llm_factory import create_llm

    llm = create_llm()

    # Bind tools to LLM
    llm_with_tools = llm.bind_tools(odin_tools) if odin_tools else llm

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
            messages = [system_msg, *list(messages)]

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
                result_str = f"Error executing tool: {e!s}"

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

    # Create checkpointer for conversation persistence
    from odin.core.llm_factory import create_checkpointer

    checkpointer = create_checkpointer()
    logger.info("LangGraph agent compiled with checkpointer", checkpointer_type=type(checkpointer).__name__)

    return graph.compile(checkpointer=checkpointer)


class CopilotKitAdapter:
    """Adapter to expose Odin tools as CopilotKit actions with LangGraph agent.

    This adapter converts Odin's tool definitions to CopilotKit's Action format
    and creates a LangGraph agent for handling conversations.

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
        self._sdk = None
        self._graph = None

    def _convert_odin_tool_to_copilotkit_action(self, tool: dict) -> Any:
        """Convert an Odin tool definition to a CopilotKit Action.

        Args:
            tool: Odin tool dictionary

        Returns:
            CopilotKit Action object
        """
        try:
            from copilotkit import Action as CopilotAction
        except ImportError as e:
            raise ImportError(
                "copilotkit package is required. Install with: pip install copilotkit"
            ) from e

        # Convert parameters to CopilotKit format
        parameters = []
        for param in tool.get("parameters", []):
            param_def = {
                "name": param["name"],
                "type": self._map_type(param.get("type", "string")),
                "description": param.get("description", ""),
                "required": param.get("required", False),
            }
            parameters.append(param_def)

        # Create handler that calls Odin's execute_tool
        tool_name = tool["name"]

        async def handler(**kwargs):
            logger.info(
                "CopilotKit action called",
                tool=tool_name,
                params=list(kwargs.keys()),
            )
            try:
                result = await self.odin_app.execute_tool(tool_name, **kwargs)
                logger.info("CopilotKit action completed", tool=tool_name)
                return result
            except Exception as e:
                logger.error(
                    "CopilotKit action failed",
                    tool=tool_name,
                    error=str(e),
                )
                raise

        action = CopilotAction(
            name=tool["name"],
            description=tool.get("description", ""),
            parameters=parameters,
            handler=handler,
        )

        return action

    def _map_type(self, odin_type: str) -> str:
        """Map Odin type to CopilotKit type.

        Args:
            odin_type: Odin parameter type

        Returns:
            CopilotKit parameter type
        """
        type_mapping = {
            "str": "string",
            "string": "string",
            "int": "number",
            "integer": "number",
            "float": "number",
            "number": "number",
            "bool": "boolean",
            "boolean": "boolean",
            "list": "array",
            "array": "array",
            "dict": "object",
            "object": "object",
        }
        return type_mapping.get(odin_type.lower(), "string")

    def get_actions(self) -> list:
        """Get all Odin tools as CopilotKit actions.

        Returns:
            List of CopilotKit Action objects
        """
        actions = []
        tools = self.odin_app.list_tools()

        for tool in tools:
            try:
                action = self._convert_odin_tool_to_copilotkit_action(tool)
                actions.append(action)
                logger.info(
                    "Converted tool to CopilotKit action",
                    tool=tool["name"],
                )
            except Exception as e:
                logger.error(
                    "Failed to convert tool",
                    tool=tool["name"],
                    error=str(e),
                )

        return actions

    def get_graph(self):
        """Get LangGraph agent graph.

        Returns:
            Compiled LangGraph StateGraph
        """
        if self._graph is None:
            self._graph = create_odin_langgraph_agent(self.odin_app)
            logger.info("LangGraph agent created")
        return self._graph

    def get_sdk(self):
        """Get CopilotKit SDK instance with agent.

        Returns:
            CopilotKitRemoteEndpoint instance
        """
        try:
            from copilotkit import CopilotKitRemoteEndpoint
        except ImportError as e:
            raise ImportError(
                "copilotkit package is required. Install with: pip install copilotkit"
            ) from e

        if self._sdk is None:
            actions = self.get_actions()
            graph = self.get_graph()

            # Use our custom OdinLangGraphAgent which:
            # 1. Has execute() method for CopilotKit SDK compatibility
            # 2. Doesn't use ag_ui Pydantic models (Python 3.14 compatible)
            # 3. Has dict_repr() and get_state() for SDK interface
            agent = OdinLangGraphAgent(
                name="odin_agent",
                description="AI assistant powered by Odin framework with weather, calendar, and data tools",
                graph=graph,
            )

            self._sdk = CopilotKitRemoteEndpoint(
                actions=actions,
                agents=[agent],
            )
            logger.info(
                "CopilotKit SDK created",
                action_count=len(actions),
                agent="odin_agent",
            )

        return self._sdk

    def mount(self, app: FastAPI, path: str = "/copilotkit"):
        """Mount CopilotKit endpoints on FastAPI app.

        Args:
            app: FastAPI application
            path: Endpoint path (default: "/copilotkit")
        """
        try:
            from copilotkit.integrations.fastapi import add_fastapi_endpoint
        except ImportError as e:
            raise ImportError(
                "copilotkit package is required. Install with: pip install copilotkit"
            ) from e

        sdk = self.get_sdk()
        add_fastapi_endpoint(app, sdk, path)

        logger.info(
            "CopilotKit endpoint mounted",
            path=path,
            actions=len(self.get_actions()),
        )
