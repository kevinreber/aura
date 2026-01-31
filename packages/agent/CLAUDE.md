# CLAUDE.md - AI Assistant Guide for daily-ai-agent

This document provides essential context for AI assistants working on this codebase.

## Project Overview

**daily-ai-agent** is a production-ready Python AI agent that serves as a personal productivity assistant. It connects to an MCP (Model Context Protocol) server via HTTP to provide:

- Natural language conversations powered by LangChain + GPT-4o-mini
- Weather forecasts, calendar management, todo tracking, commute intelligence
- Financial market data (stocks and crypto)
- AI-generated morning briefings

The project has **two interfaces**:
1. **CLI** (`daily-ai-agent`) - Typer-based terminal commands
2. **REST API** (`daily-ai-agent-api`) - Flask server on port 8001

## Directory Structure

```
daily-ai-agent/
├── src/daily_ai_agent/
│   ├── __init__.py              # Package info (v0.1.0)
│   ├── main.py                  # CLI entry point (Typer)
│   ├── api.py                   # Flask REST API (main implementation)
│   ├── api_server.py            # API server bootstrap
│   ├── agent/
│   │   ├── orchestrator.py      # LangChain agent + tool orchestration
│   │   └── tools.py             # 10 LangChain tool implementations
│   ├── services/
│   │   ├── mcp_client.py        # Async HTTP client for MCP server
│   │   └── llm.py               # OpenAI integration & briefing generation
│   └── models/
│       └── config.py            # Pydantic settings (env-based config)
├── pyproject.toml               # Project metadata, dependencies, entry points
├── uv.lock                      # UV dependency lockfile
├── .env.example                 # Environment variable template
├── Procfile                     # Heroku/Railway process definition
└── railway.json                 # Railway deployment config
```

## Key Files to Understand

| File | Purpose | Read First? |
|------|---------|-------------|
| `models/config.py` | All configuration via Pydantic BaseSettings | Yes |
| `agent/tools.py` | 10 LangChain BaseTool implementations | Yes |
| `services/mcp_client.py` | HTTP client for MCP server communication | Yes |
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
# Required for AI features
OPENAI_API_KEY=your_openai_api_key_here

# MCP Server (default: http://localhost:8000)
MCP_SERVER_URL=http://localhost:8000

# User preferences
USER_NAME=Kevin
USER_LOCATION=San Francisco
DEFAULT_COMMUTE_ORIGIN=Home
DEFAULT_COMMUTE_DESTINATION=Office

# API Server configuration
HOST=0.0.0.0
PORT=8001
DEBUG=false
ENVIRONMENT=development  # or production
```

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

```python
async with httpx.AsyncClient(timeout=self.timeout) as client:
    response = await client.post(
        f"{self.base_url}/tools/{tool_name}",
        json=input_data
    )
    response.raise_for_status()
    return response.json()
```

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

1. **WeatherTool** - Get weather forecasts
2. **CalendarTool** - Get single-date calendar events
3. **CalendarRangeTool** - Get date-range calendar events
4. **CalendarCreateTool** - Create calendar events with conflict detection
5. **TodoTool** - Get todos from buckets
6. **CommuteTool** - Basic commute between locations
7. **CommuteOptionsTool** - Driving vs transit analysis
8. **ShuttleTool** - MV Connector shuttle schedules
9. **FinancialTool** - Stock/crypto prices
10. **MorningBriefingTool** - Complete morning briefing

## Important Conventions

### Async/Await
- All external API calls use `asyncio` and `await`
- MCP client uses `httpx.AsyncClient`
- CLI wraps async with `asyncio.run()`
- Flask uses async route handlers

### Logging
- Use `loguru` for all logging: `logger.info()`, `logger.error()`, `logger.warning()`
- Never log sensitive data (API keys, tokens)

### Error Handling
- Wrap external calls in try/except
- Handle `httpx.HTTPStatusError` and `httpx.TimeoutException` specifically
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
- MCP Server: `https://web-production-66f9.up.railway.app`
- AI Agent API: `https://web-production-f80730.up.railway.app`

### Railway Deployment
- Configured via `railway.json`
- Uses NIXPACKS builder
- Start command: `uv run daily-ai-agent-api`
- Environment: Set in Railway dashboard

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
- Don't make sync HTTP calls (use httpx.AsyncClient)
- Don't hardcode URLs (use settings)
- Don't skip error handling for external calls
- Don't add new dependencies without updating pyproject.toml

## Tech Stack Summary

| Category | Technology |
|----------|------------|
| Language | Python 3.13+ |
| Package Manager | UV (preferred), pip |
| AI Framework | LangChain + OpenAI (GPT-4o-mini) |
| HTTP Client | httpx (async) |
| CLI Framework | Typer + Rich |
| API Framework | Flask + Flask-CORS |
| Data Validation | Pydantic |
| Logging | Loguru |
| Deployment | Railway, Heroku-compatible |
