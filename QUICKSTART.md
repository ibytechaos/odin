# Odin 快速开始指南

## 5分钟上手 Odin

### 1. 安装

```bash
# 克隆项目
git clone https://github.com/yourusername/odin.git
cd odin

# 安装依赖
uv sync

# 验证安装
uv run python -c "from odin import Odin; print('✓ Odin installed successfully')"
```

### 2. 运行第一个示例

```bash
# 运行自定义插件示例
PYTHONPATH=src uv run python examples/custom_plugin.py
```

你会看到：
```
=== Custom Calculator Plugin Registered ===
10 + 5 = 15
7 * 6 = 42
2^10 = 1024
```

### 3. 创建你的第一个 Plugin

创建文件 `my_plugin.py`:

```python
from typing import Any
from odin import Odin, AgentPlugin, Tool, ToolParameter
from odin.plugins.base import ToolParameterType


class GreeterPlugin(AgentPlugin):
    """简单的问候插件"""

    @property
    def name(self) -> str:
        return "greeter"

    @property
    def version(self) -> str:
        return "1.0.0"

    async def get_tools(self) -> list[Tool]:
        return [
            Tool(
                name="greet",
                description="向用户打招呼",
                parameters=[
                    ToolParameter(
                        name="name",
                        type=ToolParameterType.STRING,
                        description="用户名",
                        required=True,
                    ),
                    ToolParameter(
                        name="language",
                        type=ToolParameterType.STRING,
                        description="语言",
                        required=False,
                        default="zh",
                        enum=["zh", "en"],
                    ),
                ],
            )
        ]

    async def execute_tool(
        self, tool_name: str, **kwargs: Any
    ) -> dict[str, Any]:
        if tool_name == "greet":
            name = kwargs["name"]
            language = kwargs.get("language", "zh")

            if language == "zh":
                message = f"你好，{name}！欢迎使用 Odin 框架。"
            else:
                message = f"Hello, {name}! Welcome to Odin framework."

            return {
                "message": message,
                "language": language,
            }


async def main():
    # 初始化框架
    app = Odin()
    await app.initialize()

    # 注册插件
    await app.register_plugin(GreeterPlugin())

    # 使用工具
    result = await app.execute_tool("greet", name="张三")
    print(result["message"])

    result = await app.execute_tool("greet", name="John", language="en")
    print(result["message"])

    await app.shutdown()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

运行：
```bash
PYTHONPATH=src uv run python my_plugin.py
```

输出：
```
你好，张三！欢迎使用 Odin 框架。
Hello, John! Welcome to Odin framework.
```

### 4. 使用 CrewAI Plugin

```python
from odin import Odin
from odin.plugins.crewai import CrewAIPlugin


async def main():
    app = Odin()
    await app.initialize()

    # 注册 CrewAI 插件
    await app.register_plugin(CrewAIPlugin())

    # 查看可用的工具
    print("CrewAI Tools:")
    for tool in app.list_tools():
        print(f"  - {tool['name']}: {tool['description']}")

    # 列出所有 agents (初始为空)
    result = await app.execute_tool("list_agents")
    print(f"\nAgents: {result}")

    await app.shutdown()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### 5. 下一步

现在你已经掌握了 Odin 的基础！接下来可以：

1. **探索更多示例**: 查看 `examples/` 目录
2. **阅读开发文档**: 查看 `DEVELOPMENT.md` 了解架构设计
3. **创建复杂 Plugin**: 参考 `src/odin/plugins/crewai/plugin.py`
4. **贡献代码**: 查看 GitHub Issues 寻找感兴趣的任务

## 核心概念

### Plugin (插件)
- Odin 的基本扩展单元
- 继承 `AgentPlugin` 抽象基类
- 提供 `get_tools()` 和 `execute_tool()` 方法

### Tool (工具)
- Plugin 提供的可执行功能
- 定义输入参数和描述
- 支持转换为 OpenAI/MCP 格式

### Odin (框架)
- 统一的插件管理器
- 提供工具发现和执行 API
- 处理生命周期管理

## 配置

在项目根目录创建 `.env` 文件：

```bash
# 复制示例配置
cp .env.example .env

# 编辑配置
# 至少设置以下内容：
ODIN_ENV=development
ODIN_LOG_LEVEL=INFO

# 如果使用 LLM
OPENAI_API_KEY=sk-your-key-here
# 或
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

## 故障排查

### 问题：找不到 odin 模块

**解决方案**：
```bash
# 方法 1: 使用 PYTHONPATH
PYTHONPATH=src uv run python your_script.py

# 方法 2: 安装到开发环境
uv pip install -e .
```

### 问题：CrewAI 需要 LLM API key

CrewAI 创建 Agent 时会初始化 LLM，需要配置 API key。

**解决方案**：
```bash
# 在 .env 中设置
OPENAI_API_KEY=sk-your-key-here
```

### 问题：端口被占用

**解决方案**：
```bash
# 修改 .env 中的端口配置
HTTP_PORT=8001  # 默认 8000
MCP_PORT=8002   # 默认 8001
```

## 获取帮助

- **GitHub Issues**: https://github.com/yourusername/odin/issues
- **文档**: 查看项目 README 和 DEVELOPMENT.md
- **示例代码**: `examples/` 目录

---

**祝你使用愉快！** 🚀
