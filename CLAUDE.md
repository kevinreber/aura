# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Aura** is a unified monorepo for a personal AI productivity platform. It combines three services into a full-stack application:

- **Server** (MCP Server) - Python/FastAPI backend providing productivity tools via Model Context Protocol
- **Agent** (AI Agent) - Python/LangChain orchestrator with conversational AI powered by GPT-4o-mini
- **UI** (Web Frontend) - React Router v7 application with real-time dashboard and chat interface

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
```

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

1. **UI → Agent**: HTTP requests to `/api/v1/*` endpoints
2. **Agent → Server**: MCP protocol via SSE transport (`/mcp/sse`)
3. **MCP Clients → Server**: Direct MCP/SSE connection for Claude Desktop, Cursor
4. **Server → External APIs**: Direct HTTP calls with caching

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

Currently configured for local development. Each package has deployment configurations:

- **Server**: Railway.app (see `packages/server/README.md`)
- **Agent**: Railway.app (see `packages/agent/README.md`)
- **UI**: Vercel (see `packages/ui/README.md`)

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
