# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Aura** is a unified monorepo for a personal AI productivity platform. It combines three services into a full-stack application:

- **Server** (MCP Server) - Python/FastAPI backend providing productivity tools via Model Context Protocol. Weather, calendar CRUD, todos, commute intelligence, financial data, **Navi** the planning orchestrator (trails / concerts / itineraries).
- **Agent** (AI Agent) - Python/LangChain orchestrator with conversational AI powered by GPT-4o-mini. Wraps MCP tools as LangChain tools; exposes a Flask REST API.
- **UI** (Web Frontend) - React Router v7 application with real-time dashboard, AI chat, weekend planner, and Google-OAuth login. The UI server is the **auth boundary** — browser fetches go through its `/api/v1/*` proxy routes, never directly to the Agent.

> **Aura vs. Navi (mental model):** *Aura* is the app and the primary
> conversational agent. *Navi* is the **planning orchestrator** sub-agent
> (trails / concerts / itineraries — the feature formerly called the "Weekend
> Orchestrator"). Keep them separable: Aura *calls* Navi through a narrow
> contract so Navi can potentially be extracted into its own product later.
> Treat Navi as a component Aura invokes, not part of Aura's core. See
> [`docs/NAVI_BOUNDARY.md`](docs/NAVI_BOUNDARY.md).

### Architecture

```
┌─────────────────────┐         ┌─────────────────────┐         ┌─────────────────────┐
│   UI (Port 5173)    │  HTTP   │  Agent (Port 8001)  │ MCP/SSE │  Server (Port 8000) │
│   React Router v7   │────────▶│  LangChain + GPT    │────────▶│  MCP Server         │
│   Tailwind CSS      │         │  Tool Orchestrator  │         │  External APIs      │
│   Dashboard + Chat  │         │  Flask REST API     │         │  Redis Cache        │
└─────────────────────┘         └─────────────────────┘         └─────────────────────┘
                                                                           │
                                        ┌──────────────────────────────────┤
                                        │                                  │
                                        ▼                                  ▼
                               ┌─────────────────────┐         ┌─────────────────────┐
                               │  MCP Clients        │         │  External Services  │
                               │  • Claude Desktop   │         │  • Google Calendar  │
                               │  • Cursor           │         │  • OpenWeatherMap   │
                               │  • Other MCP Apps   │         │  • Todoist API      │
                               └─────────────────────┘         │  • Google Maps      │
                                                               │  • Financial APIs   │
                                                               └─────────────────────┘
```

The Agent communicates with the MCP Server using the official Model Context Protocol (MCP) SDK over SSE transport. External MCP clients (Claude Desktop, Cursor) can also connect directly to the server.

## Monorepo Structure

```
aura/
├── packages/
│   ├── server/          # MCP Server (Python 3.11+)
│   │   ├── mcp_server/  # Main package
│   │   ├── CLAUDE.md    # Package-specific guidance
│   │   └── README.md    # Server documentation
│   ├── agent/           # AI Agent (Python 3.13+)
│   │   ├── src/daily_ai_agent/
│   │   ├── CLAUDE.md    # Package-specific guidance
│   │   └── README.md    # Agent documentation
│   └── ui/              # Web Frontend (React Router v7)
│       ├── app/         # Application code
│       ├── CLAUDE.md    # Package-specific guidance
│       └── README.md    # UI documentation
├── docker/              # Shared Docker configurations
├── docker-compose.yml   # Multi-service orchestration
├── Makefile            # Development commands
└── .env.example        # Environment variable template
```

## Quick Start

```bash
# Setup environment
cp .env.example .env
# Edit .env with your API keys

# Start all services with Docker
make dev                 # Runs docker compose up

# Or start services individually:
make up                  # Start in background
make down                # Stop all services
make logs                # View logs
make build               # Rebuild images
```

## Service URLs

| Service | URL | Description |
|---------|-----|-------------|
| UI | http://localhost:5173 | React frontend |
| Agent | http://localhost:8001 | AI Agent API |
| Server | http://localhost:8000 | MCP Server |
| Redis | localhost:6379 | Cache layer |

## Development Commands

### Monorepo-Level Commands

```bash
make dev           # Start all services
make down          # Stop all services
make logs          # Tail logs from all services
make build         # Rebuild all Docker images
make clean         # Remove containers, volumes, images
make shell-server  # Shell into server container
make shell-agent   # Shell into agent container
make redis-cli     # Access Redis CLI
```

### Individual Package Development

Each package has its own development workflow. For package-specific commands, see:

- `packages/server/CLAUDE.md` - MCP Server development
- `packages/agent/CLAUDE.md` - AI Agent development
- `packages/ui/CLAUDE.md` - UI development

## Environment Variables

All required API keys are documented in `.env.example`. Key variables:

```bash
# Required for AI features
OPENAI_API_KEY=your_openai_key

# Required for server tools
WEATHER_API_KEY=your_openweathermap_key
GOOGLE_MAPS_API_KEY=your_google_maps_key
TODOIST_API_KEY=your_todoist_key
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key

# Personal addresses for commute features
HOME_ADDRESS=your_home_address
WORK_ADDRESS=your_work_address

# Auth (Google OAuth, single-user allowlist) — see "Authentication" section
ALLOWED_EMAILS=you@example.com
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
SESSION_SECRET=...           # openssl rand -hex 32
INTERNAL_AUTH_SECRET=...     # openssl rand -hex 32

# Weekend Orchestrator (optional — falls back to JSON fixtures if unset)
TICKETMASTER_API_KEY=...     # Concert listings via Discovery API
# Google Maps key (above) doubles as the trails/POIs provider via Places API.

# Path to weekend prefs JSON (production). Defaults to data/weekend_preferences.example.json
WEEKEND_PREFS_PATH=/data/weekend_preferences.json
```

## Authentication

Aura is currently a **single-user app** gated by Google OAuth + an email
allowlist. The UI is the auth boundary; the Agent is an internal service.

**Flow:**

1. User visits the UI → unauthenticated → redirected to `/login`
2. Clicks "Sign in with Google" → `/auth/google` builds the consent URL
3. Google redirects to `/auth/google/callback` → UI verifies CSRF state,
   exchanges code for tokens, fetches userinfo, checks `ALLOWED_EMAILS`
4. On success, the UI sets a signed session cookie (`aura_session`) and
   redirects home. Otherwise → back to `/login` with an error code.
5. Every Agent call from the UI proxy attaches:
   - `X-Internal-Auth: <INTERNAL_AUTH_SECRET>` (shared secret)
   - `X-User-Email: <verified-google-email>`
6. The Agent's `before_request` hook re-checks both headers against its
   own `INTERNAL_AUTH_SECRET` + `ALLOWED_EMAILS` (defense in depth).

**Adding/removing users:** edit `ALLOWED_EMAILS` and restart both services.
Allowlist is checked on every request, so removing an email immediately
invalidates that user's existing session.

**Bypassing for local dev:** leave `INTERNAL_AUTH_SECRET` unset on the
Agent — it will skip auth entirely. The UI still enforces login. Never
deploy with this unset.

**Future multi-tenant migration:** when you actually have a second user,
this scheme becomes per-user OAuth tokens for Todoist/Calendar plus a
`user_id` on cached data.

## Docker Architecture

### Service Dependencies

```
redis (healthcheck)
  ↓
server (healthcheck) → depends on redis
  ↓
agent (healthcheck) → depends on server
  ↓
ui → depends on agent
```

### Networking

- All services communicate via `aura-network` bridge network
- Internal service-to-service calls use service names (e.g., `http://server:8000`)
- External access via localhost ports

### Volume Mounts

Development mode mounts source code for hot-reloading:
- **server**: `./packages/server/mcp_server` → `/app/mcp_server`
- **agent**: `./packages/agent/src` → `/app/src`
- **ui**: `./packages/ui/app` and `./packages/ui/public` → `/app/app` and `/app/public`

## Key Patterns

### Service Communication

1. **Browser → UI server**: HTTP requests to `/api/v1/*` route handlers on the React Router server
2. **UI server → Agent**: The proxy routes attach `X-Internal-Auth` + `X-User-Email` and forward to the Agent. The browser **never** holds these secrets.
3. **Agent → Server**: MCP protocol via SSE transport (`/mcp/sse`)
4. **MCP Clients → Server**: Direct MCP/SSE connection for Claude Desktop, Cursor
5. **Server → External APIs**: Direct HTTP calls with caching

The UI proxy routes are: `chat`, `chat/stream`, `health`, `preferences`, `commute-options`, `shuttle`, `todos`, `financial`. SSR loaders on `home.tsx` go server-to-server directly. Anything that polls (financial, etc.) **must** go through a proxy route — bare browser fetches to the Agent will 401.

### Data Flow Example

```
User types "What's my calendar tomorrow?" in UI
  ↓
UI sends POST /api/v1/chat with message
  ↓
Agent uses LangChain to select CalendarTool
  ↓
Agent connects to Server via MCP/SSE and calls tools/call
  ↓
Server calls Google Calendar API (or returns cached data)
  ↓
Response flows back: Server → Agent → UI
  ↓
UI displays formatted calendar events
```

### Caching Strategy

- **Redis** (primary): Shared cache across server restarts
- **In-memory** (fallback): Per-service memory cache
- **TTLs**: Weather 30min, Financial 5min, Routes 15min, Geocoding 7 days
- **Calendar**: No caching (real-time accuracy required)

## Testing

Each package has its own test suite:

```bash
# Server tests (from packages/server)
uv run pytest --cov=mcp_server

# Agent tests (from packages/agent)
uv run pytest --cov=daily_ai_agent

# UI type checking (from packages/ui)
npm run typecheck
```

## Common Tasks

### Adding a New Feature

When adding a feature that spans multiple services:

1. **Start with Server**: Add tool implementation in `packages/server/mcp_server/tools/`
2. **Update Agent**: Add LangChain tool wrapper in `packages/agent/src/daily_ai_agent/agent/tools.py`
3. **Update UI**: Add widget/component in `packages/ui/app/components/`
4. **Test Integration**: Verify data flows through all layers

### Debugging Service Communication

```bash
# Check all service health
curl http://localhost:8000/health  # Server
curl http://localhost:8001/health  # Agent
curl http://localhost:5173/        # UI (should load)

# View logs for specific service
make logs | grep server
make logs | grep agent
make logs | grep ui

# Check Redis cache
make redis-cli
> KEYS *
> GET cache_key_name
```

### Working with Individual Services

When you need to work on a single service without Docker:

```bash
# Server (from packages/server)
uv sync --dev
uv run python run.py

# Agent (from packages/agent)
uv sync --dev
uv run daily-ai-agent-api

# UI (from packages/ui)
npm install
npm run dev
```

**Note**: Set appropriate environment variables for service URLs when running outside Docker.

## Important Conventions

### Package Management

- **Python packages**: Use `uv` (preferred) or `pip`
- **Node packages**: Use `npm` (do not use yarn/pnpm)
- **Dependencies**: Each package manages its own `requirements.txt` or `package.json`

### Code Style

- **Python**: Black formatter (100 char line length), MyPy type checking, Flake8 linting
- **TypeScript**: Strict mode, React Router v7 patterns
- **CSS**: Tailwind utility-first, mobile-first responsive design

### Git Workflow

The monorepo uses separate git subtrees for packages that were previously independent repositories. When working on packages:

- Make changes directly in `packages/*/` directories
- Commit at the monorepo root
- Avoid force pushes to maintain subtree history

## Deployment

- **Server**: Fly.io (`aura-mcp-server`) — see `packages/server/fly.toml`
- **Agent**: Fly.io (`aura-agent`) — see `packages/agent/fly.toml`
- **UI**: Vercel — auto-deploys on push to `main`

Both Fly apps deploy from the monorepo root (build context needs paths from `packages/*/`):

```bash
fly deploy --config packages/server/fly.toml --dockerfile docker/server.Dockerfile --app aura-mcp-server
fly deploy --config packages/agent/fly.toml  --dockerfile docker/agent.Dockerfile  --app aura-agent
```

Set Fly secrets (per-app) for everything in the env-var section above. The Agent and Server share Redis via `REDIS_URL`.

## Troubleshooting

### Services Won't Start

```bash
# Check Docker daemon is running
docker ps

# Rebuild from scratch
make clean
make build
make dev
```

### Port Conflicts

If ports 5173, 8000, 8001, or 6379 are in use:

1. Stop conflicting services
2. Or modify ports in `docker-compose.yml`

### Hot Reload Not Working

Ensure volume mounts are correct in `docker-compose.yml` and source code is in the correct directory structure.

### API Keys Missing

Check that `.env` file exists at the monorepo root with all required keys. Services inherit these via `docker-compose.yml`.

## Related Documentation

- **Server-specific**: `packages/server/CLAUDE.md` - Tool implementation, caching, API integrations
- **Agent-specific**: `packages/agent/CLAUDE.md` - LangChain tools, orchestration, AI features
- **UI-specific**: `packages/ui/CLAUDE.md` - React components, routing, styling

Each package README contains detailed usage examples and API documentation.
