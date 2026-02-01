# CLAUDE.md - AI Assistant Guide for Daily MCP Server

This document provides essential context for AI assistants working on this codebase.

## Project Overview

Daily MCP Server is a Model Context Protocol (MCP) server providing productivity tools for AI agents. Built with FastAPI and Python 3.11+, it offers real-time integrations with external APIs for weather, calendar, todos, commute intelligence, and financial data.

**Key Characteristics:**
- FastAPI server with native async support and auto-generated Swagger/OpenAPI docs
- Official MCP protocol support via SSE transport (sse-starlette)
- Real API integrations (Google Calendar, OpenWeatherMap, Google Maps, Todoist, Alpha Vantage)
- Intelligent caching with Redis primary and in-memory fallback
- Production deployed on Railway.app

## Codebase Structure

```
daily-mcp-server/
├── mcp_server/                 # Main application package
│   ├── app.py                  # FastAPI application with auto-generated Swagger docs
│   ├── server.py               # MCP protocol implementation and tool registry
│   ├── mcp_sse.py              # SSE transport for MCP protocol clients
│   ├── mcp_protocol.py         # MCP SDK wrapper for tool integration
│   ├── config.py               # Pydantic-based configuration with env var support
│   ├── tools/                  # Individual tool implementations
│   │   ├── weather.py          # OpenWeatherMap integration
│   │   ├── calendar.py         # Google Calendar CRUD operations
│   │   ├── mobility.py         # Google Maps + Caltrain + Shuttle integration
│   │   ├── todo.py             # Todoist integration
│   │   └── financial.py        # Alpha Vantage + CoinGecko integration
│   ├── schemas/                # Pydantic input/output models
│   │   ├── weather.py
│   │   ├── calendar.py
│   │   ├── mobility.py
│   │   ├── todo.py
│   │   └── financial.py
│   ├── clients/                # External API clients
│   │   ├── google_calendar.py  # Google Calendar API wrapper
│   │   └── caltrain.py         # Caltrain GTFS data client
│   └── utils/                  # Shared utilities
│       ├── cache.py            # Redis + in-memory caching
│       ├── http_client.py      # Async HTTP client wrapper
│       ├── logging.py          # Loguru-based logging
│       └── shuttle_data.py     # MV Connector shuttle schedules
├── tests/                      # Pytest test suite
│   ├── conftest.py             # Fixtures and test configuration
│   ├── test_app.py             # Application-level tests
│   └── test_tools/             # Tool-specific tests
├── pyproject.toml              # Project metadata and dependencies (UV/pip)
├── run.py                      # Development server entry point
└── env.example                 # Environment variable template
```

## Available Tools

The server provides 15 tools organized by domain:

| Tool | Type | Description |
|------|------|-------------|
| `weather.get_daily` | Read | Weather forecast via OpenWeatherMap |
| `mobility.get_commute` | Read | Basic commute info via Google Maps |
| `mobility.get_commute_options` | Read | Comprehensive commute analysis (driving + transit) |
| `mobility.get_shuttle_schedule` | Read | MV Connector shuttle schedules |
| `calendar.list_events` | Read | List events for a date |
| `calendar.list_events_range` | Read | List events for date range |
| `calendar.create_event` | Write | Create event with conflict detection |
| `calendar.update_event` | Write | Update existing event |
| `calendar.delete_event` | Write | Delete event |
| `calendar.find_free_time` | Read | Find available time slots |
| `todo.list` | Read | List todos from Todoist |
| `todo.create` | Write | Create todo with natural language dates |
| `todo.update` | Write | Update todo |
| `todo.complete` | Write | Mark todo complete/incomplete |
| `todo.delete` | Write | Delete todo |
| `financial.get_data` | Read | Stock/crypto prices |

## Development Commands

### Setup
```bash
# Recommended: Use UV for faster dependency management
uv sync --dev

# Traditional pip
pip install -r requirements.txt -r requirements-dev.txt
```

### Running the Server
```bash
# With UV
uv run python run.py

# Traditional
python run.py

# Or directly with uvicorn
uvicorn mcp_server.app:app --host 0.0.0.0 --port 8000 --reload

# Server starts at http://localhost:8000
# Swagger UI at http://localhost:8000/docs
# ReDoc at http://localhost:8000/redoc
```

### Testing
```bash
# Run all tests
uv run pytest

# With coverage
uv run pytest --cov=mcp_server --cov-report=html

# Specific test file
uv run pytest tests/test_tools/test_weather.py -v
```

### Code Quality
```bash
# Format code (Black, 100 char line length)
uv run black mcp_server/

# Lint
uv run flake8 mcp_server/

# Type check
uv run mypy mcp_server/
```

## Key Conventions

### Tool Implementation Pattern

Each tool follows this structure in `mcp_server/tools/`:

```python
class ToolName:
    def __init__(self):
        self.settings = get_settings()
        # Initialize API clients, etc.

    async def method_name(self, input_data: InputSchema) -> OutputSchema:
        # 1. Log the request
        # 2. Check cache
        # 3. Call external API if needed
        # 4. Cache result
        # 5. Return structured response
```

### Schema Pattern

Input/output schemas in `mcp_server/schemas/`:

```python
from pydantic import BaseModel
from typing import Optional

class ToolInput(BaseModel):
    required_field: str
    optional_field: Optional[str] = None

class ToolOutput(BaseModel):
    data: dict
    cached: bool = False
```

### Adding a New Tool

1. Create schema in `mcp_server/schemas/new_tool.py`
2. Create tool class in `mcp_server/tools/new_tool.py`
3. Register in `mcp_server/server.py` tools dictionary
4. Add route in `mcp_server/app.py`
5. Update imports in `mcp_server/tools/__init__.py` and `mcp_server/schemas/__init__.py`
6. Write tests in `tests/test_tools/test_new_tool.py`

### Caching Strategy

Cache TTLs are defined in `mcp_server/utils/cache.py`:

| Data Type | TTL | Reason |
|-----------|-----|--------|
| Weather geocoding | 7 days | Coordinates don't change |
| Weather forecast | 30 min | Updates frequently |
| Routes/commute | 15 min | Traffic changes |
| Financial (stocks) | 5 min | Rate limit protection |
| Financial (crypto) | 2 min | More volatile |
| Calendar | No cache | Real-time accuracy needed |

### Error Handling

- Return structured error responses with appropriate HTTP status codes
- Log errors with `get_logger("module_name")`
- Provide graceful fallbacks for API failures (mock data in development)
- Cache validation errors are handled automatically

## Configuration

Environment variables (see `env.example`):

```bash
# Required in production
WEATHER_API_KEY=your_openweathermap_key
GOOGLE_MAPS_API_KEY=your_google_maps_key
HOME_ADDRESS=full_street_address
WORK_ADDRESS=full_work_address

# Optional
GOOGLE_CALENDAR_CREDENTIALS_PATH=./credentials.json
TODOIST_API_KEY=your_todoist_key
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key
REDIS_URL=redis://localhost:6379
```

Configuration is managed via Pydantic Settings in `mcp_server/config.py`.

## Testing API Endpoints

```bash
# Health check
curl http://localhost:8000/health

# List tools
curl http://localhost:8000/tools

# Weather
curl -X POST http://localhost:8000/tools/weather.get_daily \
  -H "Content-Type: application/json" \
  -d '{"location": "San Francisco, CA", "when": "today"}'

# Calendar events
curl -X POST http://localhost:8000/tools/calendar.list_events \
  -H "Content-Type: application/json" \
  -d '{"date": "2024-01-15"}'
```

## Important Notes for AI Assistants

### Rate Limiting Awareness
- Alpha Vantage: 5 calls/minute (caching is critical)
- OpenWeatherMap: 60 calls/minute
- Google Calendar: Use batch requests for date ranges

### Code Style
- Python 3.11+ required
- Black formatter with 100 char line length
- Type hints on all functions (`disallow_untyped_defs = true` in mypy)
- Use async/await for I/O operations

### When Modifying Tools
- Always update both input and output schemas
- Register new methods in `mcp_server/server.py`
- Add corresponding routes in `mcp_server/app.py` with Swagger docs
- Write tests with mocked external API calls

### Data Privacy
- Calendar data is real user data - handle with care
- Never log API keys or sensitive data
- Use structured logging for debugging

### Deployment
- Production on Railway.app with auto-deploy
- Environment variables in Railway dashboard
- Health check at `/health` for monitoring

## MCP Protocol Support

The server supports the official Model Context Protocol (MCP) via SSE transport, enabling integration with Claude Desktop, Cursor, and other MCP-compatible clients.

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/mcp/sse` | GET | SSE stream for MCP clients |
| `/mcp/messages` | POST | JSON-RPC message endpoint |
| `/mcp/health` | GET | MCP transport health check |

### Connecting Claude Desktop

Add to your Claude Desktop configuration (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "aura": {
      "url": "http://localhost:8000/mcp/sse"
    }
  }
}
```

For production:
```json
{
  "mcpServers": {
    "aura": {
      "url": "https://your-server.railway.app/mcp/sse"
    }
  }
}
```

### Connecting via stdio (Local Development)

For local integrations where the MCP client can spawn the server as a subprocess:

```json
{
  "mcpServers": {
    "aura": {
      "command": "python",
      "args": ["-m", "mcp_server.mcp_protocol"],
      "cwd": "/path/to/packages/server"
    }
  }
}
```

### Testing MCP Connection

```bash
# Check MCP transport health
curl http://localhost:8000/mcp/health

# Response:
# {"status": "healthy", "transport": "sse", "active_sessions": 0, "protocol_version": "2024-11-05"}
```

### Architecture

The MCP implementation uses two layers:

1. **mcp_protocol.py** - Wraps existing tools using the official MCP SDK
2. **mcp_sse.py** - Implements async SSE transport using FastAPI and sse-starlette

The server provides both:
- **HTTP REST API** - Direct endpoint access with auto-generated Swagger docs
- **MCP SSE Protocol** - For Claude Desktop, Cursor, and other MCP-compatible clients

Both interfaces share the same underlying tool implementations, ensuring consistent behavior.
