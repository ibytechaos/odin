"use client";

import { CopilotKit } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";
import "@copilotkit/react-ui/styles.css";

export default function Home() {
  return (
    <CopilotKit runtimeUrl="/api/copilotkit">
      <main className="flex min-h-screen flex-col bg-gradient-to-b from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
        {/* Header */}
        <header className="p-6 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
          <div className="max-w-4xl mx-auto">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
              Odin
            </h1>
            <p className="mt-2 text-gray-600 dark:text-gray-300">
              AI Agent powered by Odin Framework
            </p>
          </div>
        </header>

        {/* Chat area */}
        <div className="flex-1 max-w-4xl w-full mx-auto p-6">
          <div className="h-[700px] bg-white dark:bg-gray-800 rounded-xl shadow-xl overflow-hidden border border-gray-200 dark:border-gray-700">
            <CopilotChat
              labels={{
                title: "Odin",
                initial: "Hi! I'm your AI assistant. How can I help you today?",
              }}
              className="h-full"
            />
          </div>
        </div>

        {/* Footer */}
        <footer className="p-4 text-center text-sm text-gray-500 dark:text-gray-400">
          <p>
            Powered by{" "}
            <a
              href="https://github.com/your-org/odin"
              className="text-blue-600 hover:underline"
              target="_blank"
              rel="noopener noreferrer"
            >
              Odin Framework
            </a>
          </p>
        </footer>
      </main>
    </CopilotKit>
  );
}
