# Aura AI Agent

The conversational LangChain agent that powers the Aura UI. It wraps the [MCP Server](../server/) tools as LangChain tools, runs the chat loop on top of GPT-4o-mini, and exposes a Flask REST API for the UI to talk to.

This package lives inside the [Aura monorepo](../../README.md). For cross-service context (architecture diagram, auth flow, env vars), read the root `CLAUDE.md` first.

## What it does

- **Conversational chat** — natural-language queries answered via LangChain tool calls
- **17 LangChain tools** wrapping the MCP server: weather, calendar CRUD (incl. travel-block insertion), todos (incl. create), commute, financial, weekend (trails / concerts / itineraries), and the daily briefing
- **REST API** on port 8001 — chat, chat-stream (SSE), preferences, and direct tool endpoints
- **Single-user auth** — re-validates `X-Internal-Auth` + `X-User-Email` headers from the UI proxy as defense in depth

## Quick Start

```bash
cd packages/agent

# Install deps (uv preferred)
uv sync --dev

# Run the API server (http://localhost:8001)
uv run daily-ai-agent-api
```

Or use the monorepo: `make dev` from the root runs everything in Docker.

## Required environment variables

```bash
# AI
OPENAI_API_KEY=sk-...

# MCP server (default: http://localhost:8000)
MCP_SERVER_URL=http://localhost:8000

# Auth (must match what the UI proxy sends — see root CLAUDE.md → Authentication)
INTERNAL_AUTH_SECRET=<openssl rand -hex 32>
ALLOWED_EMAILS=you@example.com,other@example.com

# Optional: LangSmith tracing
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls_...
LANGCHAIN_PROJECT=aura

# Optional: LLM swap
LLM_PROVIDER=openai          # or "anthropic"
ANTHROPIC_API_KEY=sk-ant-... # if using anthropic
OPENAI_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.1
```

For local dev, leaving `INTERNAL_AUTH_SECRET` unset disables the auth check entirely. **Never deploy with it unset.**

## CLI

The package also installs a Typer CLI for one-off commands and testing:

```bash
uv run daily-ai-agent health
uv run daily-ai-agent chat -m "What's my day looking like?"
uv run daily-ai-agent smart-briefing
uv run daily-ai-agent demo
```

## REST API

Started via `uv run daily-ai-agent-api`. Highlights:

| Method | Endpoint | Notes |
| --- | --- | --- |
| GET  | `/health` | Liveness check |
| GET  | `/docs` | Swagger UI |
| POST | `/chat` | Send a chat message |
| POST | `/chat/stream` | Streaming chat (SSE) |
| GET  | `/tools` | List available tools |
| GET  | `/tools/weather` | Direct weather call |
| GET  | `/tools/calendar` | Today's events |
| GET  | `/tools/todos` | Todoist items (optional `?bucket=`) |
| POST | `/tools/financial` | Stock / crypto prices |
| GET/PUT | `/preferences` | Weekend orchestrator preferences |

All endpoints require valid `X-Internal-Auth` + `X-User-Email` headers when `INTERNAL_AUTH_SECRET` is set. The UI's `/api/v1/*` proxy routes inject these automatically — browsers never call the Agent directly.

## Testing

```bash
uv run pytest                          # all tests
uv run pytest --cov=daily_ai_agent     # with coverage
uv run pytest tests/test_api.py -v     # specific file
```

## Deployment (Fly.io)

`fly.toml` is checked in. Deploy from the **monorepo root**:

```bash
fly deploy --config packages/agent/fly.toml \
  --dockerfile docker/agent.Dockerfile \
  --app aura-agent
```

Set secrets per-app with `fly secrets set KEY=value --app aura-agent`. The Agent's `MCP_SERVER_URL` should point at the production server (e.g. `https://aura-mcp-server.fly.dev`).

## Related Docs

- [`CLAUDE.md`](./CLAUDE.md) — architecture, conventions, tool list, common tasks
- [`ORCHESTRATOR_DESIGN.md`](./ORCHESTRATOR_DESIGN.md) — weekend / nearby-now planning design
- [`AI_AGENT_STRATEGY.md`](./AI_AGENT_STRATEGY.md) — strategy notes
- Root [`CLAUDE.md`](../../CLAUDE.md) — cross-service architecture + auth flow
