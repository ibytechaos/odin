"use client";

/**
 * Generative UI Demo - Main Page
 *
 * This demonstrates two patterns for Generative UI:
 *
 * 1. Tool-based Rendering (useCopilotAction):
 *    - Register renderers that match tool names
 *    - When agent calls a tool, its return value is passed to the renderer
 *    - Simple and direct
 *
 * 2. State-based Rendering (useCoAgent):
 *    - Agent maintains UI state
 *    - Frontend reads state and renders components
 *    - More flexible, supports real-time updates
 *
 * The key insight: Agent doesn't need special prompts to output UI format.
 * Tools naturally return structured data, and the SDK handles rendering.
 */

import { CopilotKit } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";
import { useCopilotAction } from "@copilotkit/react-core";
import "@copilotkit/react-ui/styles.css";

// Import our UI component renderers
import { ChartRenderer } from "../components/ChartRenderer";
import { TableRenderer } from "../components/TableRenderer";
import { CardRenderer } from "../components/CardRenderer";
import { ProgressRenderer } from "../components/ProgressRenderer";
import { AlertRenderer } from "../components/AlertRenderer";
import { FormRenderer } from "../components/FormRenderer";
import { DashboardRenderer } from "../components/DashboardRenderer";
import { SearchResultsRenderer } from "../components/SearchResultsRenderer";

/**
 * Map component type to renderer.
 * Tools return { component: "chart" | "table" | "card" | ... }
 * and we render the appropriate UI component.
 */
const componentRenderers: Record<string, React.ComponentType<any>> = {
  chart: ChartRenderer,
  table: TableRenderer,
  card: CardRenderer,
  progress: ProgressRenderer,
  alert: AlertRenderer,
  form: FormRenderer,
  dashboard: DashboardRenderer,
  search_results: SearchResultsRenderer,
};

/**
 * Universal renderer for all tool results.
 * Handles the CopilotKit action render props format:
 * { status, args, result, name }
 */
function UniversalRenderer({
  name,
  status,
  args,
  result,
}: {
  name: string;
  status: string;
  args: Record<string, unknown>;
  result: unknown;
}): React.ReactElement {
  // Show loading state while executing
  if (status === "inProgress" || status === "executing") {
    return (
      <div className="p-4 bg-gray-100 rounded-lg animate-pulse">
        <div className="flex items-center gap-2 mb-2">
          <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
          <span className="text-sm text-gray-600">Running {name}...</span>
        </div>
        <div className="h-32 bg-gray-200 rounded"></div>
      </div>
    );
  }

  // Parse result
  let data: Record<string, unknown> = {};
  if (result) {
    if (typeof result === "string") {
      try {
        data = JSON.parse(result);
      } catch {
        // If result is not JSON, show as text
        return (
          <div className="p-4 bg-white rounded-lg shadow border">
            <pre className="text-sm text-gray-800 whitespace-pre-wrap">
              {result}
            </pre>
          </div>
        );
      }
    } else if (typeof result === "object") {
      data = result as Record<string, unknown>;
    }
  }

  // Determine which renderer to use based on component type
  const componentType = data.component as string;
  const Renderer = componentRenderers[componentType];

  if (Renderer) {
    return <Renderer {...data} />;
  }

  // Fallback: render as JSON
  return (
    <div className="p-4 bg-white rounded-lg shadow border">
      <div className="text-sm font-semibold text-gray-600 mb-2">
        {name} result:
      </div>
      <pre className="text-xs text-gray-800 bg-gray-50 p-2 rounded overflow-auto max-h-64">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
}

/**
 * Chat interface with catch-all action renderer
 */
function ChatWithGenerativeUI() {
  // Use catch-all action to render all remote tool results
  // This captures actions from the backend (remoteEndpoints)
  useCopilotAction({
    name: "*",
    render: (props: any) => <UniversalRenderer {...props} />,
  });

  return (
    <CopilotChat
      agent="odin_agent"
      labels={{
        title: "Generative UI Demo",
        initial: `Hi! I'm an AI assistant with generative UI capabilities.

Try asking me to:
- **Charts**: "Show me sales data for this week" or "Create a bar chart"
- **Tables**: "List all customers" or "Show me the customer list"
- **Cards**: "Show iPhone 15 Pro details" or "Get product info"
- **Dashboard**: "Analyze revenue metrics" or "Show user analytics"
- **Search**: "Search for laptops" or "Find products under $500"

I'll respond with interactive UI components! `,
      }}
      className="h-full"
    />
  );
}

/**
 * Main page component
 */
export default function Home() {
  return (
    <CopilotKit runtimeUrl="/api/copilotkit">
      <main className="flex min-h-screen flex-col bg-gradient-to-b from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
        {/* Header */}
        <header className="p-6 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
          <div className="max-w-4xl mx-auto">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
              Generative UI Demo
            </h1>
            <p className="mt-2 text-gray-600 dark:text-gray-300">
              Odin Framework + CopilotKit AG-UI Protocol
            </p>
          </div>
        </header>

        {/* Chat area */}
        <div className="flex-1 max-w-4xl w-full mx-auto p-6">
          <div className="h-[700px] bg-white dark:bg-gray-800 rounded-xl shadow-xl overflow-hidden border border-gray-200 dark:border-gray-700">
            <ChatWithGenerativeUI />
          </div>
        </div>

        {/* Footer */}
        <footer className="p-4 text-center text-sm text-gray-500 dark:text-gray-400">
          <p>
            Powered by{" "}
            <a
              href="https://github.com/anthropics/odin"
              className="text-blue-600 hover:underline"
              target="_blank"
              rel="noopener noreferrer"
            >
              Odin Framework
            </a>
            {" + "}
            <a
              href="https://www.copilotkit.ai/"
              className="text-blue-600 hover:underline"
              target="_blank"
              rel="noopener noreferrer"
            >
              CopilotKit
            </a>
          </p>
        </footer>
      </main>
    </CopilotKit>
  );
}
