# Generative UI Example

This example demonstrates **Agentic Generative UI** using Odin Framework with CopilotKit's AG-UI Protocol.

## Key Concept

The magic of Generative UI is simple:

1. **Backend tools return structured data** with a `component` field
2. **Frontend registers renderers** that match tool names via `useCopilotAction`
3. **CopilotKit SDK automatically matches** tool calls to renderers

**The Agent doesn't need special prompts** - it just calls tools normally, and the SDK handles the UI rendering.

## Project Structure

```
generative-ui/
├── backend/
│   ├── main.py              # FastAPI server with CopilotKit
│   └── plugins/
│       ├── ui_tools.py      # Generic UI component tools
│       └── data_tools.py    # Business logic tools with UI output
└── frontend/
    ├── src/
    │   ├── app/
    │   │   ├── page.tsx     # Main page with tool renderers
    │   │   ├── layout.tsx   # App layout
    │   │   └── api/copilotkit/route.ts  # API proxy
    │   └── components/      # UI component renderers
    │       ├── ChartRenderer.tsx
    │       ├── TableRenderer.tsx
    │       ├── CardRenderer.tsx
    │       ├── ProgressRenderer.tsx
    │       ├── AlertRenderer.tsx
    │       ├── FormRenderer.tsx
    │       ├── DashboardRenderer.tsx
    │       └── SearchResultsRenderer.tsx
    └── package.json
```

## Quick Start

### 1. Start the Backend

```bash
cd backend

# Install dependencies (if not already installed)
pip install -e ../../../  # Install odin from source

# Run the server
python main.py
```

The backend will start at `http://localhost:8000`.

### 2. Start the Frontend

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

The frontend will start at `http://localhost:3000`.

### 3. Try It Out

Open http://localhost:3000 and try these prompts:

- **Charts**: "Show me sales data for this week"
- **Tables**: "List all customers"
- **Cards**: "Show iPhone 15 Pro details"
- **Dashboard**: "Analyze revenue metrics"
- **Search**: "Search for laptops"

## How It Works

### Backend: Tools Return UI Data

```python
@tool
def get_sales_data(self, period: str = "week") -> dict:
    """Get sales data and return as a chart."""
    # ... fetch/calculate data ...

    return {
        "component": "chart",      # UI component type
        "chartType": "bar",
        "title": f"Sales Data ({period})",
        "data": chart_data,
        "xAxis": "name",
        "yAxis": "value",
    }
```

### Frontend: Register Matching Renderers

```typescript
function ChatWithGenerativeUI() {
  // Register renderer that matches tool name
  useCopilotAction({
    name: "get_sales_data",  // Must match backend tool name
    parameters: [...],
    render: (props) => <ChartRenderer {...props} />,
  });

  return <CopilotChat agent="odin_agent" />;
}
```

### The SDK Magic

When the agent calls `get_sales_data`:
1. Tool executes and returns structured data
2. CopilotKit matches the tool name to the registered action
3. The `render` function receives the tool's return value as props
4. React component renders the interactive UI

## Available Tools

### UI Tools (ui_tools.py)

| Tool | Description | UI Component |
|------|-------------|--------------|
| `create_chart` | Create interactive charts | Bar/Line/Pie Chart |
| `create_table` | Create data tables | Sortable Table |
| `create_card` | Create info cards | Card with actions |
| `create_progress` | Show progress | Progress bar |
| `create_alert` | Show notifications | Alert message |
| `create_form` | Create forms | Interactive form |

### Data Tools (data_tools.py)

| Tool | Description | UI Component |
|------|-------------|--------------|
| `get_sales_data` | Fetch sales metrics | Bar Chart |
| `get_customer_list` | Fetch customer data | Data Table |
| `get_product_details` | Fetch product info | Product Card |
| `analyze_metrics` | Analyze business metrics | Dashboard |
| `search_products` | Search product catalog | Search Results |

## Key Patterns

### Pattern 1: Generic UI Tools

Create generic tools that the agent can use to build any UI:

```python
@tool
def create_chart(self, data: list[dict], chart_type: str = "bar", ...) -> dict:
    return {"component": "chart", "chartType": chart_type, "data": data, ...}
```

### Pattern 2: Business Logic with UI Output

Business tools that naturally return UI-ready data:

```python
@tool
def get_sales_data(self, period: str) -> dict:
    data = self.database.fetch_sales(period)  # Real business logic
    return {"component": "chart", "data": data, ...}  # UI-ready output
```

### Pattern 3: Multiple Renderers per Component Type

Register the same renderer for different tools:

```typescript
// Both tools use ChartRenderer
useCopilotAction({ name: "create_chart", render: (p) => <ChartRenderer {...p} /> });
useCopilotAction({ name: "get_sales_data", render: (p) => <ChartRenderer {...p} /> });
```

## Customization

### Adding New UI Components

1. Create a new renderer in `frontend/src/components/`:

```typescript
export function MyRenderer({ title, data }: MyRendererProps) {
  return <div>{/* Your UI */}</div>;
}
```

2. Add a backend tool that returns matching data:

```python
@tool
def my_tool(self, ...) -> dict:
    return {"component": "my_component", "title": "...", "data": [...]}
```

3. Register the renderer in `page.tsx`:

```typescript
useCopilotAction({
  name: "my_tool",
  parameters: [...],
  render: (props) => <MyRenderer {...props} />,
});
```

## Environment Variables

### Backend

No environment variables required for the demo. For production, configure:

- `ODIN_LLM_PROVIDER`: LLM provider (default: openai)
- `ODIN_LLM_MODEL`: Model name (default: gpt-4)
- `OPENAI_API_KEY`: OpenAI API key

### Frontend

- `BACKEND_URL`: Backend URL (default: http://localhost:8000/copilotkit)

## Troubleshooting

### "Tool not found" errors

Ensure the tool name in `useCopilotAction` exactly matches the backend tool function name.

### UI not rendering

Check browser console for errors. Ensure the `render` prop is returning a valid React component.

### CORS errors

The backend has CORS enabled for all origins in development. For production, configure `allow_origins` appropriately.

## Learn More

- [Odin Framework Documentation](../../../docs/)
- [CopilotKit Documentation](https://docs.copilotkit.ai/)
- [AG-UI Protocol](https://docs.copilotkit.ai/coagents/generative-ui)
