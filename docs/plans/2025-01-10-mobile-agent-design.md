# Mobile Agent 设计文档

## 概述

将 dexter_mobile 项目的手机自动化能力迁移到 Odin 框架，采用两层架构：
- **Plugin 层**：底层原子操作 tools（MCP 风格注解，进程内调用）
- **Agent 层**：Plan & Execute 逻辑，支持三种执行模式

## 核心设计原则

1. **MCP 风格定义 + 进程内调用**：用装饰器声明工具，但不走 stdio/HTTP，直接函数调用
2. **统一动作接口 + 可插拔平台实现**：标准操作（click/swipe/input）映射到不同平台驱动
3. **双模型配置**：LLM（文本）+ VLM（视觉），都走 OpenAI 兼容协议
4. **抽象人机交互**：框架层支持"等待外部输入"，具体实现可扩展

## 架构图

```
┌─────────────────────────────────────────────────────┐
│                   Agent Layer                        │
│  ┌───────────────┬───────────────┬───────────────┐  │
│  │    ReAct      │ Plan+Adaptive │  Hierarchical │  │
│  │    Agent      │    Agent      │  ReAct Agent  │  │
│  └───────────────┴───────────────┴───────────────┘  │
├─────────────────────────────────────────────────────┤
│                   Plugin Layer                       │
│  ┌─────────────────────────────────────────────────┐│
│  │           MobilePlugin (tools)                  ││
│  │  click | input | scroll | screenshot | ...      ││
│  └─────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────┤
│                 Controller Layer                     │
│  ┌─────────────┬─────────────┬─────────────┐       │
│  │    ADB      │     HDC     │     iOS     │       │
│  │ Controller  │ Controller  │ Controller  │       │
│  └─────────────┴─────────────┴─────────────┘       │
└─────────────────────────────────────────────────────┘
```

## 目录结构

```
src/odin/
├── plugins/builtin/
│   └── mobile/
│       ├── __init__.py
│       ├── plugin.py          # MobilePlugin (tools 定义)
│       ├── controllers/
│       │   ├── __init__.py
│       │   ├── base.py        # BaseController 抽象
│       │   ├── adb.py         # ADBController
│       │   ├── hdc.py         # HDCController
│       │   └── ios.py         # IOSController
│       ├── interaction.py     # HumanInteractionHandler
│       ├── coordinates.py     # 坐标转换工具
│       └── configs/
│           └── app_map.yaml   # App 映射配置
├── agents/
│   └── mobile/
│       ├── __init__.py
│       ├── base.py            # MobileAgentBase
│       ├── react.py           # MobileReActAgent
│       ├── plan_execute.py    # MobilePlanExecuteAgent
│       └── hierarchical.py    # MobileHierarchicalAgent
```

## 组件详细设计

### 1. Controller Layer（设备控制层）

#### BaseController 抽象接口

```python
from abc import ABC, abstractmethod
from pathlib import Path

class BaseController(ABC):
    """设备控制器抽象基类"""

    @abstractmethod
    async def tap(self, x: int, y: int) -> None:
        """点击指定坐标"""

    @abstractmethod
    async def long_press(self, x: int, y: int, duration_ms: int = 1000) -> None:
        """长按指定坐标"""

    @abstractmethod
    async def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> None:
        """从(x1,y1)滑动到(x2,y2)"""

    @abstractmethod
    async def input_text(self, text: str) -> None:
        """输入文本"""

    @abstractmethod
    async def press_key(self, key: str) -> None:
        """按键（back/home/enter等）"""

    @abstractmethod
    async def screenshot(self) -> bytes:
        """截图，返回 PNG 字节"""

    @abstractmethod
    async def get_screen_size(self) -> tuple[int, int]:
        """获取屏幕尺寸 (width, height)"""

    @abstractmethod
    async def open_app(self, package: str, activity: str | None = None) -> None:
        """打开应用"""

    @abstractmethod
    async def is_connected(self) -> bool:
        """检查设备连接状态"""
```

#### 平台实现

| Controller | 平台 | 底层工具 |
|------------|------|----------|
| ADBController | Android | adb shell input/screencap |
| HDCController | Harmony OS | hdc shell uitest/screencap |
| IOSController | iOS | WebDriverAgent / tidevice |

### 2. Plugin Layer（工具层）

#### MobilePlugin Tools

```python
class MobilePlugin(DecoratorPlugin):
    """手机控制插件"""

    @tool(description="点击屏幕指定位置")
    async def click(
        self,
        x: Annotated[float, Field(description="X坐标，支持0-1归一化/0-1000千分比/像素值")],
        y: Annotated[float, Field(description="Y坐标，支持0-1归一化/0-1000千分比/像素值")],
        count: Annotated[int, Field(description="点击次数")] = 1,
    ) -> dict[str, Any]:
        ...

    @tool(description="输入文本")
    async def input_text(
        self,
        text: Annotated[str, Field(description="要输入的文本")],
        press_enter: Annotated[bool, Field(description="输入后是否按回车")] = False,
    ) -> dict[str, Any]:
        ...

    @tool(description="滑动屏幕")
    async def scroll(
        self,
        x1: Annotated[float, Field(description="起点X坐标")],
        y1: Annotated[float, Field(description="起点Y坐标")],
        x2: Annotated[float, Field(description="终点X坐标")],
        y2: Annotated[float, Field(description="终点Y坐标")],
        duration_ms: Annotated[int, Field(description="滑动持续时间(毫秒)")] = 300,
    ) -> dict[str, Any]:
        ...

    @tool(description="等待指定时间")
    async def wait(
        self,
        duration_ms: Annotated[int, Field(description="等待时间(毫秒)")],
    ) -> dict[str, Any]:
        ...

    @tool(description="打开应用")
    async def open_app(
        self,
        app_name: Annotated[str, Field(description="应用名称，支持别名如'微信'/'WeChat'")],
    ) -> dict[str, Any]:
        ...

    @tool(description="截图并返回当前屏幕状态")
    async def screenshot(self) -> dict[str, Any]:
        ...

    @tool(description="按键操作")
    async def press_key(
        self,
        key: Annotated[str, Field(description="按键名称: back/home/enter/volume_up/volume_down")],
    ) -> dict[str, Any]:
        ...

    @tool(description="请求人工介入")
    async def human_interact(
        self,
        prompt: Annotated[str, Field(description="提示用户的信息")],
        input_type: Annotated[str, Field(description="输入类型: text/confirmation")] = "text",
    ) -> dict[str, Any]:
        ...

    @tool(description="读写共享变量")
    async def variable_storage(
        self,
        action: Annotated[str, Field(description="操作: read/write/list")],
        key: Annotated[str | None, Field(description="变量名")] = None,
        value: Annotated[str | None, Field(description="变量值(write时)")] = None,
    ) -> dict[str, Any]:
        ...
```

### 3. Agent Layer（Agent 层）

#### 三种执行模式

| 模式 | 类名 | 特点 |
|------|------|------|
| ReAct | `MobileReActAgent` | 纯循环：思考→行动→观察，无预规划 |
| Plan+Adaptive | `MobilePlanExecuteAgent` | 先规划步骤，执行中根据结果动态调整 |
| Hierarchical | `MobileHierarchicalAgent` | 高层规划(App级) + 低层ReAct，失败可回溯重规划 |

#### MobileAgentBase

```python
class MobileAgentBase(ABC):
    """Mobile Agent 基类"""

    def __init__(
        self,
        plugin: MobilePlugin,
        llm_client: AsyncOpenAI,      # 文本模型
        vlm_client: AsyncOpenAI,      # 视觉模型
        interaction_handler: HumanInteractionHandler,
    ):
        ...

    @abstractmethod
    async def execute(self, task: str) -> AgentResult:
        """执行任务"""
        ...

    async def analyze_screen(self, screenshot: bytes, context: str) -> VisionAnalysis:
        """用VLM分析截图"""
        ...
```

### 4. 人机交互抽象

```python
from typing import Protocol

class HumanInteractionHandler(Protocol):
    """人机交互处理器协议"""

    async def request_input(
        self,
        prompt: str,
        input_type: str = "text",  # text/confirmation/choice
        timeout: int | None = None,
    ) -> str | None:
        """请求人工输入"""
        ...

class CLIInteractionHandler:
    """CLI 交互实现"""

    async def request_input(self, prompt: str, input_type: str = "text", timeout: int | None = None) -> str | None:
        print(f"\n[需要人工输入] {prompt}")
        return input("> ")

class GUIInteractionHandler:
    """GUI 交互实现（Tkinter）"""

    async def request_input(self, prompt: str, input_type: str = "text", timeout: int | None = None) -> str | None:
        import tkinter as tk
        from tkinter import simpledialog
        root = tk.Tk()
        root.withdraw()
        return simpledialog.askstring("人工输入", prompt)
```

### 5. 坐标转换

```python
def normalize_coordinate(value: float, dimension: int) -> int:
    """
    将坐标值转换为像素坐标

    支持三种格式：
    - 0-1: 归一化坐标，乘以维度
    - 0-1000: 千分比，除以1000再乘维度
    - >1000: 绝对像素值

    Args:
        value: 输入坐标值
        dimension: 屏幕维度（宽或高）

    Returns:
        像素坐标值
    """
    if 0 <= value <= 1:
        return int(value * dimension)
    elif 1 < value <= 1000:
        return int(value / 1000 * dimension)
    else:
        return int(min(value, dimension - 1))
```

### 6. App 映射配置

`configs/app_map.yaml`:

```yaml
# Android Apps
android:
  wechat:
    package: com.tencent.mm
    activity: .ui.LauncherUI
    aliases:
      - 微信
      - WeChat
      - weixin

  alipay:
    package: com.eg.android.AlipayGphone
    activity: .AlipayLogin
    aliases:
      - 支付宝
      - Alipay
      - zhifubao

  # ... 更多应用

# Harmony OS Apps
harmony:
  wechat:
    bundle: com.tencent.mm
    module: entry
    ability: MainAbility
    aliases:
      - 微信
      - WeChat

# iOS Apps
ios:
  wechat:
    bundle_id: com.tencent.xin
    aliases:
      - 微信
      - WeChat
```

## 配置项

```bash
# 文本模型（用于规划、推理）
ODIN_LLM_MODEL=deepseek-v3
ODIN_LLM_BASE_URL=https://api.deepseek.com/v1
ODIN_LLM_API_KEY=sk-xxx

# 视觉模型（用于截图分析）
ODIN_VLM_MODEL=qwen-vl-max
ODIN_VLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
ODIN_VLM_API_KEY=sk-xxx

# 设备控制
ODIN_MOBILE_CONTROLLER=adb           # adb | hdc | ios
ODIN_MOBILE_DEVICE_ID=emulator-5554  # 设备序列号
ODIN_MOBILE_ADB_PATH=adb             # ADB 可执行文件路径
ODIN_MOBILE_HDC_PATH=hdc             # HDC 可执行文件路径

# Agent 配置
ODIN_MOBILE_AGENT_MODE=hierarchical  # react | plan_execute | hierarchical
ODIN_MOBILE_MAX_ROUNDS=50            # 最大执行轮次
ODIN_MOBILE_TOOL_DELAY_MS=400        # 工具执行后延迟

# 人机交互
ODIN_MOBILE_INTERACTION=cli          # cli | gui
```

## 执行流程

### ReAct 模式

```
User Task
    │
    ▼
┌─────────────────────────────────────┐
│           ReAct Loop                │
│  ┌─────────────────────────────┐   │
│  │ 1. Screenshot               │   │
│  │ 2. VLM分析 + 决策           │   │
│  │ 3. 执行Tool                 │   │
│  │ 4. 观察结果                 │   │
│  │ 5. 判断是否完成             │   │
│  └─────────────────────────────┘   │
│         ↻ 循环直到完成              │
└─────────────────────────────────────┘
    │
    ▼
  Result
```

### Plan + Adaptive Execute 模式

```
User Task
    │
    ▼
┌─────────────────┐
│   LLM 规划      │ → Plan Steps [1,2,3,4,5]
└─────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│       Adaptive Execution            │
│  For each step:                     │
│    1. Screenshot                    │
│    2. VLM分析当前状态              │
│    3. 执行步骤                      │
│    4. 检查结果                      │
│    5. 如果失败/偏离 → 重新规划部分  │
└─────────────────────────────────────┘
    │
    ▼
  Result
```

### Hierarchical ReAct 模式

```
User Task
    │
    ▼
┌─────────────────┐
│  高层规划(LLM)  │ → Agent Graph [WeChat→Camera→WeChat]
└─────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│     For each Agent (App):           │
│  ┌─────────────────────────────┐   │
│  │      Low-level ReAct        │   │
│  │  (截图→VLM→Tool→观察)       │   │
│  └─────────────────────────────┘   │
│         │                           │
│         ▼                           │
│    Agent完成? ──No──→ 继续ReAct     │
│         │                           │
│        Yes                          │
│         │                           │
│         ▼                           │
│    传递变量到下一个Agent            │
└─────────────────────────────────────┘
    │
    ▼
  Result (如果任何Agent失败，可回溯重规划)
```

## 扩展性设计

### 添加新平台控制器

1. 实现 `BaseController` 接口
2. 在 `app_map.yaml` 添加对应平台配置
3. 注册到 Controller 工厂

```python
# 示例：添加 Appium 控制器
class AppiumController(BaseController):
    async def tap(self, x: int, y: int) -> None:
        await self.driver.tap([(x, y)])
    # ... 实现其他方法
```

### 添加新的人机交互方式

实现 `HumanInteractionHandler` 协议即可：

```python
class WebSocketInteractionHandler:
    def __init__(self, ws_url: str):
        self.ws_url = ws_url

    async def request_input(self, prompt: str, input_type: str, timeout: int | None) -> str | None:
        async with websockets.connect(self.ws_url) as ws:
            await ws.send(json.dumps({"type": "input_request", "prompt": prompt}))
            response = await asyncio.wait_for(ws.recv(), timeout=timeout)
            return json.loads(response).get("value")
```

## 后续计划

1. 实现 Controller 层（ADB 优先）
2. 实现 Plugin 层（tools 定义）
3. 实现 Agent 层（三种模式）
4. 添加 HDC 和 iOS 支持
5. 集成测试和文档
