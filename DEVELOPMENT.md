# Odin Development Roadmap

## 当前状态 (v0.1.0 - Phase 1 完成)

### ✅ 已完成的核心功能

#### 1. 基础设施层
- [x] **项目配置**: uv + pyproject.toml，支持 Python 3.12+
- [x] **依赖管理**: 使用 uv 管理依赖，支持开发、生产等多环境
- [x] **代码质量**: ruff (lint + format) + mypy (type check)
- [x] **测试框架**: pytest + pytest-asyncio 配置完成

#### 2. 错误处理体系
- [x] **标准化错误码**: ODIN-xxxx 格式的错误编码
- [x] **异常层次结构**: OdinError 基类及各领域异常类
- [x] **错误处理工具**: ErrorHandler 上下文管理器
- [x] **错误序列化**: 统一的错误响应格式

#### 3. 配置系统
- [x] **Pydantic Settings**: 类型安全的配置管理
- [x] **多环境支持**: .env 文件分层加载
- [x] **配置验证**: 自动验证和类型转换
- [x] **LLM 集成**: OpenAI、Anthropic 配置支持

#### 4. 日志系统
- [x] **结构化日志**: structlog 集成
- [x] **链路追踪**: OpenTelemetry trace_id 自动注入
- [x] **多输出格式**: 开发环境彩色输出，生产环境 JSON
- [x] **日志级别**: 支持动态配置

#### 5. Plugin 系统
- [x] **抽象接口**: AgentPlugin 基类定义
- [x] **生命周期管理**: initialize/shutdown 钩子
- [x] **Tool 定义**: 统一的 Tool 和 ToolParameter 模型
- [x] **动态加载**: 从文件和目录动态发现插件
- [x] **依赖解析**: 插件间依赖管理
- [x] **格式转换**: 支持 OpenAI Function Calling 和 MCP Tool Schema

#### 6. CrewAI 集成
- [x] **CrewAI Plugin**: 完整的 CrewAI 框架适配器
- [x] **Agent 管理**: 创建、列举 agents
- [x] **Task 管理**: 创建、列举 tasks
- [x] **Crew 编排**: 创建、执行、列举 crews
- [x] **7个工具**: create_agent, create_task, create_crew, execute_crew, list_*

#### 7. 核心框架
- [x] **Odin 主类**: 框架入口和协调者
- [x] **异步优先**: 全异步 API 设计
- [x] **统一接口**: 插件注册、工具执行、生命周期管理

#### 8. 示例和文档
- [x] **自定义插件示例**: Calculator plugin
- [x] **框架演示**: 完整的初始化-使用-清理流程
- [x] **CrewAI 示例**: 基于 CrewAI 的 agent 使用案例
- [x] **README**: 项目介绍和快速开始

---

## 下一阶段计划

### Phase 2: 协议层和存储 (预计 2-3周)

#### 2.1 OpenTelemetry 集成 (高优先级)
```python
# 目标功能
from odin.tracing import setup_tracing

setup_tracing(
    service_name="my-agent",
    exporter="otlp",  # 或 jaeger, zipkin
    endpoint="http://localhost:4317"
)

# 自动为所有 tool 执行生成 spans
```

**文件清单**:
- `src/odin/tracing/__init__.py`
- `src/odin/tracing/setup.py`
- `src/odin/tracing/decorators.py` (自动 instrument 装饰器)

#### 2.2 存储抽象层
```python
# 统一的 KV 存储接口
from odin.storage import get_storage

storage = get_storage()  # 根据配置自动选择 backend
await storage.set("key", {"value": "data"})
data = await storage.get("key")
```

**支持的后端**:
- [x] SQLite (已在依赖中)
- [x] Redis (已在依赖中)
- [ ] PostgreSQL (需要实现)
- [ ] 内存存储 (开发用)

**文件清单**:
- `src/odin/storage/__init__.py`
- `src/odin/storage/base.py` (抽象接口)
- `src/odin/storage/sqlite.py`
- `src/odin/storage/redis.py`
- `src/odin/storage/memory.py`

#### 2.3 MCP 协议实现
```python
# 作为 MCP Server 运行
from odin import Odin
from odin.protocols.mcp import MCPServer

app = Odin()
# ... 注册插件

mcp = MCPServer(app)
await mcp.serve(port=8001)
```

**功能**:
- [ ] MCP Server 实现
- [ ] Tool 自动注册到 MCP
- [ ] 请求/响应序列化
- [ ] WebSocket 支持

**文件清单**:
- `src/odin/protocols/mcp/__init__.py`
- `src/odin/protocols/mcp/server.py`
- `src/odin/protocols/mcp/schemas.py`

#### 2.4 HTTP/REST API
```python
# FastAPI 集成
from odin.protocols.http import create_app

app = create_app(odin_instance)
# 自动生成 OpenAPI 文档
# GET  /tools - 列举所有工具
# POST /tools/{tool_name}/execute - 执行工具
```

**文件清单**:
- `src/odin/protocols/http/__init__.py`
- `src/odin/protocols/http/app.py`
- `src/odin/protocols/http/routes.py`

---

### Phase 3: 高级特性 (预计 2周)

#### 3.1 重试和容错
```python
from odin.utils.retry import with_retry

@with_retry(max_attempts=3, backoff="exponential")
async def unreliable_tool(**kwargs):
    # 自动重试逻辑
    pass
```

#### 3.2 性能分析集成
```python
# pprof-like profiling
from odin.profiling import enable_profiling

enable_profiling(port=6060)
# 访问 http://localhost:6060/debug/pprof
```

#### 3.3 CLI 工具
```bash
odin init my-project          # 创建新项目
odin plugin create calculator # 生成插件模板
odin serve --port 8000        # 启动服务器
odin tools list               # 列举工具
```

#### 3.4 单测工具
```python
# Mock plugin 用于测试
from odin.testing import MockPlugin

@pytest.fixture
async def app():
    app = Odin()
    app.register_plugin(MockPlugin())
    await app.initialize()
    yield app
    await app.shutdown()
```

---

### Phase 4: 生态系统扩展 (持续)

#### 4.1 更多 Plugin 适配器
- [ ] **LangGraph Plugin**: 支持 LangGraph workflows
- [ ] **AutoGen Plugin**: 多 agent 对话
- [ ] **LlamaIndex Plugin**: RAG 和文档处理
- [ ] **LangChain Plugin**: LangChain tools 转换

#### 4.2 生成式 UI 集成
- [ ] **Copilot Kit 适配器**
- [ ] **ag-ui 适配器**
- [ ] **自定义 UI 协议**

#### 4.3 部署工具
- [ ] Docker 镜像生成
- [ ] Kubernetes Helm Charts
- [ ] Serverless 部署 (AWS Lambda, etc.)

---

## 技术债务和改进

### 当前已知问题
1. ⚠️ CrewAI Agent 创建需要 LLM API key (即使只是定义也会初始化)
2. ⚠️ 缺少单元测试覆盖
3. ⚠️ 类型标注未完全覆盖
4. ⚠️ 缺少性能基准测试

### 优化方向
1. **性能**:
   - [ ] 添加 tool 执行缓存
   - [ ] 批量工具调用优化
   - [ ] 异步并发控制

2. **开发体验**:
   - [ ] 更好的错误消息
   - [ ] 开发文档和 API reference
   - [ ] 更多示例和最佳实践

3. **生产就绪**:
   - [ ] Rate limiting
   - [ ] 请求认证和授权
   - [ ] 审计日志
   - [ ] Metrics 收集

---

## 贡献指南

### 开发流程
```bash
# 1. 克隆仓库
git clone https://github.com/yourusername/odin.git
cd odin

# 2. 安装依赖
uv sync --all-extras

# 3. 运行测试
uv run pytest

# 4. 代码检查
uv run ruff check src/
uv run mypy src/

# 5. 格式化
uv run ruff format src/
```

### 目录结构约定
```
src/odin/
├── <module>/          # 功能模块
│   ├── __init__.py    # 导出公共 API
│   ├── base.py        # 抽象基类
│   └── impl.py        # 具体实现
tests/
├── unit/              # 单元测试
├── integration/       # 集成测试
└── e2e/               # 端到端测试
```

### Commit 规范
- `feat:` 新功能
- `fix:` Bug 修复
- `docs:` 文档更新
- `refactor:` 代码重构
- `test:` 测试相关
- `chore:` 构建/工具相关

---

## 性能目标

### 延迟要求
- Plugin 加载: < 100ms
- Tool 执行开销: < 10ms
- 框架初始化: < 500ms

### 吞吐量
- 支持 1000+ concurrent tool executions
- Plugin 热重载 < 1s

### 资源占用
- 基础内存占用 < 100MB
- 每个 plugin < 50MB

---

## 许可证

MIT License

---

**更新时间**: 2025-11-27
**当前版本**: v0.1.0
**下个里程碑**: v0.2.0 (Phase 2 完成)
