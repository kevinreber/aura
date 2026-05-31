# Aura MCP Server

A Model Context Protocol server providing the productivity tools used by the Aura agent and any other MCP-compatible client (Claude Desktop, Cursor, …). Built on **FastAPI** (Python 3.11+) with **SSE transport** for the MCP protocol; tools share a Redis-backed cache with an in-memory fallback.

This package lives inside the [Aura monorepo](../../README.md). For cross-service context (architecture diagram, auth flow), read the root `CLAUDE.md` first.

## What it does

22 tools across seven domains:

| Domain | Tools | Provider |
|---|---|---|
| Weather | `weather_get_daily` | OpenWeatherMap |
| Mobility | `mobility_get_commute`, `mobility_get_commute_options`, `mobility_get_shuttle_schedule` | Google Maps + Caltrain GTFS + MV Connector |
| Calendar | `calendar_list_events`, `calendar_list_events_range`, `calendar_create_event`, `calendar_update_event`, `calendar_delete_event`, `calendar_find_free_time` | Google Calendar |
| Todos | `todo_list`, `todo_create`, `todo_update`, `todo_complete`, `todo_delete` | Todoist |
| Financial | `financial_get_data` | Alpha Vantage (stocks) + CoinGecko (crypto) |
| Weekend Orchestrator | `weekend_get_trails`, `weekend_get_concerts`, `weekend_generate_itinerary` | Google Places + Ticketmaster Discovery (fixture fallback) |
| Brain-Vault | `vault_search`, `vault_read`, `vault_list` | Git-synced clone of `~/Projects/brain-vault` (ripgrep) |

Calendar exposes a smart-scheduling helper (`find_free_time`) that ranks gaps between events. The weekend tools fall back to JSON fixtures when API keys are unset, so dev + tests stay deterministic.

## Quick Start

The simplest path is `make dev` from the monorepo root — it boots Redis + the server + the agent + the UI together.

To run only the server, from `packages/server/`:

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

uv sync --dev
cp env.example .env       # then edit
uv run python run.py      # http://localhost:8000
```

Endpoints once it's running:

| Endpoint | Purpose |
|---|---|
| `http://localhost:8000/docs` | Swagger UI (try every tool from the browser) |
| `http://localhost:8000/health` | Liveness check |
| `http://localhost:8000/tools` | Tool registry |
| `http://localhost:8000/mcp/sse` | MCP SSE transport (Cursor, raw MCP SDK) |
| `http://localhost:8000/mcp/health` | MCP transport health |

## Configuration

Every external integration is optional — tools either fall back to fixtures (weekend) or fail gracefully (vault). Set what you actually need:

| Variable | Used by | Required? |
|---|---|---|
| `WEATHER_API_KEY` | `weather_get_daily` | for real forecasts |
| `GOOGLE_MAPS_API_KEY` | `mobility_*`, `weekend_get_trails` | for real routes / trails |
| `GOOGLE_CALENDAR_CREDENTIALS_PATH` or `_JSON` | `calendar_*` | for real calendar access |
| `TODOIST_API_KEY` | `todo_*` | for real Todoist sync |
| `ALPHA_VANTAGE_API_KEY` | `financial_get_data` (stocks) | for live stock prices |
| `TICKETMASTER_API_KEY` | `weekend_get_concerts` | falls back to fixtures if unset |
| `HOME_ADDRESS`, `WORK_ADDRESS` | `mobility_get_commute_options` | for door-to-door routing |
| `HOME_CALTRAIN_STATION`, `WORK_CALTRAIN_STATION` | `mobility_*` | defaults: South SF / Mountain View |
| `WEEKEND_PREFS_PATH` | weekend tools | defaults to `data/weekend_preferences.example.json` |
| `VAULT_ROOT` | `vault_*` | path inside the container; tools return `VaultUnavailableError` if unset |
| `VAULT_GIT_URL`, `VAULT_GIT_TOKEN` | brain-vault sync | only needed in prod (see below) |
| `REDIS_URL` | all tools | falls back to in-memory cache if unset |
| `PORT` | uvicorn bind port | defaults to 8000 (Railway/Fly override) |

The full annotated set is in `env.example`.

### Caching

| Data | TTL | Reason |
|---|---|---|
| Weather geocoding | 7 days | Coordinates don't change |
| Weather forecast | 30 min | Updates frequently |
| Routes / commute | 15 min | Traffic changes |
| Stocks | 5 min | Alpha Vantage rate limit (5 calls/min) |
| Crypto | 2 min | More volatile |
| Calendar | none | Real-time accuracy required |

See [`CACHING_GUIDE.md`](./CACHING_GUIDE.md) for the full strategy.

## Brain-vault sync

The vault tools (`vault_search` / `vault_read` / `vault_list`) operate on a markdown tree mounted at `VAULT_ROOT`:

- **Local dev** — bind-mount `~/Projects/brain-vault` into the container via `docker-compose.yml`. No git sync needed; edits in Obsidian are visible immediately.
- **Production** — set `VAULT_GIT_URL` + `VAULT_GIT_TOKEN` (fine-grained PAT with `Contents: Read-only` on the vault repo). The server clones on boot if `VAULT_ROOT` is empty, then `git pull`s every **15 minutes** via an asyncio background task. Worst-case freshness end-to-end: ~30 minutes (vault → GitHub + GitHub → Fly).
- **Safety** — all paths are resolved against `VAULT_ROOT` and reject traversal. Reads cap at 1 MB. `.auraignore` (optional) excludes folders from search.

If both `VAULT_GIT_URL` and a bind-mount are detected, the server logs a warning and skips sync. Sync failures never block startup.

See [`docs/brain-vault-integration.md`](../../docs/brain-vault-integration.md) for the full rollout plan.

## MCP protocol

The server exposes its tools both as an HTTP REST API (auto-Swagger at `/docs`) and as an official MCP protocol endpoint over SSE.

### Cursor / raw MCP SDK

Point the client at `/mcp/sse`:

- Local: `http://localhost:8000/mcp/sse`
- Prod: `https://aura-mcp-server.fly.dev/mcp/sse`

### Claude Desktop

Current Claude Desktop builds **silently drop URL-based MCP entries** from `claude_desktop_config.json`. Use stdio (subprocess) instead:

```jsonc
// With the Docker stack running
{
  "mcpServers": {
    "aura": {
      "command": "docker",
      "args": ["exec", "-i", "aura-server-1", "python", "-m", "mcp_server.mcp_protocol"]
    }
  }
}

// Or with host Python
{
  "mcpServers": {
    "aura": {
      "command": "uv",
      "args": ["run", "python", "-m", "mcp_server.mcp_protocol"],
      "cwd": "/path/to/aura/packages/server"
    }
  }
}
```

> **Known caveat:** Claude Desktop's chat API rejects tool names containing dots. All Aura tools were renamed to `namespace_action` (e.g. `weather_get_daily`) for compatibility — but Claude Desktop chat may still error on tool calls in some builds. Cursor, raw MCP clients, and the Aura UI's agent are unaffected. See `CLAUDE.md` → *MCP Protocol Support* for status.

## Testing

```bash
uv run pytest                            # full suite
uv run pytest --cov=mcp_server           # with coverage
uv run pytest tests/test_tools/test_weather.py -v
```

Try a tool from the command line:

```bash
curl http://localhost:8000/health

curl -X POST http://localhost:8000/tools/weather_get_daily \
  -H "Content-Type: application/json" \
  -d '{"location": "San Francisco, CA", "when": "today"}'
```

The Swagger UI at `/docs` lets you exercise every tool from the browser — preferred over hand-rolling curl for tools with rich input schemas like `calendar_find_free_time` or `weekend_generate_itinerary`.

## Code quality

```bash
uv run black mcp_server/        # format (100 char line length)
uv run flake8 mcp_server/       # lint
uv run mypy mcp_server/         # type check
```

## Deployment

Production app: **`aura-mcp-server`** on Fly.io. `fly.toml` lives in this package; build context needs paths from `packages/server/`, so deploy from the monorepo root:

```bash
fly deploy --config packages/server/fly.toml \
  --dockerfile docker/server.Dockerfile \
  --app aura-mcp-server
```

Or via the Makefile: `make fly-server` from the monorepo root.

Set secrets with `fly secrets set KEY=value --app aura-mcp-server`. `REDIS_URL` should point at a shared Redis (Upstash, Fly Redis, etc.) so the agent and server share a cache.

Health check: Fly polls `/health` every 30s.

## Project structure

```
packages/server/
├── mcp_server/
│   ├── tools/              # weather, calendar, mobility, todo, financial, weekend, vault
│   ├── schemas/            # Pydantic input/output models per tool
│   ├── clients/            # Google Calendar, Caltrain GTFS
│   ├── utils/              # cache, http_client, logging, shuttle_data
│   ├── app.py              # FastAPI app factory (+ Swagger routes)
│   ├── server.py           # MCP tool registry + JSON-RPC handlers
│   ├── mcp_sse.py          # SSE transport
│   ├── mcp_protocol.py     # MCP SDK wrapper (stdio entry point for Claude Desktop)
│   ├── vault_sync.py       # Background git-pull task for the brain-vault
│   └── config.py           # Pydantic settings
├── tests/                  # Pytest suite (+ tests/fixtures/weekend/ for offline data)
├── fly.toml                # Fly.io deploy config
├── pyproject.toml          # Dependencies (uv)
└── run.py                  # Dev server entry point (uvicorn)
```

## Related docs

- [`CLAUDE.md`](./CLAUDE.md) — architecture, conventions, common tasks for contributors
- [`CACHING_GUIDE.md`](./CACHING_GUIDE.md) — Redis + in-memory cache details
- [`GOOGLE_CALENDAR_SETUP.md`](./GOOGLE_CALENDAR_SETUP.md) — OAuth setup for Calendar API
- [`WEEKEND_ORCHESTRATOR_SPEC.md`](./WEEKEND_ORCHESTRATOR_SPEC.md) — design spec for the weekend feature
- [`COMMUTE_INTELLIGENCE.md`](./COMMUTE_INTELLIGENCE.md) — Caltrain GTFS + shuttle integration details
- [`PRODUCTION_DEPLOYMENT.md`](./PRODUCTION_DEPLOYMENT.md) — production deployment notes
- [`CHANGELOG.md`](./CHANGELOG.md) — version history
- Monorepo [`README.md`](../../README.md) and root [`CLAUDE.md`](../../CLAUDE.md)
