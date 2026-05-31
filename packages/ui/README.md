# Aura UI

The web frontend for Aura — a real-time dashboard, conversational AI chat, weekend planner, and Google-OAuth login. Built with **React Router v7** (SSR), TypeScript, and Tailwind CSS, deployed to Vercel.

This package lives inside the [Aura monorepo](../../README.md). The UI server is the **auth boundary** for the system: all browser requests to the Agent go through `/api/v1/*` proxy routes here, which inject the shared-secret + verified-email headers before forwarding.

## Quick Start

```bash
cd packages/ui

npm install
npm run dev
# → http://localhost:5173
```

Or from the monorepo root: `make dev` runs everything in Docker.

## Required environment variables

```bash
# Backend
VITE_AI_AGENT_API_URL=http://localhost:8001  # where the Agent is reachable from the UI server

# Auth (Google OAuth — see root CLAUDE.md → Authentication)
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
SESSION_SECRET=<openssl rand -hex 32>     # cookie signing
INTERNAL_AUTH_SECRET=<openssl rand -hex 32>  # shared secret with Agent

# Allowlist (comma-separated emails)
ALLOWED_EMAILS=you@example.com

# Optional
ENVIRONMENT=development
```

`SESSION_SECRET` and `INTERNAL_AUTH_SECRET` are **required in production** — the app crashes on startup if either is missing in a production build.

## Routes

| Path | Purpose |
| --- | --- |
| `/` | Dashboard (SSR-loaded data + chat) — requires login |
| `/login` | Google OAuth sign-in |
| `/auth/google` | Initiates OAuth consent |
| `/auth/google/callback` | Exchanges code, sets session cookie |
| `/auth/logout` | Clears the session |
| `/api/v1/chat` (POST) | Proxies to Agent `/chat` with auth headers |
| `/api/v1/chat/stream` (POST) | SSE streaming chat proxy |
| `/api/v1/briefing/tomorrow` (GET) | Proxies to Agent `/briefing/tomorrow` |
| `/api/v1/preferences` (GET/PUT) | Weekend orchestrator preferences proxy |
| `/api/v1/todos` (GET) | Proxies to Agent `/tools/todos` |
| `/api/v1/financial` (POST) | Proxies to Agent `/tools/financial` |
| `/api/v1/commute-options` (POST) | Proxies to Agent `/tools/commute-options` |
| `/api/v1/shuttle` (POST) | Proxies to Agent `/tools/shuttle` |
| `/api/v1/health` (GET) | Liveness check |

Anything that polls (e.g. the financial widget) **must** go through these proxy routes — bare browser fetches to the Agent will 401.

## Key files

- `app/routes/home.tsx` — SSR loader fetches dashboard data via the server-side API client
- `app/routes/login.tsx` — Aura-branded login screen
- `app/components/Dashboard.tsx` — main dashboard layout, chat, slash commands
- `app/components/WeekendPlannerWidget.tsx` — weekend itinerary preview
- `app/components/WeekendSettings.tsx` — weekend preferences modal
- `app/lib/api.ts` — `AIAgentAPI` (client, with mock fallback) and `ServerAIAgentAPI` (server, no fallback)
- `app/lib/auth.server.ts` — Google OAuth flow + allowlist check
- `app/lib/session.server.ts` — signed session cookie
- `app/lib/agent-auth.server.ts` — header injection for the Agent
- `app/lib/agent-proxy.server.ts` — shared proxy implementation used by the `/api/v1/*` routes

## Slash commands

In the chat, type `/help` to see all available commands. Highlights:

```
/summary    # Daily morning briefing
/weather    # Current weather + forecast
/finance    # Portfolio update
/calendar   # Today's schedule
/tasks      # Todo list
/commute    # Traffic / transit
/help       # All commands
```

## Scripts

```bash
npm run dev          # Vite dev server
npm run build        # Production build
npm start            # Serve the production build
npm run typecheck    # TypeScript check
```

## Tests

```bash
npm test             # Vitest suite (includes auth.server.test.ts)
```

## Deployment (Vercel)

Auto-deploys on push to `main`. Production URL: https://daily-agent-ui.vercel.app.

Environment variables must be set in the Vercel dashboard. `VITE_AI_AGENT_API_URL` should point at the production Agent (`https://aura-agent.fly.dev`).

## Related Docs

- [`CLAUDE.md`](./CLAUDE.md) — components, patterns, common tasks
- Root [`CLAUDE.md`](../../CLAUDE.md) — auth flow, cross-service architecture
