"use client";

import { CopilotKit } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";
import "@copilotkit/react-ui/styles.css";

export default function Home() {
  return (
    <CopilotKit runtimeUrl="/api/copilotkit">
      <main className="flex min-h-screen flex-col items-center justify-center p-8 bg-gradient-to-b from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-2">
            Odin Demo
          </h1>
          <p className="text-gray-600 dark:text-gray-300">
            AI Assistant with Weather, Calendar & Data Tools
          </p>
        </div>

        <div className="w-full max-w-2xl h-[600px] border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden shadow-xl bg-white dark:bg-gray-800">
          <CopilotChat
            agent="odin_agent"
            labels={{
              title: "Odin Assistant",
              initial: `Hi! I'm your AI assistant powered by Odin. Try these commands:

**Weather**
- "What's the weather in Tokyo?"
- "Show me the 5-day forecast for Paris"

**Calendar**
- "Create a meeting for tomorrow at 3pm"
- "List my upcoming events"

**Data & Reports**
- "Show me a sales report"
- "Generate a user analytics table"
- "Compare smartphones"
- "Show the sales leaderboard"

What would you like to do?`,
            }}
            className="h-full"
          />
        </div>

        <div className="mt-8 text-center text-sm text-gray-500 dark:text-gray-400">
          <p>
            Powered by{" "}
            <span className="text-blue-600">Odin Framework</span>
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
        </div>
      </main>
    </CopilotKit>
  );
}
