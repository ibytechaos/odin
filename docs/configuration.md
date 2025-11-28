# 配置管理 (Configuration Management)

Odin 使用统一的配置管理系统，支持环境变量、配置文件和热加载。

## 配置系统架构

### 1. 统一配置入口

所有配置通过 `odin.config` 模块管理：

```python
from odin.config import get_settings, reload_settings

# 获取配置（单例模式，首次调用时加载）
settings = get_settings()

# 访问配置
print(settings.openai_model)  # gpt-4o-mini
print(settings.openai_base_url)  # None or custom URL

# 热加载配置（从环境变量和 .env 文件重新加载）
settings = reload_settings()
```

### 2. 配置来源优先级

配置按以下优先级加载（高到低）：

1. **环境变量** - 直接设置的环境变量
2. **.env 文件** - 项目根目录的 `.env` 文件
3. **默认值** - `settings.py` 中定义的默认值

### 3. 配置文件

#### `.env` 文件

```bash
# LLM Provider
OPENAI_API_KEY=sk-xxx
OPENAI_MODEL=gpt-4o
OPENAI_BASE_URL=https://api.openai.com/v1

# 或使用带前缀的配置
ODIN_ENV=production
ODIN_DEBUG=false
```

#### `app.yaml` 文件（可选）

用于声明式配置应用结构：

```yaml
name: my-agent
description: My AI Assistant

llm:
  provider: openai
  model: gpt-4
  api_key_env: OPENAI_API_KEY

plugins:
  - name: weather
    enabled: true
```

## 配置项说明

### LLM Provider 配置

```python
class Settings:
    # OpenAI
    openai_api_key: str | None  # 从 OPENAI_API_KEY 环境变量读取
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str | None  # 自定义 API 端点，如代理或兼容服务

    # Anthropic
    anthropic_api_key: str | None
    anthropic_model: str = "claude-sonnet-4-5-20250929"
```

### 服务器配置

```python
class Settings:
    http_host: str = "0.0.0.0"
    http_port: int = 8000
    cors_origins: list[str] = ["http://localhost:3000"]
```

### 性能配置

```python
class Settings:
    token_limit_per_request: int = 100000
    enable_semantic_cache: bool = True
    rate_limit_requests_per_minute: int = 60
```

## 配置热加载

### 场景1：开发环境实时调试

```python
from odin.config import reload_settings

# 修改 .env 文件后，无需重启服务
settings = reload_settings()
# 新配置立即生效
```

### 场景2：动态配置切换

```python
import os
from odin.config import reload_settings

# 运行时切换配置
os.environ["OPENAI_MODEL"] = "gpt-4"
settings = reload_settings()

print(settings.openai_model)  # gpt-4
```

### 场景3：API 端点动态更新

```python
# 在代码中监听配置变更
from odin.config import get_settings

def get_llm():
    settings = get_settings()
    return ChatOpenAI(
        model=settings.openai_model,
        base_url=settings.openai_base_url
    )

# 每次调用都获取最新配置
llm = get_llm()
```

## 最佳实践

### ✅ 正确做法

```python
# 1. 通过统一配置系统访问
from odin.config import get_settings

settings = get_settings()
model = settings.openai_model  # ✓

# 2. 在需要时重新获取配置
def create_llm():
    settings = get_settings()  # 每次都获取最新配置
    return ChatOpenAI(model=settings.openai_model)
```

### ❌ 错误做法

```python
# 1. 直接读取环境变量 - 绕过配置系统
import os
model = os.getenv("OPENAI_MODEL")  # ✗ 不要这样做！

# 2. 缓存配置对象 - 无法热加载
from odin.config import get_settings

SETTINGS = get_settings()  # ✗ 全局缓存，无法热加载

def create_llm():
    return ChatOpenAI(model=SETTINGS.openai_model)  # ✗ 使用过期配置
```

## 配置验证

所有配置使用 Pydantic 进行类型验证和转换：

```python
from odin.config import get_settings

settings = get_settings()

# 自动类型转换
settings.http_port  # int, 即使环境变量是字符串
settings.debug  # bool, "true"/"false" 自动转换
settings.plugin_dirs  # list[Path], 逗号分隔字符串自动解析
```

## 常见问题

### Q: 为什么我的 .env 配置没生效？

**A:** 检查以下几点：

1. `.env` 文件在项目根目录
2. 配置项名称正确（注意前缀，如 `ODIN_ENV` vs `ENV`）
3. 调用 `reload_settings()` 重新加载配置

### Q: 如何在生产环境使用不同配置？

**A:** 不使用 `.env` 文件，直接设置环境变量：

```bash
export ODIN_ENV=production
export OPENAI_API_KEY=sk-prod-xxx
export OPENAI_BASE_URL=https://your-proxy.com/v1

python -m odin serve
```

### Q: 如何实现配置的自动热加载？

**A:** 可以使用文件监听库（如 watchdog）：

```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from odin.config import reload_settings

class ConfigReloader(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('.env'):
            print("Reloading configuration...")
            reload_settings()

observer = Observer()
observer.schedule(ConfigReloader(), path='.', recursive=False)
observer.start()
```

## 配置扩展

如需添加新的配置项：

1. 在 `settings.py` 中添加字段
2. 在 `.env.example` 中添加示例
3. 更新此文档

```python
# src/odin/config/settings.py
class Settings(BaseSettings):
    # 新增配置
    custom_feature_enabled: bool = False
    custom_api_endpoint: str = "https://api.example.com"
```

```bash
# .env.example
# Custom Feature
ODIN_CUSTOM_FEATURE_ENABLED=true
ODIN_CUSTOM_API_ENDPOINT=https://api.example.com
```
