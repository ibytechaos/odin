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

import { useState } from "react";
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
 * Chat interface with registered UI renderers
 */
function ChatWithGenerativeUI() {
  // Register chart renderer
  useCopilotAction({
    name: "create_chart",
    description: "Render an interactive chart",
    parameters: [
      { name: "component", type: "string" },
      { name: "chartType", type: "string" },
      { name: "title", type: "string" },
      { name: "data", type: "object[]" },
      { name: "xAxis", type: "string" },
      { name: "yAxis", type: "string" },
      { name: "summary", type: "object" },
    ],
    render: (props) => <ChartRenderer {...props} />,
  });

  // Register table renderer
  useCopilotAction({
    name: "create_table",
    description: "Render a data table",
    parameters: [
      { name: "component", type: "string" },
      { name: "title", type: "string" },
      { name: "columns", type: "string[]" },
      { name: "rows", type: "object[]" },
    ],
    render: (props) => <TableRenderer {...props} />,
  });

  // Register card renderer
  useCopilotAction({
    name: "create_card",
    description: "Render a card component",
    parameters: [
      { name: "component", type: "string" },
      { name: "title", type: "string" },
      { name: "content", type: "string" },
      { name: "imageUrl", type: "string" },
      { name: "actions", type: "object[]" },
    ],
    render: (props) => <CardRenderer {...props} />,
  });

  // Register progress renderer
  useCopilotAction({
    name: "create_progress",
    description: "Render a progress indicator",
    parameters: [
      { name: "component", type: "string" },
      { name: "label", type: "string" },
      { name: "current", type: "number" },
      { name: "total", type: "number" },
      { name: "percentage", type: "number" },
      { name: "status", type: "string" },
    ],
    render: (props) => <ProgressRenderer {...props} />,
  });

  // Register alert renderer
  useCopilotAction({
    name: "create_alert",
    description: "Render an alert notification",
    parameters: [
      { name: "component", type: "string" },
      { name: "type", type: "string" },
      { name: "title", type: "string" },
      { name: "message", type: "string" },
      { name: "dismissable", type: "boolean" },
    ],
    render: (props) => <AlertRenderer {...props} />,
  });

  // Register form renderer
  useCopilotAction({
    name: "create_form",
    description: "Render an interactive form",
    parameters: [
      { name: "component", type: "string" },
      { name: "title", type: "string" },
      { name: "fields", type: "object[]" },
      { name: "submitLabel", type: "string" },
    ],
    render: (props) => <FormRenderer {...props} />,
  });

  // Data tools renderers
  useCopilotAction({
    name: "get_sales_data",
    description: "Display sales data chart",
    parameters: [
      { name: "component", type: "string" },
      { name: "chartType", type: "string" },
      { name: "title", type: "string" },
      { name: "data", type: "object[]" },
      { name: "xAxis", type: "string" },
      { name: "yAxis", type: "string" },
      { name: "summary", type: "object" },
    ],
    render: (props) => <ChartRenderer {...props} />,
  });

  useCopilotAction({
    name: "get_customer_list",
    description: "Display customer table",
    parameters: [
      { name: "component", type: "string" },
      { name: "title", type: "string" },
      { name: "columns", type: "string[]" },
      { name: "rows", type: "object[]" },
    ],
    render: (props) => <TableRenderer {...props} />,
  });

  useCopilotAction({
    name: "get_product_details",
    description: "Display product card",
    parameters: [
      { name: "component", type: "string" },
      { name: "title", type: "string" },
      { name: "content", type: "string" },
      { name: "imageUrl", type: "string" },
      { name: "price", type: "string" },
      { name: "inStock", type: "boolean" },
      { name: "actions", type: "object[]" },
    ],
    render: (props) => <CardRenderer {...props} />,
  });

  useCopilotAction({
    name: "analyze_metrics",
    description: "Display metrics dashboard",
    parameters: [
      { name: "component", type: "string" },
      { name: "metric", type: "string" },
      { name: "current", type: "number" },
      { name: "previous", type: "number" },
      { name: "change", type: "number" },
      { name: "trend", type: "string" },
      { name: "chart", type: "object" },
      { name: "insights", type: "string[]" },
    ],
    render: (props) => <DashboardRenderer {...props} />,
  });

  useCopilotAction({
    name: "search_products",
    description: "Display search results",
    parameters: [
      { name: "component", type: "string" },
      { name: "query", type: "string" },
      { name: "total", type: "number" },
      { name: "results", type: "object[]" },
    ],
    render: (props) => <SearchResultsRenderer {...props} />,
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
