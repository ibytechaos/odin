# 生成式UI (Generative UI)

Odin + CopilotKit 支持通过Agent动态生成React组件，实现真正的交互式AI界面。

## 什么是生成式UI？

生成式UI允许你的Agent不仅返回文本，还能返回**可交互的React组件**，例如：
- 📊 数据可视化图表
- 📋 表格和列表
- 🔘 按钮和表单
- 🎨 自定义UI组件

## 基础示例

### 1. 后端：创建生成UI的工具

在 `plugins/data_viz.py` 中：

```python
from odin.decorators import tool
from typing import List, Dict

@tool
def create_chart(data: List[Dict[str, any]], chart_type: str = "bar") -> dict:
    """创建数据可视化图表

    Args:
        data: 图表数据，例如 [{"name": "A", "value": 10}, {"name": "B", "value": 20}]
        chart_type: 图表类型 (bar, line, pie)

    Returns:
        生成式UI渲染数据
    """
    return {
        "type": "chart",
        "chartType": chart_type,
        "data": data,
        "title": f"{chart_type.title()} Chart"
    }

@tool
def create_table(rows: List[Dict], columns: List[str]) -> dict:
    """创建数据表格

    Args:
        rows: 表格行数据
        columns: 列名列表

    Returns:
        生成式UI渲染数据
    """
    return {
        "type": "table",
        "columns": columns,
        "rows": rows
    }

@tool
def create_product_card(name: str, price: float, image_url: str, description: str) -> dict:
    """创建产品卡片

    Args:
        name: 产品名称
        price: 价格
        image_url: 图片URL
        description: 产品描述

    Returns:
        生成式UI渲染数据
    """
    return {
        "type": "product_card",
        "name": name,
        "price": price,
        "imageUrl": image_url,
        "description": description
    }
```

### 2. 前端：使用 `useCopilotAction` 接收UI

在 `frontend/src/app/page.tsx` 中：

```typescript
"use client";

import { useCopilotAction, useCopilotChat } from "@copilotkit/react-core";
import { CopilotKit } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";
import "@copilotkit/react-ui/styles.css";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

function ChatInterface() {
  // 注册图表渲染action
  useCopilotAction({
    name: "create_chart",
    description: "Render a data visualization chart",
    parameters: [
      {
        name: "data",
        type: "object[]",
        description: "Chart data points",
        required: true,
      },
      {
        name: "chartType",
        type: "string",
        description: "Type of chart (bar, line, pie)",
        required: false,
      },
    ],
    render: ({ data, chartType }) => {
      return (
        <div className="p-4 bg-white rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4">{chartType} Chart</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={data}>
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="value" fill="#8884d8" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      );
    },
  });

  // 注册表格渲染action
  useCopilotAction({
    name: "create_table",
    description: "Render a data table",
    parameters: [
      {
        name: "rows",
        type: "object[]",
        description: "Table row data",
        required: true,
      },
      {
        name: "columns",
        type: "string[]",
        description: "Column names",
        required: true,
      },
    ],
    render: ({ rows, columns }) => {
      return (
        <div className="overflow-x-auto">
          <table className="min-w-full bg-white border">
            <thead>
              <tr>
                {columns.map(col => (
                  <th key={col} className="border px-4 py-2">{col}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={i}>
                  {columns.map(col => (
                    <td key={col} className="border px-4 py-2">{row[col]}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    },
  });

  // 注册产品卡片action
  useCopilotAction({
    name: "create_product_card",
    description: "Render a product card",
    parameters: [
      { name: "name", type: "string", required: true },
      { name: "price", type: "number", required: true },
      { name: "imageUrl", type: "string", required: true },
      { name: "description", type: "string", required: true },
    ],
    render: ({ name, price, imageUrl, description }) => {
      return (
        <div className="max-w-sm bg-white rounded-lg shadow-lg overflow-hidden">
          <img src={imageUrl} alt={name} className="w-full h-48 object-cover" />
          <div className="p-4">
            <h3 className="text-xl font-semibold">{name}</h3>
            <p className="text-gray-600 mt-2">{description}</p>
            <p className="text-2xl font-bold mt-4">${price}</p>
            <button className="mt-4 w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700">
              Add to Cart
            </button>
          </div>
        </div>
      );
    },
  });

  return (
    <CopilotChat
      agent="odin_agent"
      labels={{
        title: "Generative UI Demo",
        initial: "Try asking me to:\n- Create a sales chart\n- Show a product table\n- Display a product card",
      }}
      className="h-full"
    />
  );
}

export default function Home() {
  return (
    <CopilotKit runtimeUrl="/api/copilotkit">
      <main className="flex h-screen">
        <ChatInterface />
      </main>
    </CopilotKit>
  );
}
```

### 3. 安装图表库

```bash
cd frontend
npm install recharts
```

## 测试生成式UI

重启应用后，在聊天框尝试：

**示例1：生成图表**
```
用户: 帮我创建一个销售数据的柱状图
Agent: [调用create_chart工具]
结果: 页面上出现交互式图表
```

**示例2：生成表格**
```
用户: 展示最近的订单列表
Agent: [调用create_table工具]
结果: 页面上出现数据表格
```

**示例3：生成产品卡片**
```
用户: 给我推荐一款iPhone
Agent: [调用create_product_card工具]
结果: 页面上出现产品卡片，带图片、价格和购买按钮
```

## 高级用法

### 1. 交互式组件

你可以在生成的UI中添加交互逻辑：

```typescript
useCopilotAction({
  name: "create_interactive_form",
  parameters: [/* ... */],
  render: ({ fields }) => {
    const [formData, setFormData] = useState({});

    const handleSubmit = async (e) => {
      e.preventDefault();
      // 调用后端API
      const response = await fetch('/api/submit', {
        method: 'POST',
        body: JSON.stringify(formData),
      });
      alert('Form submitted!');
    };

    return (
      <form onSubmit={handleSubmit}>
        {fields.map(field => (
          <input
            key={field.name}
            type={field.type}
            placeholder={field.label}
            onChange={(e) => setFormData({
              ...formData,
              [field.name]: e.target.value
            })}
          />
        ))}
        <button type="submit">Submit</button>
      </form>
    );
  },
});
```

### 2. 实时数据更新

使用 `useState` 和 `useEffect` 实现实时更新：

```typescript
useCopilotAction({
  name: "create_live_dashboard",
  parameters: [/* ... */],
  render: ({ metricName }) => {
    const [data, setData] = useState(null);

    useEffect(() => {
      const interval = setInterval(async () => {
        const response = await fetch(`/api/metrics/${metricName}`);
        const newData = await response.json();
        setData(newData);
      }, 5000); // 每5秒更新

      return () => clearInterval(interval);
    }, [metricName]);

    return (
      <div className="p-4 bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-lg">
        <h2 className="text-2xl font-bold">{metricName}</h2>
        <p className="text-4xl font-bold mt-4">{data?.value || 'Loading...'}</p>
      </div>
    );
  },
});
```

### 3. 多步骤UI流程

创建向导式的多步骤体验：

```typescript
useCopilotAction({
  name: "create_wizard",
  parameters: [{ name: "steps", type: "object[]" }],
  render: ({ steps }) => {
    const [currentStep, setCurrentStep] = useState(0);

    return (
      <div className="max-w-2xl mx-auto">
        <div className="mb-8">
          {steps.map((step, i) => (
            <div
              key={i}
              className={`inline-block px-4 py-2 ${
                i === currentStep ? 'bg-blue-600 text-white' : 'bg-gray-200'
              }`}
            >
              Step {i + 1}: {step.title}
            </div>
          ))}
        </div>

        <div className="p-6 bg-white rounded-lg shadow">
          <h3 className="text-xl font-semibold">{steps[currentStep].title}</h3>
          <p className="mt-4">{steps[currentStep].content}</p>

          <div className="mt-6 flex justify-between">
            <button
              onClick={() => setCurrentStep(Math.max(0, currentStep - 1))}
              disabled={currentStep === 0}
              className="px-4 py-2 bg-gray-300 rounded disabled:opacity-50"
            >
              Previous
            </button>
            <button
              onClick={() => setCurrentStep(Math.min(steps.length - 1, currentStep + 1))}
              disabled={currentStep === steps.length - 1}
              className="px-4 py-2 bg-blue-600 text-white rounded disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    );
  },
});
```

## 完整示例项目

查看 `examples/generative-ui/` 目录获取完整的示例代码，包括：
- 📊 销售仪表板
- 🛍️ 电商产品展示
- 📝 表单向导
- 📈 实时数据监控

## 最佳实践

### 1. 保持工具返回结构一致

```python
# ✓ 好的做法
@tool
def create_ui_component(...) -> dict:
    return {
        "type": "component_name",
        "data": {...}
    }

# ✗ 避免
@tool
def create_ui_component(...) -> dict:
    return {"random": "structure"}  # 难以在前端处理
```

### 2. 使用类型安全的参数

```typescript
// ✓ 明确参数类型
useCopilotAction({
  name: "render_chart",
  parameters: [
    { name: "data", type: "object[]", required: true },
    { name: "type", type: "string", enum: ["bar", "line", "pie"] },
  ],
  render: ({ data, type }) => {/* ... */},
});
```

### 3. 错误处理

```typescript
useCopilotAction({
  name: "fetch_and_render",
  parameters: [/* ... */],
  render: ({ apiUrl }) => {
    const [error, setError] = useState(null);

    useEffect(() => {
      fetch(apiUrl)
        .then(res => res.json())
        .catch(err => setError(err.message));
    }, [apiUrl]);

    if (error) {
      return <div className="text-red-600">Error: {error}</div>;
    }

    return <div>/* Normal UI */</div>;
  },
});
```

## 调试技巧

### 1. 查看工具调用

打开浏览器控制台，查看Agent调用了哪些工具：

```javascript
// 在控制台运行
window.copilotKitDebug = true;
```

### 2. 后端日志

```bash
ODIN_LOG_LEVEL=DEBUG python main.py
```

### 3. 网络请求

打开开发者工具 → Network → 查看 `/api/copilotkit` 请求的响应数据。

## 相关资源

- [CopilotKit 官方文档](https://docs.copilotkit.ai)
- [AG-UI 协议规范](https://github.com/CopilotKit/AG-UI)
- [示例项目](../examples/)
