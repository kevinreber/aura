# CLAUDE.md — AI Assistant Guide for the Aura Agent

This document provides essential context for AI assistants working on the `packages/agent/` package inside the Aura monorepo.

## Project Overview

The **Aura Agent** is a Python AI agent that powers the conversational chat in the UI. It connects to the MCP Server (sibling package `packages/server/`) via the official MCP SDK over SSE, and exposes a Flask REST API the UI proxies to. Capabilities:

- Natural-language chat powered by LangChain + GPT-4o-mini (with optional Anthropic fallback)
- Weather, calendar CRUD (incl. travel-block insertion), todos (incl. create), commute intelligence, financial data
- **Weekend Orchestrator** tools — trails, concerts, multi-day itineraries
- AI-generated daily briefings
- **Defense-in-depth auth** — verifies `X-Internal-Auth` + `X-User-Email` headers from the UI proxy

The project has **two interfaces**:
1. **CLI** (`daily-ai-agent`) — Typer-based terminal commands (dev/testing)
2. **REST API** (`daily-ai-agent-api`) — Flask server on port 8001 (what the UI talks to)

## Directory Structure

```
packages/agent/
├── src/daily_ai_agent/
│   ├── __init__.py              # Package info
│   ├── main.py                  # CLI entry point (Typer)
│   ├── api.py                   # Flask REST API
│   ├── api_server.py            # API server bootstrap
│   ├── agent/
│   │   ├── orchestrator.py      # LangChain agent + tool orchestration
│   │   └── tools.py             # 17 LangChain tool implementations
│   ├── services/
│   │   ├── mcp_client.py        # MCP SDK client (SSE transport)
│   │   ├── llm.py               # OpenAI + Anthropic integrations, briefing generation
│   │   └── preferences.py       # Weekend-orchestrator preferences (JSON file)
│   └── models/
│       └── config.py            # Pydantic settings (env-based)
├── tests/                       # Pytest suite (test_api, test_tools, test_preferences)
├── pyproject.toml               # Project metadata + entry points
├── uv.lock                      # UV dependency lockfile
├── fly.toml                     # Fly.io deploy config
└── .env.example                 # Environment variable template
```

## Key Files to Understand

| File | Purpose | Read First? |
|------|---------|-------------|
| `models/config.py` | All configuration via Pydantic BaseSettings | Yes |
| `agent/tools.py` | 10 LangChain BaseTool implementations | Yes |
| `services/mcp_client.py` | MCP SDK client with SSE transport | Yes |
| `agent/orchestrator.py` | AgentOrchestrator class with LangChain agent | Yes |
| `api.py` | Flask REST endpoints with Swagger | For API work |
| `main.py` | Typer CLI commands | For CLI work |
| `services/llm.py` | OpenAI chat + briefing generation | For AI features |

## Development Commands

### Setup
```bash
uv sync                            # Install dependencies (preferred)
uv sync --extra dev                # Include dev dependencies (pytest, etc.)
pip install -e .                   # Alternative: pip install
cp .env.example .env               # Create environment file
./scripts/setup-hooks.sh           # Install git hooks (runs tests before push)
```

### CLI Commands
```bash
uv run daily-ai-agent health                    # Check MCP server connection
uv run daily-ai-agent weather [location]        # Get weather forecast
uv run daily-ai-agent todos [bucket]            # List todos (work/home/etc)
uv run daily-ai-agent commute [origin] [dest]   # Get commute info
uv run daily-ai-agent briefing [date]           # Basic morning briefing
uv run daily-ai-agent smart-briefing            # AI-powered briefing
uv run daily-ai-agent chat -m "message"         # Single chat message
uv run daily-ai-agent chat                      # Interactive chat mode
uv run daily-ai-agent demo                      # Feature demonstration
```

### API Server
```bash
uv run daily-ai-agent-api          # Start Flask server on http://localhost:8001
```

### Quality Checks
```bash
uv run pytest                      # Run tests
uv run pytest --cov=daily_ai_agent # Run with coverage
uv run mypy src/                   # Type checking
uv run black src/                  # Code formatting
uv run isort src/                  # Import sorting
```

## Required Environment Variables

```bash
# AI
OPENAI_API_KEY=your_openai_api_key_here
LLM_PROVIDER=openai                       # "openai" (default) or "anthropic"
ANTHROPIC_API_KEY=your_anthropic_key      # only needed if LLM_PROVIDER=anthropic

# MCP Server
MCP_SERVER_URL=http://localhost:8000      # set to https://aura-mcp-server.fly.dev in prod

# Auth (must match UI's INTERNAL_AUTH_SECRET + ALLOWED_EMAILS; see root CLAUDE.md)
INTERNAL_AUTH_SECRET=<openssl rand -hex 32>
ALLOWED_EMAILS=you@example.com

# User preferences
USER_NAME=Kevin
USER_LOCATION=San Francisco
DEFAULT_COMMUTE_ORIGIN=Home
DEFAULT_COMMUTE_DESTINATION=Office

# API Server configuration
HOST=0.0.0.0
PORT=8001
DEBUG=false
ENVIRONMENT=development                   # or production

# Optional: LangSmith tracing
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls_...
LANGCHAIN_PROJECT=aura
```

**Local dev shortcut:** leave `INTERNAL_AUTH_SECRET` unset and the auth check is skipped entirely. The UI still enforces login. **Never deploy with it unset.**

## Code Patterns

### 1. Tool Implementation Pattern (agent/tools.py)

All tools extend LangChain's `BaseTool`:

```python
class ExampleTool(BaseTool):
    name: str = "example_tool"
    description: str = "Clear description for LLM to understand when to use"
    args_schema: Type[BaseModel] = ExampleInput  # Pydantic model

    def _get_mcp_client(self) -> MCPClient:
        return MCPClient()

    async def _arun(self, param: str) -> str:
        """Async implementation (preferred)"""
        client = self._get_mcp_client()
        data = await client.call_tool("mcp_tool_name", {"param": param})
        return self._format_response(data)

    def _run(self, param: str) -> str:
        """Sync wrapper for async"""
        return asyncio.run(self._arun(param))
```

### 2. MCP Client Pattern (services/mcp_client.py)

Uses the official MCP SDK with SSE transport:

```python
from mcp import ClientSession
from mcp.client.sse import sse_client

async with sse_client(self.sse_url) as (read_stream, write_stream):
    async with ClientSession(read_stream, write_stream) as session:
        await session.initialize()
        result = await session.call_tool(tool_name, arguments)
        # Parse JSON from TextContent response
        return json.loads(result.content[0].text)
```

**Key features:**
- Dynamic tool discovery via `session.list_tools()`
- Retry logic with exponential backoff
- Automatic session management

### 3. CLI Command Pattern (main.py)

```python
@app.command()
def command_name(
    param: str = typer.Option("default", help="Parameter description")
):
    """Command help text shown in --help."""
    console = Console()
    result = asyncio.run(async_operation())
    console.print(Panel.fit(result, title="Title", border_style="blue"))
```

### 4. Flask API Pattern (api.py)

```python
@app.route("/endpoint", methods=["GET"])
async def endpoint_handler():
    try:
        client = MCPClient()
        data = await client.call_tool("tool_name", params)
        return jsonify({"tool": "tool_name", "data": data, "timestamp": ...})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

### 5. Configuration Access

```python
from daily_ai_agent.models.config import get_settings
settings = get_settings()  # Singleton pattern
# Access: settings.openai_api_key, settings.mcp_server_url, etc.
```

## API Endpoints (Port 8001)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Service health check |
| GET | `/tools` | List available tools |
| GET | `/docs` | Swagger UI documentation |
| POST | `/chat` | AI chat (rate limit: 10/min) |
| GET | `/briefing?type=smart` | Morning briefing |
| GET | `/tools/weather?location=SF` | Weather data |
| GET | `/tools/todos?bucket=work` | Todos (bucket optional) |
| GET | `/tools/calendar?date=YYYY-MM-DD` | Calendar events |
| GET | `/tools/commute` | Basic commute info |
| POST | `/tools/commute-options` | Enhanced commute analysis |
| POST | `/tools/shuttle` | Shuttle schedules |
| POST | `/tools/financial` | Stock/crypto prices |

## Available LangChain Tools

Defined in `agent/tools.py`. The orchestrator registers all of them by default.

| # | Tool class | Wraps MCP tool | Purpose |
|---|---|---|---|
| 1 | `WeatherTool` | `weather.get_daily` | Forecast for a location |
| 2 | `CalendarTool` | `calendar.list_events` | Events for a single date |
| 3 | `CalendarRangeTool` | `calendar.list_events_range` | Events for a date range |
| 4 | `CalendarCreateTool` | `calendar.create_event` | Create event w/ conflict check |
| 5 | `CalendarUpdateTool` | `calendar.update_event` | Update existing event |
| 6 | `CalendarDeleteTool` | `calendar.delete_event` | Delete event |
| 7 | `TodoTool` | `todo.list` | List todos (bucketed) |
| 8 | `TodoCreateTool` | `todo.create` | Create todo |
| 9 | `CommuteTool` | `mobility.get_commute` | Basic commute |
| 10 | `CommuteOptionsTool` | `mobility.get_commute_options` | Drive vs transit comparison |
| 11 | `ShuttleTool` | `mobility.get_shuttle_schedule` | MV Connector shuttle schedules |
| 12 | `FinancialTool` | `financial.get_data` | Stock + crypto prices |
| 13 | `MorningBriefingTool` | (orchestrated) | Composite daily briefing |
| 14 | `CreateTravelBlockTool` | `calendar.create_event` | Deterministic travel-time blocks |
| 15 | `TrailScoutTool` | `weekend.get_trails` | Weekend trail scouting |
| 16 | `ConcertAlertTool` | `weekend.get_concerts` | Concert listings |
| 17 | `ItineraryTool` | `weekend.generate_itinerary` | Multi-day weekend itinerary |

## Important Conventions

### Async/Await
- All external API calls use `asyncio` and `await`
- MCP client uses official MCP SDK with SSE transport
- CLI wraps async with `asyncio.run()`
- Flask uses async route handlers

### Logging
- Use `loguru` for all logging: `logger.info()`, `logger.error()`, `logger.warning()`
- Never log sensitive data (API keys, tokens)

### Error Handling
- Wrap external calls in try/except
- Handle `MCPError` for MCP protocol errors
- Return user-friendly error messages, log technical details

### Data Validation
- Use Pydantic models for all inputs
- Define `args_schema` for every LangChain tool
- Include field descriptions and examples

### Output Formatting
- CLI uses Rich: `Console`, `Panel`, `Table`
- API returns JSON with `{"tool": ..., "data": ..., "timestamp": ..., "error": ...}`

## Adding New Features

### Adding a New CLI Command

1. Add to `src/daily_ai_agent/main.py`:
```python
@app.command()
def new_command(param: str = typer.Option(...)):
    """Description."""
    result = asyncio.run(your_async_function())
    console.print(result)
```

### Adding a New LangChain Tool

1. Create Pydantic input schema in `agent/tools.py`
2. Create tool class extending `BaseTool`
3. Add MCP client method in `services/mcp_client.py` if needed
4. Register tool in `agent/orchestrator.py` tools list

### Adding a New API Endpoint

1. Add route in `api.py`
2. Use async pattern with try/except
3. Return standardized JSON response
4. Document with Swagger decorators

## Deployment

### Production URLs
- MCP Server: `https://aura-mcp-server.fly.dev`
- Agent API: `https://aura-agent.fly.dev`

### Fly.io Deployment
- `fly.toml` lives in this package
- Deploy from monorepo root: `fly deploy --config packages/agent/fly.toml --dockerfile docker/agent.Dockerfile --app aura-agent`
- Secrets via `fly secrets set KEY=value --app aura-agent`
- Health check at `/health` (Fly polls every 30s)

## Common Issues & Solutions

### "MCP server unavailable"
- Check `MCP_SERVER_URL` in `.env`
- Verify server is running: `curl $MCP_SERVER_URL/health`

### "OpenAI API key not set"
- Ensure `OPENAI_API_KEY` is in `.env`
- Required for chat, smart-briefing, and AI features

### "Timeout on calendar operations"
- MCP client has 45s timeout for Google Calendar
- This is expected for initial OAuth flows

### Rate Limiting
- Chat endpoint: 10 requests/minute per IP
- MCP server handles its own rate limits with caching

## Do's and Don'ts

### Do
- Use `uv run` for all commands
- Read existing patterns before adding new code
- Use async/await for external calls
- Add Pydantic schemas for new inputs
- Follow existing Rich formatting for CLI output

### Don't
- Don't log API keys or sensitive user data
- Don't make sync calls (use async/await with MCP SDK)
- Don't hardcode URLs (use settings)
- Don't skip error handling for external calls
- Don't add new dependencies without updating pyproject.toml

## Tech Stack Summary

| Category | Technology |
|----------|------------|
| Language | Python 3.13+ |
| Package Manager | UV (preferred), pip |
| AI Framework | LangChain + OpenAI (GPT-4o-mini) |
| MCP Client | Official MCP SDK with SSE transport |
| HTTP Client | httpx (for health checks) |
| CLI Framework | Typer + Rich |
| API Framework | Flask + Flask-CORS |
| Data Validation | Pydantic |
| Logging | Loguru |
| Deployment | Railway, Heroku-compatible |
