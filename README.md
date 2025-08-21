# Daily MCP Server 🌅

A Model Context Protocol (MCP) server providing comprehensive daily productivity tools for AI agents. Features both **read** and **write** operations for real-world integration. Built with Flask and Python for personal productivity and AI agent learning.

## 🎉 **NEW: Write Operations!**

✨ **Phase 1.5 Complete** - Now supports calendar event creation with smart conflict detection!

## 🛠️ Available Tools

### 📊 **Read Operations**

#### 🌤️ Weather (`weather.get_daily`)

Get daily weather forecasts powered by OpenWeatherMap.

- **Input**: `location` (string), `when` ("today" | "tomorrow")
- **Output**: Temperature highs/lows, precipitation chance, detailed summary
- **Real API**: ✅ OpenWeatherMap integration

#### 🚗 Mobility (`mobility.get_commute`)

Get real-time commute and traffic information.

- **Input**: `origin`, `destination`, `mode` ("driving" | "transit" | "bicycling" | "walking")
- **Output**: Duration, distance, route summary, live traffic status
- **Real API**: ✅ Google Maps Directions integration

#### 📅 Calendar (`calendar.list_events`)

List calendar events for any date with multi-calendar support.

- **Input**: `date` (YYYY-MM-DD)
- **Output**: Events with times, locations, descriptions, attendees
- **Real API**: ✅ Google Calendar (Primary, Runna, Family calendars)

#### 📅 Calendar Range (`calendar.list_events_range`)

Efficiently get events for date ranges (much faster than multiple single-date calls).

- **Input**: `start_date`, `end_date` (YYYY-MM-DD)
- **Output**: All events in range sorted by time
- **Real API**: ✅ Google Calendar multi-calendar support

#### ✅ Todo (`todo.list`)

List todo items with smart filtering and categorization.

- **Input**: `bucket` ("work" | "home" | "errands" | "personal"), `include_completed` (boolean)
- **Output**: Todos with priorities, due dates, completion status
- **API Status**: 🔄 Mock data (Todoist integration planned)

#### 💰 Financial (`financial.get_data`)

Real-time stock and cryptocurrency market data.

- **Input**: `symbols` (["MSFT", "BTC", "ETH", "NVDA"]), `data_type` ("stocks" | "crypto" | "mixed")
- **Output**: Live prices, daily changes, market status, portfolio summary
- **Real APIs**: ✅ Alpha Vantage (stocks) + CoinGecko (crypto)

### ✨ **Write Operations**

#### 📅+ Calendar Create (`calendar.create_event`) 🆕

**Create new calendar events with intelligent conflict detection!**

- **Input**: `title`, `start_time`, `end_time`, `description`, `location`, `attendees`, `calendar_name`
- **Output**: Created event details, conflict warnings, Google Calendar URL
- **Features**:
  - ⚠️ **Smart Conflict Detection** - Warns about overlapping events
  - 🎯 **Multi-Calendar Support** - Target specific calendars (primary, work, etc.)
  - 🔗 **Real Integration** - Events appear in Google Calendar instantly
  - 📧 **Attendee Management** - Email invitations and notifications
- **Real API**: ✅ Google Calendar Events API with write permissions

## 🚀 Quick Start

### 1. Setup Environment

**Option A: Using UV (Recommended - Much Faster!)**

```bash
# Clone the repository
git clone <your-repo-url>
cd daily-mcp-server

# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies (creates venv automatically)
uv sync --dev

# Activate the environment (optional - uv commands work without this)
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

**Option B: Traditional pip/venv**

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. Configure Environment

```bash
# Copy environment template
cp env.example .env

# Edit .env with your API keys
# Required for full functionality:
WEATHER_API_KEY=your_openweathermap_api_key
GOOGLE_MAPS_API_KEY=your_google_maps_api_key
```

### 3. Run the Server

**With UV:**

```bash
# Start development server
uv run python run.py
# Or use the script shortcut:
uv run mcp-server

# Server will start on http://localhost:8000
```

**Traditional:**

```bash
python run.py
```

## 🧪 Testing the Tools

### Health Check

```bash
curl http://localhost:8000/health
```

### List Available Tools

```bash
curl http://localhost:8000/tools
```

### Test Weather Tool

```bash
curl -X POST http://localhost:8000/tools/weather.get_daily \
  -H "Content-Type: application/json" \
  -d '{"location": "San Francisco, CA", "when": "today"}'
```

### Test Mobility Tool

```bash
curl -X POST http://localhost:8000/tools/mobility.get_commute \
  -H "Content-Type: application/json" \
  -d '{"origin": "San Francisco", "destination": "Oakland", "mode": "driving"}'
```

### Test Calendar Tool

```bash
curl -X POST http://localhost:8000/tools/calendar.list_events \
  -H "Content-Type: application/json" \
  -d '{"date": "2024-01-15"}'
```

### 🆕 Test Calendar Event Creation

```bash
curl -X POST http://localhost:8000/tools/calendar.create_event \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Team Meeting",
    "start_time": "2024-01-15T14:00:00",
    "end_time": "2024-01-15T15:00:00",
    "location": "Conference Room A",
    "description": "Weekly team sync",
    "attendees": ["colleague@example.com"],
    "calendar_name": "primary"
  }'
```

### Test Todo Tool

```bash
curl -X POST http://localhost:8000/tools/todo.list \
  -H "Content-Type: application/json" \
  -d '{"bucket": "work", "include_completed": false}'
```

## 🔑 API Keys Setup

### OpenWeatherMap (Weather Tool)

1. Sign up at [OpenWeatherMap](https://openweathermap.org/api)
2. Get your free API key
3. Add to `.env`: `WEATHER_API_KEY=your_key_here`

### Google APIs (Mobility & Calendar Tools)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable APIs:
   - **Directions API** (for mobility/commute)
   - **Calendar API** (for calendar read/write)
4. Create credentials:
   - **API Key** for Directions API
   - **OAuth 2.0** for Calendar API (download JSON file)
5. Add to `.env`:
   ```
   GOOGLE_MAPS_API_KEY=your_api_key_here
   GOOGLE_CALENDAR_CREDENTIALS_PATH=path/to/credentials.json
   ```

### Google Calendar Setup (for Write Operations)

1. Set up OAuth consent screen in Google Cloud Console
2. Add scopes: `calendar.readonly` and `calendar.events`
3. Add yourself as a test user
4. Download OAuth credentials JSON file
5. Place in your project and update `.env` path

### Alpha Vantage (Financial Tool)

1. Sign up at [Alpha Vantage](https://www.alphavantage.co/support/#api-key)
2. Get your free API key (500 requests/day)
3. Add to `.env`: `ALPHA_VANTAGE_API_KEY=your_key_here`

**Note**: The server works without API keys using mock data for development/testing.

## 🏗️ Architecture

This repository contains **only the MCP server**. The complete morning routine system uses a multi-repository architecture:

```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│   Remix Frontend    │    │    AI Agent        │    │    MCP Server       │
│  (morning-routine-  │    │ (morning-routine-   │    │ (daily-mcp-server)  │
│       ui)           │    │      agent)         │    │    [THIS REPO]      │
├─────────────────────┤    ├─────────────────────┤    ├─────────────────────┤
│ • User Interface    │    │ • LangChain/LlamaIdx│    │ • Flask Server      │
│ • Data Loading      │◄──►│ • OpenAI/Claude     │◄──►│ • 6 Tools (5R+1W)   │
│ • Error Boundaries  │    │ • Tool Orchestration│    │ • External APIs     │
│ • Remix Routes      │    │ • Optional BFF API  │    │ • Schema Validation │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
```

## 🚀 Deployment

### Option 1: Railway.app (Recommended for Learning)

1. Push code to GitHub
2. Connect repository to [Railway](https://railway.app)
3. Add environment variables in Railway dashboard
4. Deploy automatically on push!

### Option 2: Render.com (Free)

1. Connect GitHub repository to [Render](https://render.com)
2. Set up environment variables
3. Deploy with zero configuration

### Option 3: Local with Ngrok

```bash
# Run server locally
python run.py

# In another terminal, expose to internet
ngrok http 8000
```

## 🧩 Development

### Project Structure

```
daily-mcp-server/
├── mcp_server/           # Main application package
│   ├── tools/           # Individual MCP tools
│   ├── schemas/         # Pydantic validation schemas
│   ├── utils/           # Shared utilities
│   ├── app.py          # Flask application factory
│   └── config.py       # Configuration management
├── tests/              # Test suite
├── pyproject.toml      # Modern Python dependencies & config
├── requirements.txt    # Legacy dependencies (still supported)
└── run.py             # Development server entry point
```

### Running Tests

**With UV:**

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=mcp_server --cov-report=html

# Run specific tests
uv run pytest tests/test_tools/test_weather.py -v
```

**Traditional:**

```bash
pytest
pytest --cov=mcp_server --cov-report=html
```

### Code Formatting

**With UV:**

```bash
# Format code
uv run black mcp_server/

# Check linting
uv run flake8 mcp_server/

# Type checking
uv run mypy mcp_server/
```

**Traditional:**

```bash
black mcp_server/
flake8 mcp_server/
mypy mcp_server/
```

## 📊 API Integration Status

| Tool               | Status      | API Provider              | Features                           |
| ------------------ | ----------- | ------------------------- | ---------------------------------- |
| 🌤️ Weather         | ✅ **Live** | OpenWeatherMap            | Current conditions, forecasts      |
| 🚗 Mobility        | ✅ **Live** | Google Maps               | Real-time traffic, routes          |
| 📅 Calendar Read   | ✅ **Live** | Google Calendar           | Multi-calendar support             |
| 📅+ Calendar Write | ✅ **Live** | Google Calendar           | Event creation, conflict detection |
| 💰 Financial       | ✅ **Live** | Alpha Vantage + CoinGecko | Stocks + crypto prices             |
| ✅ Todo            | 🔄 **Mock** | Todoist (planned)         | Smart categorization               |

## 🎯 **Current Capabilities**

- ✅ **5 Read Tools** - All with real API integration
- ✅ **1 Write Tool** - Calendar event creation with smart features
- ✅ **Multi-Calendar Support** - Primary, Runna, Family calendars
- ✅ **Conflict Detection** - Smart scheduling assistance
- ✅ **Production Deployment** - Railway.app with auto-deployment

## 🔮 **Phase 2 Roadmap**

- 🎯 **Smart Scheduling** - AI-powered optimal meeting time suggestions
- ✏️ **Calendar CRUD** - Update and delete calendar events
- 📝 **Todo Write Operations** - Create, update, complete tasks
- 🧠 **Natural Language** - Enhanced parsing for relative times
- 👥 **Multi-tenancy** - Multiple user support

## 🤝 Contributing

This is a personal learning project, but feel free to:

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## 📄 License

MIT License - feel free to use this code for your own learning projects!

---

## 📖 **Interactive Documentation**

Visit `http://localhost:8000/docs` for comprehensive Swagger UI documentation with:

- 📋 **All Tool Schemas** - Input/output examples and validation
- 🧪 **Try It Out** - Test tools directly in the browser
- 📊 **Response Examples** - See real API responses
- 🔍 **Schema Explorer** - Understand data structures

## 🎉 **What Makes This Special**

This isn't just another API - it's a **complete productivity assistant backend**:

- 🤖 **AI Agent Ready** - Purpose-built for LLM integration
- 🔄 **Read + Write** - Both information retrieval AND action taking
- 🧠 **Smart Features** - Conflict detection, multi-calendar support
- ⚡ **Real Integrations** - Live data from Google, OpenWeatherMap, financial APIs
- 📱 **Production Deployed** - Working system you can use daily
- 🎯 **Personal Use** - Designed for individual productivity

**Happy coding!** 🚀 This MCP server demonstrates modern AI agent architecture with real-world integrations and write capabilities.
