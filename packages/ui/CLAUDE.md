# CLAUDE.md — AI Assistant Guide for the Aura UI

This document provides essential context for AI assistants working on the `packages/ui/` package inside the Aura monorepo.

## Project Overview

The **Aura UI** is a React Router v7 web application that serves as the frontend for the Aura AI assistant. It features a real-time dashboard with widgets (weather, finance, calendar, todos, commute, weekend planner), an AI chat interface, Google-OAuth login, and a settings modal for weekend orchestrator preferences.

**The UI server is the auth boundary for the whole system.** Browser fetches never hit the Agent directly — they go through `/api/v1/*` route handlers here, which inject `X-Internal-Auth` (shared secret) and `X-User-Email` (from the verified session) before forwarding to the Agent.

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                 Aura UI                                      │
│                          (React Router v7 + Vercel)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  Browser (Client)                     │  Node.js (Server - SSR + proxy)     │
│  ─────────────────                    │  ─────────────────────              │
│  • Dashboard.tsx (interactive)        │  • home.tsx loader (SSR data)       │
│  • WeekendPlannerWidget.tsx           │  • api.v1.*.ts (auth-gated proxies) │
│  • WeekendSettings.tsx                │  • auth.server.ts (Google OAuth)    │
│  • CommuteDashboard.tsx               │  • session.server.ts (signed cookie)│
│  • Clock.tsx                          │  • agent-auth.server.ts (headers)   │
│  • AIAgentAPI (mock-fallback client)  │  • ServerAIAgentAPI (strict server) │
└───────────────────────────────────────┴─────────────────────────────────────┘
                                        │  X-Internal-Auth + X-User-Email
                                        ▼
                              ┌─────────────────────┐
                              │   Aura Agent        │
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
packages/ui/
├── app/                          # Application source code
│   ├── components/
│   │   ├── Clock.tsx
│   │   ├── CommuteDashboard.tsx
│   │   ├── Dashboard.tsx              # Main dashboard + chat
│   │   ├── WeekendPlannerWidget.tsx   # Weekend itinerary preview
│   │   ├── WeekendSettings.tsx        # Preferences modal
│   │   ├── HabitsWidget.tsx
│   │   ├── NotesWidget.tsx
│   │   └── PomodoroWidget.tsx
│   ├── lib/
│   │   ├── api.ts                     # AIAgentAPI (client) + ServerAIAgentAPI (server)
│   │   ├── auth.server.ts             # Google OAuth flow + allowlist
│   │   ├── auth.server.test.ts        # Vitest suite for auth.server
│   │   ├── session.server.ts          # Signed session cookie
│   │   ├── agent-auth.server.ts       # Injects X-Internal-Auth + X-User-Email
│   │   └── agent-proxy.server.ts      # Shared proxy helper for /api/v1/*
│   ├── routes/
│   │   ├── home.tsx                   # SSR loader + Dashboard
│   │   ├── login.tsx                  # Aura-branded login screen
│   │   ├── auth.google.ts             # Initiates OAuth consent
│   │   ├── auth.google.callback.ts    # Exchanges code, sets cookie
│   │   ├── auth.logout.ts             # Clears session
│   │   ├── api.v1.chat.ts             # POST → Agent /chat
│   │   ├── api.v1.chat.stream.ts      # POST → Agent /chat/stream (SSE)
│   │   ├── api.v1.preferences.ts      # GET/PUT → Agent /preferences
│   │   ├── api.v1.todos.ts            # GET → Agent /tools/todos
│   │   ├── api.v1.financial.ts        # POST → Agent /tools/financial
│   │   ├── api.v1.commute-options.ts  # POST → Agent /tools/commute-options
│   │   ├── api.v1.shuttle.ts          # POST → Agent /tools/shuttle
│   │   ├── api.v1.health.ts           # GET liveness
│   │   └── api._index.ts              # API docs
│   ├── app.css
│   ├── root.tsx
│   └── routes.ts                      # Route configuration (typed)
├── scripts/
│   └── capture_pr_screenshots.mjs     # Playwright screenshot helper
├── public/
├── .env.example
├── package.json
├── react-router.config.ts             # SSR enabled
├── tsconfig.json
└── vite.config.ts
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

# Backend
VITE_AI_AGENT_API_URL=http://localhost:8001  # Agent reachable from the UI server

# Auth (Google OAuth — see root CLAUDE.md → Authentication)
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
SESSION_SECRET=<openssl rand -hex 32>        # required in production
INTERNAL_AUTH_SECRET=<openssl rand -hex 32>  # required in production; shared with Agent
ALLOWED_EMAILS=you@example.com,other@example.com

# Optional
ENVIRONMENT=development
```

`SESSION_SECRET` and `INTERNAL_AUTH_SECRET` are validated at startup — the server **will throw** if either is missing when `NODE_ENV=production`.

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

### Internal API (auth-gated proxies to the Agent)

All `/api/v1/*` routes require a valid session cookie. The proxy attaches `X-Internal-Auth` (from `INTERNAL_AUTH_SECRET`) and `X-User-Email` (from the verified session) before forwarding to the Agent.

| Endpoint | Method | Forwards to |
|----------|--------|-------------|
| `/api` | GET | (docs page) |
| `/api/v1/health` | GET | Agent `/health` |
| `/api/v1/chat` | POST | Agent `/chat` |
| `/api/v1/chat/stream` | POST | Agent `/chat/stream` (SSE) |
| `/api/v1/preferences` | GET / PUT | Agent `/preferences` |
| `/api/v1/todos` | GET | Agent `/tools/todos` |
| `/api/v1/financial` | POST | Agent `/tools/financial` |
| `/api/v1/commute-options` | POST | Agent `/tools/commute-options` |
| `/api/v1/shuttle` | POST | Agent `/tools/shuttle` |

### Server-side data fetching (SSR)

`home.tsx`'s loader uses `ServerAIAgentAPI` (server-only, no mock fallback). It calls the Agent directly from the Node runtime, so it doesn't need the proxy routes — but it **does** still attach the same auth headers via `agent-auth.server.ts`.

### Auth routes

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/login` | GET | Login screen |
| `/auth/google` | GET | Initiate OAuth consent |
| `/auth/google/callback` | GET | Exchange code, check allowlist, set cookie |
| `/auth/logout` | POST | Clear session |

### Critical rule

**Anything that polls or fetches client-side must go through a `/api/v1/*` proxy route.** Browsers don't have `INTERNAL_AUTH_SECRET`, so a direct `fetch('http://localhost:8001/...')` will 401. The financial widget regressed on this once — see commit 7092ef7.

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

1. **SSR is enabled** — initial dashboard data loads server-side. See `react-router.config.ts`.

2. **Two API clients exist**:
   - `apiClient` (client-side, in `api.ts`): mock-data fallback on error, used by widgets that poll
   - `serverApiClient` (server-side): strict, errors propagate to the loader's `Promise.allSettled`

3. **Proxy-everything pattern** — every browser-side call to the Agent goes through `/api/v1/*`. Auth headers are injected server-side. Never call the Agent directly from a component.

4. **Widgets are collapsible** — state in `collapsedWidgets` object in `Dashboard.tsx`.

5. **Mobile-first design** — some widgets auto-collapse on mobile.

6. **Path alias** — `~/` maps to `./app/` (`tsconfig.json`).

7. **Auth boundary** — see root `CLAUDE.md` → *Authentication*. The login flow lives entirely in this package; the Agent only re-validates headers.

## Related Packages

- `packages/agent` (Port 8001) — LangChain agent
- `packages/server` (Port 8000) — MCP tool server

## Troubleshooting

### Dashboard shows "Failed to load" errors
- Check the Agent is running on port 8001
- Check `VITE_AI_AGENT_API_URL` env var
- Look at the server logs — `ServerAIAgentAPI` throws with detailed messages

### Chat not responding
- Check `/api/v1/chat` is accessible (and you're logged in)
- Check the Agent is responding to `/chat`
- Check `INTERNAL_AUTH_SECRET` matches between UI + Agent

### 401s on a polling widget
- The widget is calling the Agent directly instead of via `/api/v1/*`. Browsers don't carry the internal-auth secret. Move the call through a proxy route.

### Type errors
- Run `npm run typecheck` to see all errors
- Check that interfaces match API response shapes
- React Router types are auto-generated in `.react-router/types/`
