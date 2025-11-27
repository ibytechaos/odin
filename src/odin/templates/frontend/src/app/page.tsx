"use client";

import { CopilotKit } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";
import "@copilotkit/react-ui/styles.css";

export default function Home() {
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000/copilotkit";

  return (
    <CopilotKit runtimeUrl={backendUrl}>
      <main className="flex min-h-screen flex-col items-center justify-center p-8 bg-gradient-to-b from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-2">
            {{PROJECT_TITLE}}
          </h1>
          <p className="text-gray-600 dark:text-gray-300">
            AI Assistant powered by Odin Framework
          </p>
        </div>

        <div className="w-full max-w-2xl h-[600px] border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden shadow-xl bg-white dark:bg-gray-800">
          <CopilotChat
            labels={{
              title: "{{PROJECT_TITLE}}",
              initial: "Hi! I'm your AI assistant. How can I help you today?",
            }}
            className="h-full"
          />
        </div>

        <div className="mt-8 text-center text-sm text-gray-500 dark:text-gray-400">
          <p>
            Powered by{" "}
            <a
              href="https://github.com/yourusername/odin"
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
        </div>
      </main>
    </CopilotKit>
  );
}
