# 🤖 Daily AI Assistant Agent

An intelligent AI agent that acts as your **personal productivity assistant**, orchestrating tools from your high-performance [MCP server](../daily-mcp-server/) to provide comprehensive daily management. Features both **information retrieval** and **action taking** capabilities with **lightning-fast performance** thanks to intelligent caching.

## 🚀 **ENHANCED: Lightning-Fast Performance!**

✨ **NEW**: **Advanced caching** eliminates rate limiting and delivers **instant responses**!

### 🔥 **Performance Improvements**

- ⚡ **60-90% faster responses** for repeated requests
- 🛡️ **Zero rate limiting issues** with intelligent caching
- 📊 **Smart data freshness** - live data when needed, cached when optimal
- 🚀 **Instant weather/financial/calendar** data for common queries

🎯 **What makes this special?** This isn't just another chatbot - it's a **production-ready AI assistant** that:

- **✅ FIXED: Calendar Reading** - Now properly reads and displays your real calendar events
- **Creates real calendar events** through conversational AI (ready for update/delete)
- **Orchestrates 8 specialized tools** with intelligent routing
- **Provides smart conflict detection** when scheduling meetings
- **Integrates live APIs** (Google Calendar, OpenWeatherMap, financial markets)
- **High-performance caching** eliminates rate limiting with Redis + in-memory fallback
- **Uses LangChain + GPT-4o-mini** for optimal cost/performance
- **Runs in production** with FastAPI backend and CLI interface

## ✨ Enhanced Features

### 🗣️ **Conversational Calendar Management**

- **✅ "What's on my calendar tomorrow?"** → Now properly reads and displays your real events
- **"Schedule lunch with John tomorrow at noon"** → Creates actual Google Calendar event
- **🆕 "Find me 60 minutes free tomorrow afternoon"** → AI-powered smart time finding with preference scoring
- **🆕 "When can I schedule a 2-hour deep work session this week?"** → Multi-day intelligent scheduling
- **Smart conflict detection** → Warns about overlapping meetings
- **Multi-calendar support** → Target work, personal, family calendars
- **Natural language parsing** → Understands dates, times, and context
- **🔜 Coming Soon**: _"Move my 2pm meeting to 3pm"_ and _"Cancel my gym session"_

### 📊 **Comprehensive Data Access**

- 🌤️ **Real Weather Data** - Live forecasts from OpenWeatherMap
- 💰 **Live Financial Markets** - Real-time stocks & crypto prices
- 📅 **Calendar Integration** - Multi-calendar events with Google Calendar
- ✅ **Smart Todo Management** - Prioritized task lists with filtering
- 🚗 **Commute Intelligence** - Real-time traffic, transit options, fuel estimates, and AI recommendations

### 🤖 **Advanced AI Capabilities**

- **Tool Selection Intelligence** - GPT-4o-mini chooses optimal tools
- **Parallel Execution** - Multiple operations simultaneously
- **Context Awareness** - Remembers conversation flow
- **Error Recovery** - Graceful handling of API failures

## 🚀 Quick Start

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) for package management
- OpenAI API key (for conversational features)
- Running MCP server at https://web-production-66f9.up.railway.app

### Installation

```bash
# Clone and setup
git clone <your-repo-url>
cd daily-ai-agent

# Install dependencies
uv sync

# Setup environment variables
cp .env.example .env
# Edit .env with your API keys (see Configuration section)
```

### Configuration

Create a `.env` file based on `.env.example`:

```bash
# Required for conversational AI
OPENAI_API_KEY=your_openai_api_key_here

# MCP Server (already configured for your deployment)
MCP_SERVER_URL=https://web-production-66f9.up.railway.app

# Customize your preferences
USER_NAME=Kevin
USER_LOCATION=San Francisco
DEFAULT_COMMUTE_ORIGIN=Home
DEFAULT_COMMUTE_DESTINATION=Office
```

### Usage Options

#### 🖥️ **Option 1: CLI Interface** (Great for terminal users)

```bash
# Quick health check
uv run daily-ai-agent health

# Individual tool commands
uv run daily-ai-agent weather
uv run daily-ai-agent todos
uv run daily-ai-agent commute

# Complete morning briefings
uv run daily-ai-agent briefing          # Basic data briefing
uv run daily-ai-agent smart-briefing    # AI-powered conversational briefing

# Natural language conversations
uv run daily-ai-agent chat -m "What's my day looking like?"
uv run daily-ai-agent chat -m "Should I wear a jacket today?"
uv run daily-ai-agent chat -m "Schedule lunch with John tomorrow at 1pm"  # 🆕 Calendar creation!
uv run daily-ai-agent chat -m "Find me 90 minutes free tomorrow afternoon"  # 🆕 Smart time finding!
uv run daily-ai-agent chat              # Interactive chat mode

# Demo all features
uv run daily-ai-agent demo
```

#### 🌐 **Option 2: API Server** (Great for web apps & integrations)

**Start the API server:**

```bash
# Start the Flask API server (runs on http://localhost:8001)
uv run daily-ai-agent-api
```

The server will start and show available endpoints:

```
🚀 Starting AI Agent API Server
📊 Environment: development
🔧 Debug mode: true
🤖 AI Features: ✅ Enabled
🌐 MCP Server: http://localhost:8000

Available endpoints:
  📋 Health check:     http://localhost:8001/health
  📚 Swagger UI:       http://localhost:8001/docs
  🗂️  List tools:       http://localhost:8001/tools
  💬 Chat API:         POST http://localhost:8001/chat
  📅 Briefing API:     http://localhost:8001/briefing
  🌤️  Weather API:      http://localhost:8001/tools/weather
  ✅ Todos API:        http://localhost:8001/tools/todos
  📅 Calendar API:     http://localhost:8001/tools/calendar
  🚗 Commute API:      http://localhost:8001/tools/commute
```

**API Usage Examples:**

```bash
# Health check
curl http://localhost:8001/health

# Get weather
curl "http://localhost:8001/tools/weather?location=San Francisco&when=today"

# Get todos (with enhanced bucket support!)
curl "http://localhost:8001/tools/todos?bucket=work"          # Specific bucket
curl "http://localhost:8001/tools/todos"                     # All todos (no bucket)

# Get calendar events
curl "http://localhost:8001/tools/calendar?date=2025-01-15"

# Chat with AI (requires OpenAI API key)
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What's my day looking like?"}'

# Get smart briefing
curl "http://localhost:8001/briefing?type=smart"

# Get financial data
curl -X POST http://localhost:8001/tools/financial \
  -H "Content-Type: application/json" \
  -d '{"symbols": ["MSFT", "BTC", "ETH"], "data_type": "mixed"}'
```

**🎯 Interactive API Documentation:**

Visit **http://localhost:8001/docs** for full Swagger UI documentation with:

- ✅ Interactive API testing
- ✅ Request/response examples
- ✅ Parameter documentation
- ✅ Live server testing

### 🚀 Try It Now (Quick Start)

#### **CLI Interface:**

```bash
# 1. Clone and setup
git clone <your-repo> && cd daily-ai-agent
uv sync

# 2. Add your OpenAI API key to .env
cp .env.example .env
# Edit .env: OPENAI_API_KEY=sk-your-key-here

# 3. Test the connection
uv run daily-ai-agent health

# 4. Try the AI features!
uv run daily-ai-agent smart-briefing
uv run daily-ai-agent chat -m "What's my day like?"
```

#### **API Server:**

```bash
# 1. Same setup as above (clone, uv sync, .env)

# 2. Start the API server
uv run daily-ai-agent-api

# 3. Test the API (in another terminal)
curl http://localhost:8001/health
curl http://localhost:8001/tools/weather
curl http://localhost:8001/tools/todos  # ✨ All todos (enhanced!)

# 4. Try the interactive docs
open http://localhost:8001/docs
```

## 📋 Example Output

### 🤖 AI-Powered Smart Briefing

```bash
$ uv run daily-ai-agent smart-briefing

🤖 Generating your intelligent morning briefing...

╭───────────────────────────────────────── 🌅 AI Morning Briefing ─────────────────────────────────────────╮
│ Good morning, Kevin! Here's your complete morning briefing:                                              │
│                                                                                                          │
│ 🌤️ **Weather**: It's a lovely day with scattered clouds and a pleasant temperature of **77.4°F**. Perfect │
│ for getting out and about!                                                                               │
│                                                                                                          │
│ 📅 **Calendar**: You have **no events** scheduled for today, so it looks like you have a free day ahead! │
│                                                                                                          │
│ ✅ **Todos**: You have **3 pending tasks** to tackle. Let's make sure to get those done!                 │
│                                                                                                          │
│ 🚗 **Commute**: Since you have no events today, there's no commute information needed for the office.    │
│                                                                                                          │
│ 💰 **Markets**: 7 instruments tracked | 📈 4 gaining | 📉 3 declining | 🏆 Best: BTC (+4.2%)           │
│                                                                                                          │
│ Looks like you have a great day ahead with plenty of time to focus on your tasks! Let me know if you     │
│ need help with anything specific.                                                                        │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### 💬 Natural Language Conversations

```bash
$ uv run daily-ai-agent chat -m "What's my day looking like?"

You: What's my day looking like?
🤖 Thinking...
Assistant: Here's your morning briefing, Kevin:

🌤️ **Weather**: Scattered Clouds - 77.4°F
📅 **Calendar**: 0 events today
✅ **Todos**: 3 pending tasks
🚗 **Commute**: N/A to office
💰 **Markets**: 7 instruments tracked | 📈 4 gaining | 📉 3 declining | 🏆 Best: BTC (+4.2%)

Let me know if you need help with anything specific!

$ uv run daily-ai-agent chat -m "Should I wear a jacket today?"

You: Should I wear a jacket today?
🤖 Thinking...
Assistant: Today in San Francisco, the weather is expected to be warm with a high of 77.4°F and a low of 56.6°F. Since it's a bit on the warmer side, you might not need a jacket, but it could be a good idea to have one handy for the cooler morning or evening.

$ uv run daily-ai-agent chat -m "Schedule lunch with John tomorrow at 1pm"

You: Schedule lunch with John tomorrow at 1pm
🤖 Thinking...
Assistant: ✅ **Event Created Successfully!**

I've created a lunch meeting for you:
- **Title**: Lunch with John
- **Time**: Tomorrow, January 16th, 1:00 PM - 2:00 PM
- **Calendar**: Primary
- **Event ID**: abc123xyz
- **URL**: https://calendar.google.com/calendar/event?eid=abc123xyz

✅ **No conflicts detected** - your calendar is free at that time!

The event has been added to your Google Calendar and John will receive an invitation.

$ uv run daily-ai-agent chat -m "How's Microsoft stock doing?"

You: How's Microsoft stock doing?
🤖 Thinking...
Assistant: The current price of Microsoft (MSFT) is $522.04, up by $1.20 (+0.2%). Looking good with a slight upward trend today!
```

### 📊 Individual Tool Output

```bash
# Weather with real OpenWeatherMap data
$ uv run daily-ai-agent weather

  🌤️ Weather for San Francisco, US
┏━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃ Metric        ┃ Value            ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ High          │ 77.4°F           │
│ Low           │ 56.6°F           │
│ Precipitation │ 0%               │
│ Summary       │ Scattered Clouds │
│ Date          │ 2025-08-11       │
└───────────────┴──────────────────┘

# Todo management with priorities
$ uv run daily-ai-agent todos

                             ✅ Work Todos
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Task                      ┃ Priority ┃ Due Date                      ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Review quarterly reports  │ high     │ Tue, 12 Aug 2025 06:24:57 GMT │
│ Code review for PR #123   │ medium   │ Mon, 11 Aug 2025 06:24:57 GMT │
│ Plan sprint retrospective │ medium   │ Sat, 16 Aug 2025 06:24:57 GMT │
└───────────────────────────┴──────────┴───────────────────────────────┘
📊 Total: 3 items, 3 pending

# Financial data with real market prices
$ uv run daily-ai-agent chat -m "Show me MSFT, BTC, and ETH prices"

You: Show me MSFT, BTC, and ETH prices
🤖 Thinking...
Assistant: Here's the latest financial update:

- **Microsoft Corporation (MSFT)**: $522.04 (+$1.20, +0.2%)
- **Bitcoin (BTC)**: $119,483.00 (+$961.16, +0.8%)
- **Ethereum (ETH)**: $4,282.23 (+$57.58, +1.3%)

Let me know if you need anything else!

# Health check
$ uv run daily-ai-agent health
✅ MCP Server is healthy!
```

## 🏗️ Architecture

```
┌─────────────────────┐    HTTP/REST    ┌──────────────────────┐
│   AI Agent Layer   │ ──────────────> │   MCP Server         │
│   (This Project)   │                 │   (Railway Deployed) │
│                     │                 │                      │
│ • Flask API Server  │                 │ • 8 Tools (6R + 2W)  │
│ • CLI Interface     │                 │ • Weather API ✅      │
│ • Tool Orchestrator │                 │ • Financial API ✅    │
│ • LangChain Agent   │                 │ • Calendar R/W ✅     │
│ • GPT-4o-mini       │                 │ • Todoist API ✅      │
│ • Swagger UI        │                 │ • Mobility API ✅     │
│                     │                 │ • Enhanced Buckets ✨ │
└─────────────────────┘                 └──────────────────────┘
          │                                       │
          │                                       │
          ▼                                       │
┌─────────────────────┐                         │
│   Frontend UI       │ ────────────────────────┘
│   (Remix/React)     │    Direct MCP Access
│                     │
│ • Real-time Updates │
│ • Bucket Selection  │
│ • Interactive Chat  │
│ • Dashboard View    │
└─────────────────────┘

🔄 **Dual Interface Architecture:**
• **CLI**: Direct tool access for terminal users
• **API**: RESTful endpoints for web apps & integrations (Port 8001)
• **UI**: React dashboard with bucket selection (Port 5173)
```

## 🔧 Development

### Project Structure

```
daily-ai-agent/
├── src/daily_ai_agent/
│   ├── __init__.py              # Package entry point
│   ├── main.py                  # CLI interface
│   ├── agent/                   # AI orchestration logic
│   ├── services/
│   │   ├── mcp_client.py        # MCP server HTTP client
│   │   └── llm.py              # OpenAI integration (coming)
│   ├── models/
│   │   ├── config.py           # Settings management
│   │   └── schemas.py          # Data models
│   └── utils/                  # Helpers and formatters
├── tests/                      # Test suite
├── examples/                   # Demo scripts
├── requirements.txt           # Dependencies
└── pyproject.toml            # Project configuration
```

### Running Tests

```bash
# Install dev dependencies
uv sync --dev

# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=daily_ai_agent
```

### API Server Development

**Start development server:**

```bash
# Start with auto-reload (development mode)
uv run daily-ai-agent-api

# Or with custom configuration
ENVIRONMENT=development PORT=8001 DEBUG=true uv run daily-ai-agent-api
```

**Test API endpoints:**

```bash
# Health check
curl http://localhost:8001/health

# Weather (GET)
curl "http://localhost:8001/tools/weather?location=New York&when=today"

# Todos with enhanced bucket support (GET)
curl "http://localhost:8001/tools/todos"                    # All todos
curl "http://localhost:8001/tools/todos?bucket=work"       # Work bucket only
curl "http://localhost:8001/tools/todos?bucket=personal"   # Personal bucket only

# Chat API (POST) - requires OpenAI API key
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me about my todos and weather"}'

# Smart briefing
curl "http://localhost:8001/briefing?type=smart"
```

**Interactive testing:**

- Visit **http://localhost:8001/docs** for Swagger UI
- All endpoints are documented and testable

### Add New Commands

```python
# In src/daily_ai_agent/main.py
@app.command()
def my_command():
    """Add your custom command here."""
    # Your logic here
```

## 🎯 Available Commands

| Command                   | Description                        | Example                                          |
| ------------------------- | ---------------------------------- | ------------------------------------------------ |
| `health`                  | Check MCP server connectivity      | `uv run daily-ai-agent health`                   |
| `weather [location]`      | Get weather forecast               | `uv run daily-ai-agent weather "New York"`       |
| `todos [bucket]`          | List todo items                    | `uv run daily-ai-agent todos work`               |
| `commute [origin] [dest]` | Get commute info                   | `uv run daily-ai-agent commute`                  |
| `briefing [date]`         | Basic morning briefing             | `uv run daily-ai-agent briefing`                 |
| `smart-briefing`          | AI-powered conversational briefing | `uv run daily-ai-agent smart-briefing`           |
| `chat -m "message"`       | Natural language conversation      | `uv run daily-ai-agent chat -m "Schedule lunch"` |
| `chat`                    | Interactive chat mode              | `uv run daily-ai-agent chat`                     |
| `demo`                    | Run feature demonstration          | `uv run daily-ai-agent demo`                     |

### 🆕 **Calendar Creation Examples** (via chat)

- `chat -m "Schedule lunch with John tomorrow at 1pm"`
- `chat -m "Book dentist appointment next Tuesday at 3pm"`
- `chat -m "Create team meeting Friday 2-3pm in Conference Room A"`
- `chat -m "Set up workout session this weekend"`

## 🚀 Roadmap

### ✅ **Phase 1.5 Complete** (Calendar Creation)

- [x] MCP server integration with 6 tools
- [x] Calendar event creation via natural language
- [x] Smart conflict detection for scheduling
- [x] Multi-calendar support (Primary, Runna, Family)
- [x] LangChain + GPT-4o-mini tool orchestration
- [x] FastAPI server + CLI interface
- [x] Real Google Calendar integration
- [x] Production deployment (Railway + Vercel)

### 🔄 **Phase 2 In Progress** (Enhanced Intelligence)

- [ ] Smart scheduling - AI suggests optimal meeting times
- [ ] Calendar update/delete operations
- [ ] Natural language time parsing ("next Tuesday", "in 2 hours")
- [ ] Conversation memory and context
- [ ] Todo write operations (create, update, complete)

### 🔮 **Future Phases** (Advanced Features)

- [ ] Multi-tenancy and user management
- [ ] Proactive notifications and reminders
- [ ] Voice integration (speech-to-text)
- [ ] Team collaboration features
- [ ] Mobile app integration
- [ ] Slack/Teams bot integration

## 🤝 Integration

### With MCP Server

This agent connects to your deployed MCP server at:

- **Health**: `GET /health`
- **Tools**: `POST /tools/{tool_name}`
- **List**: `GET /tools`

### API Server Endpoints (Port 8001)

The AI Agent **already exposes** comprehensive REST endpoints:

#### 🤖 **AI Features**

- **Chat**: `POST /chat` - Natural language conversations
- **Briefing**: `GET /briefing?type=smart` - AI-powered morning briefings

#### 🔧 **Tool Access**

- **Weather**: `GET /tools/weather?location=SF&when=today`
- **Todos**: `GET /tools/todos?bucket=work` (✨ Enhanced: omit bucket for all todos)
- **Calendar**: `GET /tools/calendar?date=2025-01-15`
- **Commute**: `GET /tools/commute?origin=Home&destination=Office`
- **Financial**: `POST /tools/financial` (body: `{"symbols": ["MSFT", "BTC"]}`)
- **Commute Options**: `POST /tools/commute-options` - Enhanced commute analysis
- **Shuttle**: `POST /tools/shuttle` - MV Connector schedules

#### 📊 **System**

- **Health**: `GET /health` - Service health status
- **Tools List**: `GET /tools` - Available endpoints
- **Documentation**: `GET /docs` - Interactive Swagger UI

### With Frontend UI

The **daily-agent-ui** project integrates via:

- **API Proxy**: Routes through AI Agent API (avoids CORS)
- **Real-time Data**: Live updates from MCP server
- **Enhanced UX**: Bucket selection, chat interface, dashboard views

### Environment Variables

**For API Server:**

```bash
# Required for AI features
OPENAI_API_KEY=your_openai_key_here

# Server configuration
HOST=0.0.0.0                    # Default: 0.0.0.0 (all interfaces)
PORT=8001                       # Default: 8001
ENVIRONMENT=development          # development | production

# MCP Server connection
MCP_SERVER_URL=http://localhost:8000  # Your MCP server URL

# User preferences
USER_NAME=Kevin
USER_LOCATION=San Francisco
DEFAULT_COMMUTE_ORIGIN=Home
DEFAULT_COMMUTE_DESTINATION=Office
```

## 📚 Related Projects

- **[MCP Server](../daily-mcp-server/)** - Backend tools and APIs
- **Morning Routine Frontend** - Web interface (coming soon)

## 🛡️ Security

- **Environment variables** for all API keys
- **No sensitive data** in git repository
- **Secure HTTP** connections to external APIs
- **Input validation** for all user inputs

## 📝 License

MIT License - See LICENSE file for details

## 🛠️ Local Development Setup

### Quick Start for Development

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/daily-ai-agent.git
cd daily-ai-agent

# 2. Copy the local development config
cp .env.local.example .env

# 3. Edit .env and add your OpenAI API key
# OPENAI_API_KEY=your_key_here

# 4. Install dependencies
uv sync --dev

# 5. Start the development server with hot reload
FLASK_DEBUG=1 uv run daily-ai-agent-api
```

### Development Server Features

When running in development mode (`ENVIRONMENT=development`):
- **Hot Reload**: Server restarts on code changes
- **Debug Logging**: Verbose logging for debugging
- **Swagger UI**: Interactive API docs at http://localhost:8001/docs
- **Request IDs**: Every request gets a unique ID for tracing

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov=daily_ai_agent --cov-report=html

# Run specific test file
uv run pytest tests/test_api.py -v

# Run tests matching a pattern
uv run pytest -k "test_weather" -v
```

## 🔧 Adding Custom Tools

### Step 1: Create Tool Input Schema

```python
# In src/daily_ai_agent/agent/tools.py

class MyToolInput(BaseModel):
    """Input schema for my custom tool."""
    param1: str = Field(description="Description of parameter 1")
    param2: int = Field(default=10, description="Optional parameter with default")
```

### Step 2: Create Tool Class

```python
class MyCustomTool(BaseTool):
    """Custom tool description."""

    name: str = "my_custom_tool"
    description: str = "What this tool does and when to use it"
    args_schema: Type[BaseModel] = MyToolInput

    def _get_mcp_client(self) -> MCPClient:
        """Get MCP client instance."""
        return MCPClient()

    async def _arun(self, param1: str, param2: int = 10) -> str:
        """Async implementation of the tool."""
        try:
            client = self._get_mcp_client()
            # Call MCP server or implement logic
            result = await client.call_tool("my_tool.action", {
                "param1": param1,
                "param2": param2
            })
            return f"Result: {result}"
        except Exception as e:
            return f"Error: {str(e)}"

    def _run(self, param1: str, param2: int = 10) -> str:
        """Sync wrapper for async call."""
        return asyncio.run(self._arun(param1, param2))
```

### Step 3: Register Tool

```python
# In get_all_tools() function
def get_all_tools():
    return [
        WeatherTool(),
        CalendarTool(),
        # ... existing tools ...
        MyCustomTool(),  # Add your new tool
    ]
```

### Step 4: Add API Endpoint (Optional)

```python
# In src/daily_ai_agent/api.py

@app.route('/tools/my-tool', methods=['POST'])
async def my_tool_endpoint():
    """My custom tool endpoint."""
    try:
        data = request.get_json() or {}
        # ... implement endpoint logic ...
        return jsonify({"tool": "my_tool", "data": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

## ❓ Troubleshooting

### Common Issues

#### MCP Server Connection Failed
```
Error: MCP server health check failed
```
**Solution:**
1. Verify MCP server is running: `curl http://localhost:8000/health`
2. Check `MCP_SERVER_URL` in your `.env` file
3. Ensure no firewall is blocking the connection

#### OpenAI API Key Missing
```
Error: Conversational AI not available
```
**Solution:**
1. Add `OPENAI_API_KEY=your_key` to your `.env` file
2. Verify the key is valid at https://platform.openai.com
3. Check API key has sufficient credits

#### CORS Errors in Browser
```
Access-Control-Allow-Origin error
```
**Solution:**
1. Add your frontend URL to `ALLOWED_ORIGINS` in `.env`
2. Format: `ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173`
3. Restart the API server

#### Rate Limit Exceeded
```
Error: 429 Too Many Requests
```
**Solution:**
1. Increase `RATE_LIMIT_PER_MINUTE` in `.env` (default: 60)
2. Implement client-side rate limiting
3. Use request batching where possible

#### Import Errors After Updates
```
ModuleNotFoundError: No module named 'daily_ai_agent.utils'
```
**Solution:**
1. Reinstall dependencies: `uv sync`
2. Clear Python cache: `find . -type d -name __pycache__ -exec rm -rf {} +`
3. Verify Python version: `python --version` (requires 3.13+)

### Debug Mode

Enable verbose logging for troubleshooting:

```bash
# Set in .env
DEBUG=true
LOG_LEVEL=DEBUG

# Or run with environment variables
DEBUG=true LOG_LEVEL=DEBUG uv run daily-ai-agent-api
```

### Request Tracing

Every API response includes a `request_id` header and field:
- Use this ID when reporting issues
- Correlate logs across services
- Track requests in monitoring tools

## 🙋‍♂️ Support

For questions or issues:

1. Check the [AI Agent Strategy](./AI_AGENT_STRATEGY.md) document
2. Review the [MCP Server documentation](../daily-mcp-server/README.md)
3. Create an issue in this repository

---

**Happy morning routines! 🌅**
