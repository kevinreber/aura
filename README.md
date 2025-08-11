# Daily MCP Server 🌅

A Model Context Protocol (MCP) server providing morning routine tools for AI agents. Built with Flask and Python for personal learning and experimentation.

## 🛠️ Tools Available

### 🌤️ Weather (`weather.get_daily`)

Get daily weather forecasts for any location.

- **Input**: `location` (string), `when` ("today" | "tomorrow")
- **Output**: Temperature highs/lows, precipitation chance, summary

### 🚗 Mobility (`mobility.get_commute`)

Get commute time and route information between locations.

- **Input**: `origin`, `destination`, `mode` ("driving" | "transit" | "bicycling" | "walking")
- **Output**: Duration, distance, route summary, traffic status

### 📅 Calendar (`calendar.list_events`)

List calendar events for a specific date.

- **Input**: `date` (YYYY-MM-DD)
- **Output**: List of events with times, locations, descriptions

### ✅ Todo (`todo.list`)

List todo items from different buckets/categories.

- **Input**: `bucket` ("work" | "home" | "errands" | "personal"), `include_completed` (boolean)
- **Output**: List of todos with priorities, due dates, tags

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

### Google Maps (Mobility Tool)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Enable the Directions API
3. Create an API key
4. Add to `.env`: `GOOGLE_MAPS_API_KEY=your_key_here`

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
│ • Data Loading      │◄──►│ • OpenAI/Claude     │◄──►│ • 4 Core Tools      │
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

## 🔮 Future Integrations

The tools currently use mock data but are designed for easy integration with real services:

- **Weather**: ✅ OpenWeatherMap API (ready)
- **Mobility**: ✅ Google Maps API (ready)
- **Calendar**: 🔄 Google Calendar API (planned)
- **Todo**: 🔄 Todoist API (planned)

## 🤝 Contributing

This is a personal learning project, but feel free to:

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## 📄 License

MIT License - feel free to use this code for your own learning projects!

---

**Happy coding!** 🚀 This MCP server is perfect for learning about AI agents, API integrations, and modern Python web development.
