# Odin 监控与可观测性

## 概览

Odin 框架提供了完整的生产级监控能力，专为 AI/Agent 系统设计。集成了业界标准的 **OpenTelemetry** 和 **Prometheus**，同时提供了针对 LLM 应用的专门指标。

## 核心能力

### 1. OpenTelemetry 集成

#### Traces (分布式追踪)
- 自动追踪工具执行
- 支持自定义 span
- 异常自动记录
- Trace ID 自动注入到日志

#### Metrics (指标收集)
- Counter (计数器)
- Histogram (直方图)
- UpDownCounter (可增可减计数器)

#### 支持的导出器
- **OTLP**: 生产环境，支持 Jaeger、Tempo、Datadog 等
- **Console**: 开发环境，直接输出到终端

### 2. Prometheus 集成

- HTTP `/metrics` 端点
- 自动格式转换（OpenTelemetry → Prometheus）
- 支持 Grafana 可视化

### 3. AI/Agent 专用指标

#### 工具执行指标
```
odin.tool.executions    # 工具调用次数
odin.tool.errors        # 工具执行错误次数
odin.tool.latency       # 工具执行延迟

Labels: tool, plugin, success, error_type
```

#### LLM 请求指标
```
odin.llm.requests       # LLM API 请求次数
odin.llm.tokens         # Token 消耗量
odin.llm.cost           # 预估成本（USD）
odin.llm.latency        # API 请求延迟

Labels: provider, model, token_type (prompt/completion)
```

#### Agent 任务指标
```
odin.agent.tasks        # Agent 任务总数
odin.agent.success      # 成功的任务数
odin.agent.latency      # 任务执行时间

Labels: agent_type, task_type
```

#### 插件生命周期
```
odin.plugin.loaded      # 已加载的插件数量

Labels: plugin
```

#### 自定义指标
```
odin.custom.counter     # 通用计数器
odin.custom.histogram   # 通用直方图

Labels: name (+ 自定义 labels)
```

---

## 快速开始

### 方案 1: OpenTelemetry (推荐生产环境)

#### 1. 配置环境变量

```bash
# .env
OTEL_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_SERVICE_NAME=my-agent
```

#### 2. 启动收集器

使用 Docker 启动 Jaeger（包含 OTLP 接收器）:

```bash
docker run -d --name jaeger \
  -e COLLECTOR_OTLP_ENABLED=true \
  -p 16686:16686 \
  -p 4317:4317 \
  -p 4318:4318 \
  jaegertracing/all-in-one:latest
```

#### 3. 运行应用

```python
from odin import Odin

app = Odin()  # OpenTelemetry 自动启用
await app.initialize()

# 你的代码...
```

#### 4. 查看追踪

访问 http://localhost:16686 查看 Jaeger UI

---

### 方案 2: Prometheus

#### 1. 启用 Prometheus 导出器

```python
from odin import Odin
from odin.tracing.prometheus import setup_prometheus_exporter

app = Odin()
await app.initialize()

# 启动 Prometheus HTTP 服务器
setup_prometheus_exporter(app.settings, port=9090)

# 你的代码...
```

#### 2. 配置 Prometheus 抓取

创建 `prometheus.yml`:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'odin-agent'
    static_configs:
      - targets: ['localhost:9090']
```

#### 3. 启动 Prometheus

```bash
docker run -d --name prometheus \
  -p 9091:9090 \
  -v $(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus
```

#### 4. 查看指标

访问 http://localhost:9091 查看 Prometheus UI

---

### 方案 3: 完整监控栈 (OpenTelemetry + Prometheus + Grafana)

#### 使用 Docker Compose

创建 `docker-compose.yml`:

```yaml
version: '3.8'

services:
  # Jaeger (Traces)
  jaeger:
    image: jaegertracing/all-in-one:latest
    environment:
      - COLLECTOR_OTLP_ENABLED=true
    ports:
      - "16686:16686"  # UI
      - "4317:4317"    # OTLP gRPC
      - "4318:4318"    # OTLP HTTP

  # Prometheus (Metrics)
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9091:9090"

  # Grafana (Visualization)
  grafana:
    image: grafana/grafana:latest
    environment:
      - GF_AUTH_ANONYMOUS_ENABLED=true
      - GF_AUTH_ANONYMOUS_ORG_ROLE=Admin
    ports:
      - "3000:3000"
    volumes:
      - ./grafana/provisioning:/etc/grafana/provisioning
```

启动：
```bash
docker-compose up -d
```

访问：
- Jaeger UI: http://localhost:16686
- Prometheus: http://localhost:9091
- Grafana: http://localhost:3000

---

## 使用指南

### 1. 自动追踪工具执行

所有通过 Odin 框架执行的工具都会自动记录指标：

```python
# 自动记录:
# - odin.tool.executions
# - odin.tool.latency
# - odin.tool.errors (如果失败)

result = await app.execute_tool("my_tool", arg1="value")
```

### 2. 使用装饰器追踪自定义函数

```python
from odin.tracing import traced, timed

@traced(name="my_operation", attributes={"user_id": "123"})
@timed(metric_name="custom.latency")
async def my_function():
    # 自动创建 span 并记录延迟
    pass
```

### 3. 手动记录指标

```python
from odin.tracing import get_metrics_collector

metrics = get_metrics_collector()

# LLM 请求
metrics.record_llm_request(
    provider="openai",
    model="gpt-4",
    prompt_tokens=100,
    completion_tokens=50,
    latency=0.5,
    cost=0.002,
)

# Agent 任务
metrics.record_agent_task(
    agent_type="crewai",
    task_type="research",
    success=True,
    latency=2.5,
)

# 自定义指标
metrics.increment_counter("my.counter", value=1, labels={"type": "foo"})
metrics.record_latency("my.latency", 0.123, labels={"endpoint": "/api"})
```

### 4. 创建追踪 Span

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("my_operation") as span:
    span.set_attribute("user_id", "123")
    span.set_attribute("request_type", "search")

    # 你的代码
    result = do_something()

    span.set_attribute("result_count", len(result))
```

---

## Grafana Dashboard

### 推荐的 Dashboard 指标

#### 1. 概览面板
- 总请求数 (odin.tool.executions)
- 错误率 (odin.tool.errors / odin.tool.executions)
- P50/P95/P99 延迟 (odin.tool.latency)
- 活跃插件数 (odin.plugin.loaded)

#### 2. LLM 成本面板
- 每小时 Token 消耗 (odin.llm.tokens)
- 累计成本 (odin.llm.cost)
- 按模型分组的成本分布

#### 3. 性能面板
- 工具执行延迟热图
- LLM API 延迟分布
- Agent 任务成功率

### Prometheus 查询示例

```promql
# 工具调用 QPS
rate(odin_tool_executions_total[5m])

# 错误率
rate(odin_tool_errors_total[5m]) / rate(odin_tool_executions_total[5m])

# P95 延迟
histogram_quantile(0.95, rate(odin_tool_latency_bucket[5m]))

# LLM 成本趋势
rate(odin_llm_cost_total[1h])

# 按插件分组的工具调用
sum by (plugin) (rate(odin_tool_executions_total[5m]))
```

---

## 专门的 LLM 监控工具

除了 OpenTelemetry/Prometheus，你还可以集成专门的 LLM 监控平台：

### 1. LangSmith (LangChain 官方)
- 链路可视化
- Prompt 版本管理
- 测试和评估

### 2. Helicone
- LLM 请求缓存
- 成本跟踪
- 请求日志

### 3. Phoenix (Arize AI)
- 开源 LLM 观测平台
- Embedding 可视化
- Drift 检测

### 4. LangFuse
- 开源 LLM 工程平台
- Trace 和 Debug
- 成本分析

### 集成方式

通过自定义 Plugin 集成：

```python
from odin import AgentPlugin

class HeliconePlugin(AgentPlugin):
    """集成 Helicone 监控"""

    async def execute_tool(self, tool_name: str, **kwargs):
        # 在工具执行前后添加 Helicone 追踪
        with helicone.trace(tool_name):
            return await super().execute_tool(tool_name, **kwargs)
```

---

## 性能优化

### 1. 采样策略

对于高吞吐量应用，启用采样减少开销：

```python
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

# 只采样 10% 的 trace
sampler = TraceIdRatioBased(0.1)
```

### 2. 批量导出

默认配置已优化批量导出，如需调整：

```python
from opentelemetry.sdk.trace.export import BatchSpanProcessor

processor = BatchSpanProcessor(
    exporter,
    max_queue_size=2048,
    schedule_delay_millis=5000,  # 5秒批量一次
)
```

### 3. 异步导出

所有导出器使用异步处理，不会阻塞主线程。

---

## 故障排查

### 问题 1: 看不到 Traces

**检查清单**:
1. `OTEL_ENABLED=true` 已设置
2. OTLP endpoint 可访问
3. 防火墙未阻止 4317 端口
4. 查看日志中的 "OpenTelemetry setup" 消息

### 问题 2: Prometheus 无法抓取

**检查清单**:
1. HTTP 服务器已启动（查看日志）
2. 端口未被占用
3. Prometheus 配置的 target 地址正确
4. 访问 `http://localhost:9090/metrics` 手动验证

### 问题 3: 指标数据丢失

**可能原因**:
- 导出器连接失败（检查网络）
- 采样率过低
- 缓冲区溢出（增加 `max_queue_size`）

---

## 最佳实践

### 1. 开发环境
```bash
# .env.development
OTEL_ENABLED=true
ODIN_ENV=development
# 使用 console exporter，直接输出
```

### 2. 生产环境
```bash
# .env.production
OTEL_ENABLED=true
ODIN_ENV=production
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
OTEL_SERVICE_NAME=my-prod-agent
```

### 3. 指标命名规范
```python
# 使用层次化命名
metrics.increment_counter("app.feature.action")

# 使用有意义的 labels
metrics.record_latency("api.request", 0.1, labels={
    "endpoint": "/users",
    "method": "GET",
    "status": "200",
})
```

### 4. 告警规则示例

```yaml
# prometheus-rules.yml
groups:
  - name: odin_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(odin_tool_errors_total[5m]) / rate(odin_tool_executions_total[5m]) > 0.1
        for: 5m
        annotations:
          summary: "工具执行错误率超过 10%"

      - alert: HighLLMCost
        expr: increase(odin_llm_cost_total[1h]) > 10
        annotations:
          summary: "过去 1 小时 LLM 成本超过 $10"

      - alert: SlowToolExecution
        expr: histogram_quantile(0.95, rate(odin_tool_latency_bucket[5m])) > 5
        for: 10m
        annotations:
          summary: "P95 工具执行延迟超过 5 秒"
```

---

## 参考资源

- [OpenTelemetry Python 文档](https://opentelemetry-python.readthedocs.io/)
- [Prometheus 查询语法](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Grafana Dashboard 示例](https://grafana.com/grafana/dashboards/)
- [Jaeger 快速开始](https://www.jaegertracing.io/docs/latest/getting-started/)

---

**需要帮助？** 查看 `examples/monitoring_demo.py` 获取完整示例。
