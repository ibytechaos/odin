/**
 * CopilotKit API Route
 *
 * Environment variables:
 * - OPENAI_API_KEY: Your OpenAI API key (required)
 * - OPENAI_BASE_URL: Custom OpenAI-compatible base URL (optional)
 * - OPENAI_MODEL: Model to use (optional, default: gpt-4o-mini)
 * - BACKEND_URL: Backend URL for remote endpoints (optional)
 */

import {
  CopilotRuntime,
  OpenAIAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { NextRequest } from "next/server";
import OpenAI from "openai";

export const POST = async (req: NextRequest) => {
  const runtime = new CopilotRuntime({
    remoteEndpoints: [
      {
        url: process.env.BACKEND_URL || "http://localhost:8000/copilotkit",
      },
    ],
  });

  // Create OpenAI client with custom base URL if configured
  const openaiConfig: ConstructorParameters<typeof OpenAI>[0] = {
    apiKey: process.env.OPENAI_API_KEY,
  };

  // Support custom OpenAI-compatible endpoints (e.g., local LLM servers)
  if (process.env.OPENAI_BASE_URL) {
    openaiConfig.baseURL = process.env.OPENAI_BASE_URL;
  }

  const openai = new OpenAI(openaiConfig);

  // Create service adapter with configured OpenAI client
  const serviceAdapter = new OpenAIAdapter({
    openai,
    model: process.env.OPENAI_MODEL || "gpt-4o-mini",
  });

  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilotkit",
  });

  return handleRequest(req);
};
