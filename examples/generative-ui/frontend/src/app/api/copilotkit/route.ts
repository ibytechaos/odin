/**
 * CopilotKit API Route
 *
 * This Next.js API route acts as a proxy between the frontend and
 * the Python backend. It's required because CopilotKit's frontend
 * components communicate via GraphQL, while our backend uses REST.
 *
 * The CopilotRuntime handles the protocol translation automatically.
 */

import { NextRequest } from "next/server";
import {
  CopilotRuntime,
  OpenAIAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";

export const POST = async (req: NextRequest) => {
  // Create runtime with remote backend endpoint
  const runtime = new CopilotRuntime({
    remoteEndpoints: [
      {
        // Point to our Python backend running CopilotKit adapter
        url: process.env.BACKEND_URL || "http://localhost:8000/copilotkit",
      },
    ],
  });

  // Create service adapter (uses OpenAI-compatible API)
  const serviceAdapter = new OpenAIAdapter();

  // Create endpoint handler
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilotkit",
  });

  return handleRequest(req);
};
