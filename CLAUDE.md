# CLAUDE.md - AI Assistant Guide for daily-agent-ui

This document provides essential context for AI assistants working on this codebase.

## Project Overview

**Daily Agent UI** is a React Router v7 web application that serves as the frontend interface for a personal AI assistant system. It features a real-time dashboard with widgets for weather, finance, calendar, todos, and commute information, plus an AI chat interface.

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              daily-agent-ui                                  │
│                        (React Router v7 + Vercel)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  Browser (Client)                     │  Node.js (Server - SSR)             │
│  ─────────────────                    │  ─────────────────────              │
│  • Dashboard.tsx (interactive)        │  • home.tsx loader (data fetching)  │
│  • CommuteDashboard.tsx               │  • api.v1.chat.ts (proxy)           │
│  • Clock.tsx (real-time)              │  • ServerAIAgentAPI class           │
│  • AIAgentAPI class (client)          │                                     │
└───────────────────────────────────────┴─────────────────────────────────────┘
                                        │
                                        ▼ HTTP
                              ┌─────────────────────┐
                              │   AI Agent Backend  │
                              │    (Port 8001)      │
                              └─────────────────────┘
```

## Tech Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| React | 19.1.0 | UI framework |
| React Router | 7.7.1 | Full-stack framework with SSR |
| TypeScript | 5.8.3 | Type safety |
| Tailwind CSS | 4.1.4 | Styling (utility-first) |
| Vite | 6.3.3 | Build tool & dev server |
| Vercel | - | Deployment platform |

## Directory Structure

```
daily-agent-ui/
├── app/                          # Application source code
│   ├── components/               # React components
│   │   ├── Clock.tsx            # Real-time clock widget
│   │   ├── CommuteDashboard.tsx # Commute/transit info widget
│   │   └── Dashboard.tsx        # Main dashboard with all widgets + chat
│   ├── lib/                     # Utilities and shared code
│   │   └── api.ts               # API clients (AIAgentAPI, ServerAIAgentAPI)
│   ├── routes/                  # Page and API routes
│   │   ├── home.tsx             # Main page (SSR loader + Dashboard)
│   │   ├── api.v1.chat.ts       # Chat proxy endpoint (POST)
│   │   ├── api.v1.health.ts     # Health check endpoint (GET)
│   │   └── api._index.ts        # API documentation endpoint
│   ├── welcome/                 # Welcome page assets (unused)
│   ├── app.css                  # Global styles + Tailwind imports
│   ├── root.tsx                 # App shell, layout, error boundary
│   └── routes.ts                # Route configuration
├── public/                      # Static assets (logos, favicons)
├── .env.example                 # Environment variable template
├── package.json                 # Dependencies and scripts
├── react-router.config.ts       # React Router config (SSR enabled)
├── tsconfig.json                # TypeScript configuration
└── vite.config.ts               # Vite configuration
```

## Key Files to Understand

### `app/lib/api.ts` - API Layer (Lines 1-744)
- **`AIAgentAPI`** class: Client-side API client with fallback mock data
- **`ServerAIAgentAPI`** class: Server-side API client (no mock fallbacks)
- All TypeScript interfaces for data types (WeatherData, FinancialData, etc.)
- Handles: weather, financial, calendar, todos, chat, commute data

### `app/components/Dashboard.tsx` - Main UI (Lines 1-1258)
- All dashboard widgets (weather, financial, calendar, todos)
- AI chat interface with slash commands
- Collapsible widget state management
- Chat history and message handling

### `app/routes/home.tsx` - SSR Data Loading (Lines 1-98)
- Server-side loader fetches all dashboard data
- Uses `Promise.allSettled` for graceful error handling
- Passes data as props to Dashboard component

## Development Commands

```bash
# Install dependencies
npm install

# Start development server (http://localhost:3000)
npm run dev

# Type checking
npm run typecheck

# Production build
npm run build

# Run production server
npm start
```

## Environment Variables

```bash
# .env file (copy from .env.example)
VITE_AI_AGENT_API_URL=http://localhost:8001  # AI Agent backend URL
VITE_ENVIRONMENT=development                  # development/staging/production
VITE_DEBUG=true                               # Enable debug logging
```

## Code Patterns

### 1. Route Pattern with SSR Data Loading

```typescript
// app/routes/[page].tsx
import type { Route } from "./+types/[page]";

export async function loader({ context }: Route.LoaderArgs) {
  const data = await serverApiClient.getData();
  return { data };
}

export default function Page({ loaderData }: Route.ComponentProps) {
  return <Component data={loaderData.data} />;
}
```

### 2. API Route Pattern

```typescript
// app/routes/api.v1.[endpoint].ts
export async function action({ request }: { request: Request }) {
  const body = await request.json();
  // Process request...
  return new Response(JSON.stringify({ success: true }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}
```

### 3. Widget Component Pattern

```typescript
interface WidgetProps {
  data: DataType | null;
  loading?: boolean;
  error?: string;
  collapsed?: boolean;
  onToggle?: () => void;
}

function Widget({ data, loading, error, collapsed, onToggle }: WidgetProps) {
  if (loading) return <WidgetSkeleton />;
  if (error) return <WidgetError message={error} />;
  // Render widget content...
}
```

### 4. API Client Pattern

```typescript
// Client-side: Uses mock fallbacks
const data = await apiClient.getWeather(); // Falls back to mock on error

// Server-side: No fallbacks, errors propagate
const data = await serverApiClient.getWeather(); // Throws on error
```

## Slash Commands System

The chat interface supports these slash commands (defined in `Dashboard.tsx:64-115`):

| Command | Aliases | Description |
|---------|---------|-------------|
| `/summary` | `/briefing` | Daily morning briefing |
| `/weather` | `/forecast` | Weather information |
| `/finance` | `/stocks`, `/market` | Financial portfolio |
| `/calendar` | `/schedule`, `/events` | Today's calendar |
| `/tasks` | `/todos`, `/todo` | Task list |
| `/commute` | `/traffic` | Traffic/commute info |
| `/help` | `/commands` | Show all commands |

## Styling Guidelines

### Tailwind CSS Conventions
- Mobile-first responsive design: `base` → `sm:` → `md:` → `lg:` → `xl:`
- Dark mode support: `dark:` prefix
- Component spacing: `p-3 sm:p-4 lg:p-6` for progressive sizing
- Border radius: Use `rounded-lg` or `rounded-xl` for cards

### Color Scheme
- Primary: Blue (`blue-500`, `blue-600`)
- Success: Green (`green-500`, `green-600`)
- Warning: Yellow/Orange (`yellow-500`, `orange-500`)
- Error: Red (`red-500`, `red-600`)
- Neutral: Gray scale (`gray-50` to `gray-900`)

## API Endpoints

### Internal API (Proxy to AI Agent)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api` | GET | API documentation |
| `/api/v1/health` | GET | Health check |
| `/api/v1/chat` | POST | Chat with AI (proxies to AI Agent) |

### External API (AI Agent Backend - Port 8001)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chat` | POST | Send chat message |
| `/tools/weather` | GET | Get weather data |
| `/tools/financial` | POST | Get financial data |
| `/tools/calendar` | GET | Get calendar events |
| `/tools/todos` | GET | Get todo items |
| `/tools/commute` | POST | Get basic commute info |
| `/tools/commute-options` | POST | Get driving/transit options |
| `/tools/shuttle` | POST | Get shuttle schedule |

## Common Tasks

### Adding a New Widget

1. Create component in `app/components/NewWidget.tsx`
2. Add data type interface in `app/lib/api.ts`
3. Add API method to both `AIAgentAPI` and `ServerAIAgentAPI`
4. Add mock data fallback in `AIAgentAPI`
5. Add data fetching to `app/routes/home.tsx` loader
6. Import and render in `app/components/Dashboard.tsx`

### Adding a New API Endpoint

1. Create file `app/routes/api.v1.[endpoint].ts`
2. Export `action` for POST/PUT/DELETE or `loader` for GET
3. Add route to `app/routes.ts`
4. Update API documentation in `app/routes/api._index.ts`

### Adding a Slash Command

1. Add command to `slashCommands` array in `Dashboard.tsx:64-115`
2. Define: `command`, `aliases`, `description`, `icon`, `action`
3. For special handling, update `processSlashCommand` function

## Testing Checklist

Before submitting changes:
- [ ] `npm run typecheck` passes
- [ ] `npm run build` succeeds
- [ ] Dashboard loads with all widgets
- [ ] Chat interface works with slash commands
- [ ] Mobile responsive layout works
- [ ] Dark mode styling is correct

## Deployment

### Vercel (Production)
- Auto-deploys on push to `main` branch
- Production URL: https://daily-agent-ui.vercel.app
- Environment variables set in Vercel dashboard

### Local Production Preview
```bash
npm run build
npm start  # Runs on http://localhost:3000
```

## Important Notes

1. **SSR is enabled** - The app uses server-side rendering for initial data load. Check `react-router.config.ts`.

2. **Two API clients exist**:
   - `apiClient` (client-side): Has mock data fallbacks
   - `serverApiClient` (server-side): Throws errors on failure

3. **Chat uses a proxy** - The `/api/v1/chat` endpoint proxies to the AI Agent to avoid CORS issues.

4. **Widgets are collapsible** - State is managed per-widget in `collapsedWidgets` object.

5. **Mobile-first design** - Some widgets auto-collapse on mobile for better UX.

6. **Path alias** - `~/` maps to `./app/` (configured in `tsconfig.json:17-19`)

## Related Projects

- **daily-ai-agent** (Port 8001) - AI Agent backend with LangChain
- **daily-mcp-server** (Port 8000) - MCP tool server for data APIs

## Troubleshooting

### Dashboard shows "Failed to load" errors
- Check if AI Agent backend is running on port 8001
- Check `VITE_AI_AGENT_API_URL` environment variable
- Server logs show fetch errors with detailed messages

### Chat not responding
- Check `/api/v1/chat` endpoint is accessible
- Check AI Agent backend is responding to `/chat`
- Look for CORS errors in browser console

### Type errors
- Run `npm run typecheck` to see all errors
- Check that interfaces match API response shapes
- React Router types are auto-generated in `.react-router/types/`
