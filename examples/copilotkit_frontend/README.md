# CopilotKit Frontend Example

This is a minimal React/Next.js frontend to test Odin + CopilotKit integration.

## Quick Setup

### 1. Create Next.js project

```bash
npx create-next-app@latest copilotkit-frontend --typescript --tailwind --eslint --app --src-dir --use-npm
cd copilotkit-frontend
```

### 2. Install CopilotKit

```bash
npm install @copilotkit/react-core @copilotkit/react-ui
```

### 3. Replace `src/app/page.tsx`

```tsx
"use client";

import { CopilotKit } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";
import "@copilotkit/react-ui/styles.css";

export default function Home() {
  return (
    <CopilotKit runtimeUrl="http://localhost:8000/copilotkit">
      <main className="flex min-h-screen flex-col items-center justify-center p-24">
        <h1 className="text-4xl font-bold mb-8">Odin + CopilotKit Demo</h1>
        <div className="w-full max-w-2xl h-[600px] border rounded-lg overflow-hidden">
          <CopilotChat
            labels={{
              title: "Odin Assistant",
              initial: "Hi! I can help you with weather and calendar. Try asking:\n\n• What's the weather in Tokyo?\n• Create a meeting for tomorrow at 3pm\n• Show me the forecast for the next 5 days",
            }}
          />
        </div>
      </main>
    </CopilotKit>
  );
}
```

### 4. Update `src/app/layout.tsx` (remove metadata export for client component)

```tsx
import "./globals.css";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
```

### 5. Start backend (in another terminal)

```bash
cd /path/to/odin
PYTHONPATH=src uv run python examples/copilotkit_backend.py
```

### 6. Start frontend

```bash
npm run dev
```

### 7. Open browser

Go to http://localhost:3000

## What You Can Ask

The Odin backend exposes these tools:

### Weather
- "What's the weather in San Francisco?"
- "What's the temperature in Tokyo in fahrenheit?"
- "Show me the weather forecast for the next 5 days"

### Calendar
- "Create a meeting called 'Team Standup' for tomorrow at 9am"
- "Schedule a doctor appointment for next Monday at 2pm"
- "List my upcoming events"

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    Browser (localhost:3000)                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │               Next.js + CopilotKit                    │  │
│  │  ┌────────────────────────────────────────────────┐  │  │
│  │  │          <CopilotChat />                       │  │  │
│  │  │  - Renders chat UI                             │  │  │
│  │  │  - Streams responses                           │  │  │
│  │  │  - Shows tool execution                        │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP POST + SSE
                              │ /copilotkit
                              ▼
┌────────────────────────────────────────────────────────────┐
│                    Backend (localhost:8000)                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │     FastAPI + CopilotKit SDK + Odin Framework        │  │
│  │                                                       │  │
│  │  CopilotKitAdapter                                   │  │
│  │    └── Converts Odin tools → CopilotKit actions     │  │
│  │                                                       │  │
│  │  Odin Plugins                                        │  │
│  │    ├── WeatherPlugin (get_weather, get_forecast)    │  │
│  │    └── CalendarPlugin (create_event, list_events)   │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

## Troubleshooting

### CORS Error
Make sure the backend has CORS middleware enabled (it's already in copilotkit_backend.py)

### Connection Refused
Make sure the backend is running on port 8000

### Tools Not Working
Check the backend logs for errors. Tools should be listed at startup.

### CopilotKit Errors
Make sure you have the latest version: `npm update @copilotkit/react-core @copilotkit/react-ui`
