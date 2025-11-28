# Odin 框架架构重新设计

## 🎯 设计目标

### 1. Agent 后端灵活性
- ✅ 支持 **CrewAI** 作为默认 Agent 引擎（不是 LangGraph）
- ✅ 支持 **LangGraph** 作为可选 Agent 引擎
- ✅ 支持 **自定义 Agent** 实现
- ✅ 用户可以通过配置选择 Agent 后端

### 2. 协议无感知
- ✅ 业务层代码**不感知底层协议**（MCP/A2A/AG-UI/CopilotKit）
- ✅ 工具定义**一次编写，所有协议共享**
- ✅ 自动协议检测和路由
- ✅ 统一的 Agent 状态管理

---

## 🏗️ 新架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                    Business Layer                            │
│  - @tool 装饰器定义工具                                        │
│  - Plugin 类定义业务逻辑                                       │
│  - 不感知协议和 Agent 实现                                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  Tool Registry Layer                         │
│  - 统一的工具注册表                                           │
│  - 工具元数据管理（name, description, parameters）            │
│  - 工具执行器（executor）                                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                 Agent Abstraction Layer                      │
│  - IAgent 接口（统一的 Agent 抽象）                           │
│  - CrewAIAgentBackend（CrewAI 实现）⭐ 默认                  │
│  - LangGraphAgentBackend（LangGraph 实现）                   │
│  - CustomAgentBackend（自定义实现）                          │
│  - AgentFactory（根据配置创建 Agent）                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              Protocol Dispatcher Layer                       │
│  - 自动检测请求协议类型                                        │
│  - 路由到对应的协议适配器                                      │
│  - 统一的错误处理                                             │
└─────────────────────────────────────────────────────────────┘
           ↓           ↓           ↓            ↓
┌──────────────┬──────────────┬──────────────┬──────────────┐
│ MCP Adapter  │ A2A Adapter  │ AGUI Adapter │Copilot Adapter│
│  (stdio)     │  (HTTP)      │   (SSE)      │  (GraphQL)    │
└──────────────┴──────────────┴──────────────┴──────────────┘
```

---

## 📦 核心组件设计

### 1. IAgent 接口（Agent 抽象）

```python
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, TypedDict

class AgentState(TypedDict):
    """统一的 Agent 状态"""
    messages: list  # 对话历史
    current_step: str  # 当前步骤
    intermediate_results: list  # 中间结果
    ui_components: list[dict]  # 生成式 UI 组件
    error: str | None  # 错误信息
    metadata: dict[str, Any]  # 自定义元数据

class IAgent(ABC):
    """统一的 Agent 接口

    所有 Agent 后端（CrewAI、LangGraph、自定义）都必须实现这个接口
    """

    @abstractmethod
    async def execute(
        self,
        *,
        input: str | dict,
        state: AgentState | None = None,
        thread_id: str,
        **kwargs
    ) -> AsyncGenerator[dict, None]:
        """执行 Agent

        Args:
            input: 用户输入（文本或结构化数据）
            state: 当前 Agent 状态
            thread_id: 会话 ID（用于持久化）

        Yields:
            事件流：
            - {"type": "message", "content": "..."}
            - {"type": "tool_call", "tool": "...", "args": {...}}
            - {"type": "state_update", "state": {...}}
            - {"type": "ui_component", "component": {...}}
            - {"type": "error", "error": "..."}
        """
        pass

    @abstractmethod
    async def get_state(self, thread_id: str) -> AgentState | None:
        """获取 Agent 状态"""
        pass

    @abstractmethod
    async def update_state(self, thread_id: str, state: AgentState) -> None:
        """更新 Agent 状态"""
        pass

    @abstractmethod
    def add_tool(self, tool: Tool) -> None:
        """添加工具到 Agent"""
        pass

    @abstractmethod
    def get_metadata(self) -> dict:
        """获取 Agent 元数据（name, description, capabilities）"""
        pass
```

---

### 2. CrewAI Agent Backend（默认实现）⭐

```python
from crewai import Agent as CrewAgent, Crew, Task
from copilotkit.crewai import CrewAIAgent as CopilotKitCrewAIAgent

class CrewAIAgentBackend(IAgent):
    """基于 CrewAI 的 Agent 实现

    这是 Odin 框架的默认 Agent 后端
    """

    def __init__(
        self,
        name: str = "odin_agent",
        description: str = "AI Agent powered by Odin + CrewAI",
        llm: str | None = None,  # 从配置读取
    ):
        self.name = name
        self.description = description
        self.llm = llm

        # CrewAI Agents
        self._agents: list[CrewAgent] = []
        self._tasks: list[Task] = []
        self._crew: Crew | None = None
        self._tools: list[Tool] = []

        # 为 CopilotKit 创建包装
        self._copilotkit_agent: CopilotKitCrewAIAgent | None = None

        self._initialize_crew()

    def _initialize_crew(self):
        """初始化 CrewAI Crew"""
        # 创建默认 Agent
        main_agent = CrewAgent(
            role="AI Assistant",
            goal=self.description,
            backstory="An intelligent AI assistant powered by Odin framework",
            verbose=True,
            llm=self.llm,
        )
        self._agents.append(main_agent)

        # 创建默认 Task
        default_task = Task(
            description="Process user request and provide helpful response",
            agent=main_agent,
            expected_output="A helpful and accurate response"
        )
        self._tasks.append(default_task)

        # 创建 Crew
        self._crew = Crew(
            agents=self._agents,
            tasks=self._tasks,
            verbose=True,
        )

    def add_tool(self, tool: Tool) -> None:
        """添加工具到 CrewAI Agent"""
        # 将 Odin Tool 转换为 CrewAI Tool
        from crewai.tools import BaseTool as CrewAIBaseTool

        class OdinToolWrapper(CrewAIBaseTool):
            name: str = tool.name
            description: str = tool.description
            odin_tool: Tool = tool

            async def _arun(self, **kwargs: Any) -> Any:
                # 执行 Odin 工具
                return await tool.execute(**kwargs)

        crewai_tool = OdinToolWrapper()
        self._tools.append(crewai_tool)

        # 更新 Agent 的工具列表
        for agent in self._agents:
            agent.tools.append(crewai_tool)

    async def execute(
        self,
        *,
        input: str | dict,
        state: AgentState | None = None,
        thread_id: str,
        **kwargs
    ) -> AsyncGenerator[dict, None]:
        """执行 CrewAI Crew"""

        # 准备输入
        if isinstance(input, str):
            crew_input = {"user_request": input}
        else:
            crew_input = input

        # 发送开始事件
        yield {
            "type": "run_started",
            "agent": self.name,
            "thread_id": thread_id
        }

        try:
            # 执行 Crew（同步调用，需要在线程池中运行）
            import asyncio
            result = await asyncio.to_thread(
                self._crew.kickoff,
                inputs=crew_input
            )

            # 发送结果
            yield {
                "type": "message",
                "content": str(result),
                "role": "assistant"
            }

            # 发送完成事件
            yield {
                "type": "run_finished",
                "agent": self.name,
                "thread_id": thread_id
            }

        except Exception as e:
            yield {
                "type": "error",
                "error": str(e),
                "agent": self.name
            }

    async def get_state(self, thread_id: str) -> AgentState | None:
        """获取状态（CrewAI 没有内置状态管理）"""
        # TODO: 实现状态持久化
        return None

    async def update_state(self, thread_id: str, state: AgentState) -> None:
        """更新状态"""
        # TODO: 实现状态持久化
        pass

    def get_metadata(self) -> dict:
        """获取 Agent 元数据"""
        return {
            "name": self.name,
            "description": self.description,
            "type": "crewai",
            "capabilities": ["multi_agent", "task_delegation"],
            "tools": [tool.name for tool in self._tools]
        }

    def get_copilotkit_agent(self) -> CopilotKitCrewAIAgent:
        """获取 CopilotKit 包装的 Agent（用于 CopilotKit 协议）"""
        if self._copilotkit_agent is None:
            self._copilotkit_agent = CopilotKitCrewAIAgent(
                name=self.name,
                description=self.description,
                crew=self._crew
            )
        return self._copilotkit_agent
```

---

### 3. LangGraph Agent Backend（可选实现）

```python
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

class LangGraphAgentBackend(IAgent):
    """基于 LangGraph 的 Agent 实现

    可选的 Agent 后端，用于需要复杂状态图的场景
    """

    def __init__(
        self,
        name: str = "odin_agent",
        description: str = "AI Agent powered by Odin + LangGraph",
    ):
        self.name = name
        self.description = description
        self._graph = None
        self._checkpointer = MemorySaver()
        self._tools = []

        self._build_graph()

    def _build_graph(self):
        """构建 LangGraph 状态图"""
        # ... (当前的 LangGraph 实现)
        pass

    def add_tool(self, tool: Tool) -> None:
        """添加工具到 LangGraph"""
        # 转换为 LangChain Tool
        self._tools.append(convert_to_langchain_tool(tool))
        self._build_graph()  # 重新构建图

    # ... 实现其他 IAgent 方法
```

---

### 4. Agent Factory（工厂模式）

```python
from odin.config import get_settings

class AgentFactory:
    """Agent 工厂，根据配置创建 Agent 实例"""

    @staticmethod
    def create_agent(agent_type: str | None = None) -> IAgent:
        """创建 Agent 实例

        Args:
            agent_type: Agent 类型 (crewai, langgraph, custom)
                       如果为 None，从配置读取

        Returns:
            IAgent 实例
        """
        settings = get_settings()
        agent_type = agent_type or settings.agent_backend  # 新配置项

        if agent_type == "crewai":
            return CrewAIAgentBackend(
                name=settings.agent_name,
                description=settings.agent_description,
                llm=create_llm(),  # 使用 LLM 工厂
            )
        elif agent_type == "langgraph":
            return LangGraphAgentBackend(
                name=settings.agent_name,
                description=settings.agent_description,
            )
        elif agent_type == "custom":
            # 加载用户自定义 Agent
            return load_custom_agent(settings.custom_agent_path)
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")
```

---

### 5. Protocol Dispatcher（协议分发器）

```python
from fastapi import Request

class ProtocolType(Enum):
    MCP = "mcp"
    A2A = "a2a"
    AGUI = "agui"
    COPILOTKIT = "copilotkit"
    HTTP = "http"

class ProtocolDispatcher:
    """协议分发器

    自动检测请求类型并路由到对应的协议适配器
    """

    def __init__(self, agent: IAgent):
        self.agent = agent
        self.adapters = {
            ProtocolType.MCP: MCPAdapter(agent),
            ProtocolType.A2A: A2AAdapter(agent),
            ProtocolType.AGUI: AGUIAdapter(agent),
            ProtocolType.COPILOTKIT: CopilotKitAdapter(agent),
            ProtocolType.HTTP: HTTPAdapter(agent),
        }

    @staticmethod
    def detect_protocol(request: Request) -> ProtocolType:
        """自动检测请求协议类型"""

        # 检查 Content-Type
        content_type = request.headers.get("content-type", "")

        # CopilotKit: GraphQL 请求
        if "application/json" in content_type:
            body = await request.json()
            if "query" in body and "copilot" in body.get("query", "").lower():
                return ProtocolType.COPILOTKIT

        # AG-UI: Accept header 包含 text/event-stream
        if "text/event-stream" in request.headers.get("accept", ""):
            return ProtocolType.AGUI

        # A2A: 特定的 A2A 端点
        if request.url.path.startswith("/.well-known/agent-card"):
            return ProtocolType.A2A

        # MCP: 通过 stdio（不会有 HTTP 请求）
        # 这里不会到达，MCP 是单独启动的

        # 默认：HTTP/REST
        return ProtocolType.HTTP

    async def dispatch(self, request: Request):
        """分发请求到对应的协议适配器"""
        protocol = self.detect_protocol(request)
        adapter = self.adapters[protocol]
        return await adapter.handle_request(request)
```

---

### 6. Base Protocol Adapter（协议适配器基类）

```python
class IProtocolAdapter(ABC):
    """协议适配器接口"""

    def __init__(self, agent: IAgent):
        self.agent = agent

    @abstractmethod
    async def handle_request(self, request: Any) -> Any:
        """处理协议请求"""
        pass

    @abstractmethod
    def convert_tools(self) -> Any:
        """将 Odin 工具转换为协议特定格式"""
        pass
```

---

### 7. CopilotKit Adapter（重构版）

```python
class CopilotKitAdapter(IProtocolAdapter):
    """CopilotKit 协议适配器

    支持 CrewAI 和 LangGraph 作为后端
    """

    def __init__(self, agent: IAgent):
        super().__init__(agent)
        self._sdk = None

    def get_sdk(self):
        """获取 CopilotKit SDK"""
        if self._sdk is not None:
            return self._sdk

        # 根据 Agent 类型选择不同的集成方式
        if isinstance(self.agent, CrewAIAgentBackend):
            # 使用官方 CrewAI 集成
            from copilotkit import CopilotKitRemoteEndpoint

            crewai_agent = self.agent.get_copilotkit_agent()
            self._sdk = CopilotKitRemoteEndpoint(
                agents=[crewai_agent],
                actions=self.convert_tools()  # Actions 仍然可用
            )

        elif isinstance(self.agent, LangGraphAgentBackend):
            # 使用 LangGraph 集成（当前的实现）
            from copilotkit import CopilotKitRemoteEndpoint

            langgraph_agent = self.agent.get_langgraph_agent()
            self._sdk = CopilotKitRemoteEndpoint(
                agents=[langgraph_agent],
                actions=self.convert_tools()
            )
        else:
            # 自定义 Agent：回退到 Actions 模式
            from copilotkit import CopilotKitRemoteEndpoint

            self._sdk = CopilotKitRemoteEndpoint(
                actions=self.convert_tools()
            )

        return self._sdk

    def convert_tools(self) -> list:
        """转换工具为 CopilotKit Actions"""
        # ... (当前的实现)
        pass

    async def handle_request(self, request: Request):
        """处理 CopilotKit GraphQL 请求"""
        from copilotkit.integrations.fastapi import add_fastapi_endpoint

        sdk = self.get_sdk()
        # CopilotKit 会处理后续逻辑
        return await sdk.handle_graphql_request(request)
```

---

## 📝 配置文件更新

### `.env` 新增配置

```bash
# ============================================
# Agent Backend Configuration
# ============================================
# Choose agent backend: crewai, langgraph, custom
ODIN_AGENT_BACKEND=crewai  # ⭐ 默认使用 CrewAI

# Agent Metadata
ODIN_AGENT_NAME=odin_agent
ODIN_AGENT_DESCRIPTION=AI assistant powered by Odin framework

# Custom Agent (if using custom backend)
# ODIN_CUSTOM_AGENT_PATH=my_agents.CustomAgent
```

---

## 🔄 使用示例

### 业务层代码（协议无感知）

```python
# plugins/weather.py
from odin.decorators import tool

@tool
def get_weather(location: str, unit: str = "celsius") -> dict:
    """获取天气信息"""
    return {
        "location": location,
        "temperature": 22,
        "unit": unit,
        "condition": "Sunny"
    }

# 这个工具会自动：
# 1. 注册到 Tool Registry
# 2. 添加到 Agent（CrewAI/LangGraph）
# 3. 暴露给所有协议（MCP/A2A/AG-UI/CopilotKit）
```

### 启动服务（自动协议路由）

```python
# main.py
from odin import Odin
from odin.core.agent_factory import AgentFactory
from odin.protocols.dispatcher import ProtocolDispatcher

async def main():
    # 1. 创建 Odin 实例
    app = Odin()
    await app.initialize()

    # 2. 创建 Agent（从配置读取类型）
    agent = AgentFactory.create_agent()  # 默认创建 CrewAI Agent

    # 3. 添加工具到 Agent
    for tool in app.list_tools():
        agent.add_tool(tool)

    # 4. 创建协议分发器
    dispatcher = ProtocolDispatcher(agent)

    # 5. 创建 FastAPI app
    from fastapi import FastAPI
    fastapi_app = FastAPI()

    # 6. 添加统一端点（自动检测协议）
    @fastapi_app.post("/agent")
    async def unified_endpoint(request: Request):
        return await dispatcher.dispatch(request)

    # 7. 也可以手动挂载特定协议
    # CopilotKit
    copilotkit_adapter = dispatcher.adapters[ProtocolType.COPILOTKIT]
    copilotkit_adapter.mount(fastapi_app, "/copilotkit")

    # A2A
    a2a_adapter = dispatcher.adapters[ProtocolType.A2A]
    fastapi_app.mount("/a2a", a2a_adapter.app)

    # HTTP/REST
    http_adapter = dispatcher.adapters[ProtocolType.HTTP]
    fastapi_app.mount("/api", http_adapter.app)

    return fastapi_app
```

### 切换 Agent 后端（零代码修改）

```bash
# 使用 CrewAI（默认）
ODIN_AGENT_BACKEND=crewai

# 切换到 LangGraph
ODIN_AGENT_BACKEND=langgraph

# 使用自定义 Agent
ODIN_AGENT_BACKEND=custom
ODIN_CUSTOM_AGENT_PATH=my_agents.MyAgent
```

**业务代码完全不变！**

---

## 🎯 架构优势

### 1. Agent 后端灵活性 ✅
- ✅ 默认使用 CrewAI（更适合多 Agent 协作）
- ✅ 可选 LangGraph（更适合复杂状态图）
- ✅ 支持自定义 Agent
- ✅ 配置切换，零代码修改

### 2. 协议完全无感知 ✅
- ✅ 业务代码只关心工具定义
- ✅ 工具自动暴露给所有协议
- ✅ 自动协议检测和路由
- ✅ 统一的错误处理

### 3. 最佳实践集成 ✅
- ✅ CrewAI：使用官方 `copilotkit.crewai.CrewAIAgent`
- ✅ LangGraph：使用当前的 `OdinLangGraphAgent`
- ✅ 双向状态共享（所有 Agent 后端）
- ✅ 生成式 UI 支持（协议无关）

### 4. 扩展性强 ✅
- ✅ 新增 Agent 后端：实现 `IAgent` 接口
- ✅ 新增协议：实现 `IProtocolAdapter` 接口
- ✅ 插件化设计

---

## 📊 对比：改进前 vs 改进后

| 特性 | 改进前 | 改进后 |
|-----|--------|--------|
| Agent 后端 | ❌ 硬编码 LangGraph | ✅ 可配置（CrewAI/LangGraph/自定义）|
| CrewAI 支持 | ⚠️ 只是插件 | ✅ 作为默认 Agent 引擎 |
| 协议感知 | ❌ 每个协议单独写代码 | ✅ 完全无感知，自动适配 |
| 工具定义 | ⚠️ 需要手动转换 | ✅ 定义一次，所有协议共享 |
| 协议切换 | ❌ 需要改代码 | ✅ 配置切换即可 |
| 新增协议 | ❌ 需要大量修改 | ✅ 实现适配器接口即可 |
| 官方集成 | ❌ 自己实现 | ✅ 使用官方 SDK |

---

## 🚀 实施计划

### Phase 1：核心抽象层（1-2 天）
1. ✅ 创建 `IAgent` 接口
2. ✅ 实现 `CrewAIAgentBackend`（默认）
3. ✅ 实现 `LangGraphAgentBackend`（可选）
4. ✅ 实现 `AgentFactory`

### Phase 2：协议分发层（1 天）
5. ✅ 创建 `ProtocolDispatcher`
6. ✅ 实现协议自动检测
7. ✅ 重构现有协议适配器继承 `IProtocolAdapter`

### Phase 3：集成测试（1 天）
8. ✅ 测试 CrewAI + CopilotKit
9. ✅ 测试 CrewAI + MCP/A2A/AG-UI
10. ✅ 测试 Agent 后端切换

### Phase 4：文档和示例（1 天）
11. ✅ 更新文档
12. ✅ 创建示例项目
13. ✅ 迁移指南

**总计：4-5 天完成完整架构改造**

---

## 📚 参考资源

- [CrewAI 官方文档](https://docs.crewai.com/)
- [CopilotKit CrewAI 集成](https://docs.copilotkit.ai/crewai/)
- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [AG-UI 协议规范](https://docs.ag-ui.com/)

---

## ✅ 总结

这个新架构实现了：

1. **✅ CrewAI 作为默认 Agent** - 不再硬编码 LangGraph
2. **✅ 协议完全无感知** - 业务代码一次编写，自动适配所有协议
3. **✅ 灵活可扩展** - Agent 和协议都可以轻松扩展
4. **✅ 最佳实践** - 使用官方 SDK 和推荐模式

**用户可以专注于业务逻辑，框架自动处理所有协议适配！**
