# Odin Framework 快速开始

## 安装

```bash
pip install odin-agent
# 或使用 uv (推荐)
uv pip install odin-agent
```

## 快速创建项目

### 1. 创建全栈项目

```bash
odin create my-agent
cd my-agent
```

这将创建一个包含前后端的完整项目：

```
my-agent/
├── main.py              # 后端入口
├── plugins/            # 插件目录
│   ├── __init__.py
│   └── example.py      # 示例插件
├── frontend/           # Next.js 前端
│   ├── src/
│   │   └── app/
│   │       ├── api/copilotkit/route.ts  # GraphQL 代理
│   │       └── page.tsx                 # 主页面
│   └── package.json
├── .env.example       # 环境变量示例
└── start.sh          # 启动脚本
```

### 2. 仅创建后端

```bash
odin create my-backend --backend
```

### 3. 仅创建前端

```bash
odin create my-frontend --frontend
```

## 配置环境

### 1. 复制环境变量文件

```bash
cp .env.example .env
```

### 2. 配置LLM

编辑 `.env` 文件：

```bash
# OpenAI
OPENAI_API_KEY=sk-your-api-key
OPENAI_MODEL=gpt-4o
# 可选：使用自定义API端点（如代理或兼容服务）
OPENAI_BASE_URL=https://api.openai.com/v1

# 或使用 Anthropic
# ANTHROPIC_API_KEY=sk-ant-xxx
# ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
```

## 启动应用

### 方法1：使用启动脚本（推荐）

```bash
# 启动前后端
./start.sh

# 仅启动后端
./start.sh backend

# 仅启动前端
./start.sh frontend
```

### 方法2：手动启动

**后端：**
```bash
python main.py --protocol copilotkit --host 0.0.0.0 --port 8000
```

**前端：**
```bash
cd frontend
npm install
npm run dev
```

## 验证安装

### 1. 检查后端

访问 http://localhost:8000/health

应该看到：
```json
{
  "status": "healthy",
  "tools": 0
}
```

### 2. 检查前端

访问 http://localhost:3000

你应该看到一个聊天界面。

### 3. 测试对话

在聊天框输入 "Hello"，你应该收到LLM的回复。

## 创建第一个工具

### 1. 创建插件文件

在 `plugins/` 目录创建 `weather.py`：

```python
from odin.decorators import tool

@tool
def get_weather(location: str, unit: str = "celsius") -> dict:
    """获取指定城市的天气信息

    Args:
        location: 城市名称
        unit: 温度单位 (celsius 或 fahrenheit)

    Returns:
        包含天气信息的字典
    """
    # 这里是模拟数据，实际应该调用天气API
    return {
        "location": location,
        "temperature": 22,
        "unit": unit,
        "condition": "晴天"
    }
```

### 2. 重启后端

```bash
./start.sh backend
```

### 3. 测试新工具

在聊天框输入："北京的天气怎么样？"

Agent会自动调用 `get_weather` 工具并返回结果。

## 下一步

- [配置管理](./configuration.md) - 了解如何配置和热加载
- [生成式UI](./generative-ui.md) - 使用CopilotKit创建动态UI
- [插件开发](./plugin-development.md) - 开发自定义插件
- [协议支持](./protocols.md) - MCP, A2A, AG-UI协议详解

## 常见问题

### Q: 前端显示"连接错误"

**A:** 检查以下几点：
1. 后端是否正常运行（访问 http://localhost:8000/health）
2. 前端 `/api/copilotkit/route.ts` 中的后端URL是否正确
3. CORS配置是否允许前端域名

### Q: 聊天框没有响应

**A:**
1. 打开浏览器开发者工具（F12）查看Network标签
2. 检查是否有请求到 `/api/copilotkit`
3. 查看后端日志是否有错误

### Q: 如何使用其他LLM Provider？

**A:** 修改 `.env` 文件：

```bash
# 使用Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-xxx
```

然后修改 `adapter.py` 中的LLM初始化（或等待未来版本支持配置化LLM选择）。

## 故障排除

### 后端错误

```bash
# 查看详细日志
ODIN_LOG_LEVEL=DEBUG python main.py
```

### 前端错误

```bash
# 清除缓存重新安装
cd frontend
rm -rf node_modules package-lock.json .next
npm install
npm run dev
```

### 配置热加载测试

```python
from odin.config import reload_settings
import os

# 修改环境变量
os.environ['OPENAI_MODEL'] = 'gpt-4-turbo'

# 热加载配置
settings = reload_settings()
print(settings.openai_model)  # gpt-4-turbo
```
