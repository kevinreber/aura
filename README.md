# Aura

Unified monorepo for the Aura productivity platform — a personal AI assistant with a real-time dashboard, conversational chat, calendar/todo CRUD, commute intelligence, and a weekend orchestrator.

## Quick Start

    cp .env.example .env
    # Edit .env with your API keys + auth secrets (see CLAUDE.md for details)
    make dev

The first `make dev` will fail fast if `SESSION_SECRET`, `INTERNAL_AUTH_SECRET`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, or `ALLOWED_EMAILS` are missing. Generate the two secrets with `openssl rand -hex 32`.

## Services

| Service | URL                   | Description                                |
| ------- | --------------------- | ------------------------------------------ |
| UI      | http://localhost:5173 | React Router v7 frontend (auth boundary)   |
| Agent   | http://localhost:8001 | LangChain AI agent (Flask, internal-only)  |
| Server  | http://localhost:8000 | MCP Server (FastAPI, productivity tools)   |
| Redis   | localhost:6379        | Cache layer for server tools               |

## Production (Fly.io)

Both Python services are deployed to Fly.io from the monorepo root:

    fly deploy --config packages/server/fly.toml --dockerfile docker/server.Dockerfile --app aura-mcp-server
    fly deploy --config packages/agent/fly.toml  --dockerfile docker/agent.Dockerfile  --app aura-agent

The UI is deployed to Vercel (auto-deploy from `main`).

| Service    | Production URL                          |
| ---------- | --------------------------------------- |
| UI         | https://daily-agent-ui.vercel.app       |
| Agent      | https://aura-agent.fly.dev              |
| MCP Server | https://aura-mcp-server.fly.dev         |

## Authentication

Aura is a **single-user app** gated by Google OAuth + an email allowlist. The UI is the auth boundary; the Agent is internal. See `CLAUDE.md` → *Authentication* for the full flow.

Browser calls never hit the Agent directly — they go through `/api/v1/*` routes on the UI server, which inject the shared-secret + verified-email headers before forwarding.

## Commands

    make dev    # Start all services
    make down   # Stop all services
    make logs   # View logs
    make build  # Rebuild images
    make clean  # Remove containers, volumes, images

## Packages

- `packages/server` — MCP Server (FastAPI). Weather, calendar CRUD, todos, commute, financial, **weekend orchestrator** (trails / concerts / itineraries).
- `packages/agent` — AI Agent (LangChain + GPT-4o-mini). Wraps MCP tools, runs the chat loop, exposes a Flask REST API.
- `packages/ui` — Web frontend (React Router v7, Tailwind). Dashboard, chat, weekend planner widget, login.

## 🤖 Claude Code Integration

This project includes custom Claude Code skills and hooks for enhanced development:

```bash
./.claude/setup.sh
```

See [.claude/README.md](.claude/README.md) and [.claude/QUICKSTART.md](.claude/QUICKSTART.md).

## Documentation

- **CLAUDE.md** — architecture, auth flow, env vars, common tasks
- **packages/server/CLAUDE.md** — server tools, caching, MCP protocol
- **packages/agent/CLAUDE.md** — LangChain tools, orchestration, preferences
- **packages/ui/CLAUDE.md** — components, routing, auth proxy
- **packages/server/WEEKEND_ORCHESTRATOR_SPEC.md** — weekend feature spec
- **packages/agent/ORCHESTRATOR_DESIGN.md** — orchestrator design notes
