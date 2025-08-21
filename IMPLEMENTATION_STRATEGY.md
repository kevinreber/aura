# Implementation Strategy: Daily MCP Server

**Repository Scope**: This repository contains ONLY the MCP server component. The AI agent and frontend will be separate repositories for better architectural separation.

## Tech Stack (Python + Flask)

### MCP Server (This Repository)

**Core Framework:**

- **Server**: Flask 2.3+ with async support
- **Validation**: Pydantic v2 for schema validation + marshmallow for Flask integration
- **API Clients**: `httpx` for async HTTP calls to external APIs
- **Documentation**: flask-openapi3 for automatic API docs
- **CORS**: flask-cors for cross-origin requests

**Infrastructure:**

- **Containerization**: Docker for deployment
- **Monitoring**: Prometheus metrics + structured logging
- **Secrets**: Environment variables + optional Vault integration
- **Cache**: Redis for API response caching (optional)

### Related Repositories (Separate)

**AI Agent Repository** (`morning-routine-agent`):

- **Framework**: LangChain or LlamaIndex for agent orchestration
- **LLM Integration**: OpenAI/Claude via `litellm`
- **MCP Client**: Consumes this MCP server's tools
- **BFF API**: Optional FastAPI layer for frontend integration

**Frontend Repository** (`morning-routine-ui`):

- **Framework**: Remix (React framework with excellent data loading)
- **Styling**: Tailwind CSS for modern UI
- **Deployment**: Vercel/Netlify for static hosting
- **API Integration**: Calls agent BFF or directly to MCP server

## Development Phases

### Phase 0: Prototype (Weeks 1-2)

**Goal**: Working end-to-end demo with basic tools

**Sprint 1 (Week 1):**

```
Day 1-2: Project setup + MCP server skeleton
Day 3-4: Implement weather.get_daily tool
Day 5: Basic agent + simple CLI interface
```

**Sprint 2 (Week 2):**

```
Day 1-2: Add mobility.get_commute + calendar.list_events
Day 3-4: Add todo.list + agent orchestration logic
Day 5: End-to-end demo + basic error handling
```

**Deliverables:**

- Working MCP server with 4 tools
- Basic agent that can orchestrate tool calls
- CLI interface for testing
- Docker Compose setup for local development

### Phase 1: MVP Hardening (Weeks 3-6)

**Sprint 3-4: Infrastructure + Security**

- RBAC implementation
- Secrets management integration
- Input validation and error handling
- Basic metrics collection

**Sprint 5-6: Production Readiness**

- FastAPI BFF layer
- Session management
- Caching layer
- Basic UI (Streamlit)
- Load testing setup

### Phase 1.5: First Write Tool (Weeks 3-4) 🚀 **NEXT MILESTONE**

> **Current Status**: Phase 0 ✅ COMPLETE - All read tools working, end-to-end flow deployed to Railway

**Sprint 3: Calendar Write Operations**

```
Day 1-2: Implement calendar.create_event tool
Day 3-4: Add calendar.update_event and calendar.delete_event
Day 5: Integration testing + UI support for calendar creation
```

**Sprint 4: Enhanced Agent Capabilities**

```
Day 1-2: Add intelligent event scheduling logic
Day 3-4: Implement conflict detection and suggestions
Day 5: Add natural language event parsing
```

**Deliverables:**

- ✅ Write capability: Users can create/modify calendar events via chat
- ✅ Smart scheduling: AI suggests optimal meeting times
- ✅ Conflict resolution: Warns about overlapping events
- ✅ Natural language: "Schedule lunch with John tomorrow at noon"

### Phase 2: Production Features (Weeks 5-8)

**Sprint 5-6: Multi-tenancy + Security**

- User authentication and sessions
- Multi-tenant data isolation
- API key management per user
- Audit logging for write operations

**Sprint 7-8: Advanced Features**

- Advanced error handling & circuit breakers
- Response caching for read operations
- Performance monitoring & alerting
- Usage analytics and rate limiting

## Deployment Options for Personal Learning Project

> **Perfect for single-user experimentation and learning about MCP servers!**

### 1. **Free/Nearly Free Options (Recommended)**

**Option A: Railway.app (Hobby Plan)**

```
Cost: $0-5/month (500 hours free monthly)
Setup Time: 5 minutes
Complexity: Super Low
```

**Perfect for learning because:**

- ✅ **Git-based deployment** - just push to deploy
- ✅ **Automatic domains + SSL** - no configuration needed
- ✅ **Built-in environment variables** - easy API key management
- ✅ **Free tier** covers most personal usage
- ✅ **Great for iteration** - redeploy on every git push

**Setup:**

```bash
# 1. Connect GitHub repo to Railway
# 2. Set environment variables (API keys)
# 3. Deploy automatically on push - DONE!
```

**Option B: Render (Free Tier)**

```
Cost: $0/month (free tier)
Setup Time: 5 minutes
Complexity: Super Low
```

**Great for learning:**

- ✅ **Completely free** for personal projects
- ✅ **Auto-deploy from GitHub**
- ✅ **Built-in SSL** and custom domains
- ✅ **Sleep after 15min inactivity** (perfect for learning - saves resources)

**Option C: Fly.io (Personal Plan)**

```
Cost: $0-3/month (generous free tier)
Setup Time: 10 minutes
Complexity: Low
```

**Perfect for Docker learning:**

- ✅ **Docker-native** - great for learning containerization
- ✅ **Global edge deployment** - surprisingly fast
- ✅ **Simple CLI** - `fly deploy` and you're done
- ✅ **Free allowances** cover personal use

### 2. **Local Development + Occasional Cloud**

**Option A: Mostly Local + Ngrok**

```
Cost: $0/month
Setup Time: 2 minutes
Complexity: Minimal
```

**Perfect for active development:**

```bash
# Run locally
python run.py

# Expose to internet when needed
ngrok http 8000
# Gives you https://xyz.ngrok.io → your local server
```

**Option B: Local + GitHub Codespaces**

```
Cost: $0/month (60 hours free)
Setup Time: 1 minute
Complexity: Zero
```

**Great for learning anywhere:**

- ✅ **VS Code in browser** with full development environment
- ✅ **Automatically installs dependencies** from your repo
- ✅ **Accessible from any device**

### 3. **If You Want to Learn Infrastructure**

**Option A: DigitalOcean Droplet**

```
Cost: $6/month (basic droplet)
Setup Time: 30 minutes
Complexity: Medium
```

**Best for learning DevOps:**

- ✅ **Full server control** - learn Linux, Docker, nginx
- ✅ **Cheap and predictable** pricing
- ✅ **Great tutorials** and documentation

**Setup:**

```bash
# 1. Create $6/month droplet
# 2. Install Docker
# 3. Deploy with docker-compose
# 4. Set up basic nginx + Let's Encrypt SSL
```

## Detailed Implementation Plan

### Directory Structure (MCP Server Only)

```
daily-mcp-server/              # This repository
├── mcp_server/               # Main MCP server package
│   ├── __init__.py
│   ├── app.py               # Flask application factory
│   ├── server.py            # MCP protocol implementation
│   ├── tools/               # Individual tool implementations
│   │   ├── __init__.py
│   │   ├── weather.py       # weather.get_daily
│   │   ├── mobility.py      # mobility.get_commute
│   │   ├── calendar.py      # calendar.list_events
│   │   └── todo.py          # todo.list
│   ├── schemas/             # Pydantic schemas & validation
│   │   ├── __init__.py
│   │   ├── weather.py
│   │   ├── mobility.py
│   │   ├── calendar.py
│   │   └── todo.py
│   ├── utils/               # Shared utilities
│   │   ├── __init__.py
│   │   ├── http_client.py   # httpx wrapper
│   │   ├── cache.py         # Redis caching (optional)
│   │   └── logging.py       # Structured logging
│   └── config.py            # Configuration management
├── tests/                   # Test suite
│   ├── __init__.py
│   ├── test_tools/          # Tool-specific tests
│   ├── test_server.py       # Server tests
│   └── conftest.py          # Pytest configuration
├── docker/                  # Docker configuration
│   ├── Dockerfile
│   └── docker-compose.yml   # For local development
├── docs/                    # API documentation
├── requirements.txt         # Python dependencies
├── requirements-dev.txt     # Development dependencies
├── .env.example            # Environment template
├── README.md               # Setup and usage instructions
└── run.py                  # Development server entry point
```

### Key Dependencies

```python
# requirements.txt - Flask Option
flask==3.0.0                    # Latest Flask with async support
flask-cors==4.0.0               # CORS handling
flask-openapi3==3.0.0           # Auto API documentation
flask-limiter==3.5.0            # Rate limiting
pydantic==2.5.0                 # Schema validation
httpx==0.25.2                   # Async HTTP client
redis[hiredis]==5.0.1           # Caching (optional)
loguru==0.7.2                   # Structured logging
prometheus-flask-exporter==0.23.0  # Metrics

# MCP Protocol (when available)
mcp-sdk==0.1.0  # Replace with actual package name

# External API integrations
openweathermap-python-api==1.3.0
googlemaps==4.10.0

# Alternative: FastAPI Option (if you change your mind)
# fastapi[all]==0.104.1         # All-in-one with docs, validation, async
# uvicorn[standard]==0.24.0     # ASGI server
```

```python
# requirements-dev.txt
pytest==7.4.3
pytest-cov==4.1.0
pytest-asyncio==0.21.1
black==23.11.0
flake8==6.1.0
mypy==1.7.1
```

### Environment Configuration

```python
# mcp_server/config.py
from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    # Core MCP Server Settings
    environment: str = "development"
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # External API Keys (for tools)
    weather_api_key: str  # OpenWeatherMap API key
    google_maps_api_key: str  # Google Maps API key

    # Optional calendar integration
    google_calendar_credentials_path: Optional[str] = None

    # Optional todo integration (e.g., Todoist, Any.do)
    todoist_api_key: Optional[str] = None

    # Caching (optional)
    redis_url: Optional[str] = None
    cache_ttl: int = 300  # 5 minutes default

    # Security & CORS
    secret_key: str = "your-secret-key-change-in-production"
    allowed_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Rate limiting
    rate_limit_per_minute: int = 60

    class Config:
        env_file = ".env"

# Global settings instance
settings = Settings()
```

## Development Workflow

### 1. **Local Development Setup**

```bash
# Initial setup
git clone <repo>
cd daily-mcp-server
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Environment setup
cp .env.example .env
# Edit .env with your API keys:
# WEATHER_API_KEY=your_openweathermap_key
# GOOGLE_MAPS_API_KEY=your_google_maps_key

# Optional: Start Redis for caching
docker-compose up -d redis  # or install Redis locally

# Run MCP server
python run.py
# Server will start on http://localhost:8000
```

### 2. **Testing the MCP Server**

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=mcp_server --cov-report=html

# Run specific tool tests
pytest tests/test_tools/test_weather.py -v

# Test specific endpoints
curl http://localhost:8000/tools/weather.get_daily \
  -H "Content-Type: application/json" \
  -d '{"location": "San Francisco", "when": "today"}'
```

### 2. **Testing Strategy**

```python
# pytest configuration
pytest.ini:
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --cov=. --cov-report=html
```

### 3. **CI/CD Pipeline** (GitHub Actions)

```yaml
# .github/workflows/main.yml
name: CI/CD
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - run: pytest
      - run: docker build .

  deploy:
    if: github.ref == 'refs/heads/main'
    needs: test
    runs-on: ubuntu-latest
    steps:
      - run: echo "Deploy to staging/production"
```

## Recommended Starting Point

1. **Week 1**: Start with single VPS deployment using Docker Compose
2. **Implement MVP**: Focus on the 4 core read-only tools
3. **Validate**: Get basic end-to-end flow working
4. **Iterate**: Add production features incrementally
5. **Scale**: Move to managed services when ready

## Multi-Repository Architecture Overview

```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│   Remix Frontend    │    │    AI Agent         │    │    MCP Server       │
│  (morning-routine-  │    │ (morning-routine-   │    │ (daily-mcp-server)  │
│       ui)           │    │      agent)         │    │    [THIS REPO]      │
├─────────────────────┤    ├─────────────────────┤    ├─────────────────────┤
│ • User Interface    │    │ • LangChain/LlamaIdx│    │ • Flask Server      │
│ • Data Loading      │◄──►│ • OpenAI/Claude     │◄──►│ • 4 Core Tools      │
│ • Error Boundaries  │    │ • Tool Orchestration│    │ • External APIs     │
│ • Remix Routes      │    │ • Optional BFF API  │    │ • Schema Validation │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
```

**Communication Flow:**

1. User makes request in Remix UI
2. Remix calls AI Agent (directly or via BFF)
3. Agent calls MCP Server tools
4. MCP Server fetches data from external APIs
5. Results flow back: MCP → Agent → Frontend

## Updated Starting Point

### **Phase 0: MCP Server First (This Repository)**

1. **Week 1**: Build MCP server with Flask + 4 core tools
2. **Week 2**: Add validation, error handling, basic caching
3. **Test**: Direct HTTP calls to validate all tools work

### **Phase 1: Add Agent (New Repository)**

1. **Week 3**: Create agent repository, implement basic orchestration
2. **Week 4**: Connect agent to MCP server, test end-to-end

### **Phase 2: Add Frontend (New Repository)**

1. **Week 5**: Create Remix app, connect to agent
2. **Week 6**: Polish UI, add error handling, deploy

**Benefits of This Approach:**

- ✅ Each component can be developed and tested independently
- ✅ Clear separation of concerns
- ✅ Perfect for learning different technologies
- ✅ Independent deployment and scaling
- ✅ Easier to maintain and debug

## **✅ COMPLETED: Railway Production Deployment**

### **Current Production Status:**

✅ **MCP Server**: `https://web-production-66f9.up.railway.app`
✅ **AI Agent**: `https://web-production-f80730.up.railway.app`
✅ **Frontend UI**: `https://daily-agent-ui.vercel.app`
✅ **Auto-deployment**: Connected to GitHub with environment variables
✅ **All 5 tools working**: Weather, Calendar, Financial, Mobility, Todos

**Total Cost: $0/month** (Railway's free tier + Vercel free tier)
**Deployment Time: ✨ DONE ✨**

### **For Local Development:**

```bash
# Work locally 99% of the time
python run.py

# When you want to test from your phone/other devices:
ngrok http 8000
# Gives you public URL instantly
```

### **✅ COMPLETED: Initial Implementation Timeline**

**Week 1-2: MCP Server + Agent** ✅ **DONE**

✅ Built Flask MCP server with 5 tools (weather, calendar, financial, mobility, todos)
✅ Deployed to Railway with auto-deployment
✅ Created LangChain agent with tool orchestration
✅ Connected agent to MCP server with error handling

**Week 3: Frontend + Full Integration** ✅ **DONE**

✅ Created Remix dashboard with data widgets
✅ Added AI chat interface with slash commands
✅ Deployed to Vercel with CORS-free server-side data loading
✅ End-to-end morning routine flow working

### **🚀 NEXT: Enhanced Capabilities Timeline**

**Week 4-5: First Write Tool Implementation**

1. **Days 1-3**: Add calendar.create_event with natural language parsing
2. **Days 4-5**: Implement smart scheduling and conflict detection
3. **Weekend**: Test "Schedule lunch with John tomorrow at noon" capabilities

**Week 6-7: Multi-user + Production Hardening**

1. **Days 1-3**: Add user authentication and multi-tenancy
2. **Days 4-5**: Enhanced error handling and monitoring
3. **Weekend**: Performance optimization and caching

**Perfect for a personal learning project!** You get:

- ✅ **Zero infrastructure management**
- ✅ **Free hosting** for experimentation
- ✅ **Professional deployment experience**
- ✅ **Easy iteration** - just git push to deploy
- ✅ **Learn modern deployment patterns** without complexity

## 🎯 **CURRENT FOCUS: Phase 1.5 - First Write Tool**

### **Why Calendar Write Operations Next?**

1. **High Impact**: Users want to create meetings, not just view them
2. **Complex enough**: Requires natural language parsing, conflict detection
3. **Safe to test**: Calendar events are easy to undo if something goes wrong
4. **Foundation**: Sets up patterns for other write operations (todos, reminders)

### **Recommended Implementation Order:**

1. **Start with `calendar.create_event`** - Core functionality
2. **Add smart scheduling** - AI suggests optimal times based on existing events
3. **Natural language parsing** - "Schedule dentist appointment next Tuesday at 2pm"
4. **Conflict detection** - Warn about overlapping events
5. **Update/delete operations** - Complete CRUD operations

### **Success Metrics:**

✅ User can create calendar events via natural language chat
✅ AI suggests smart meeting times avoiding conflicts  
✅ Events appear in Google Calendar within 30 seconds
✅ Error handling for invalid times, missing attendees, etc.

**Ready to implement the first write tool? This is the natural next evolution of your personal morning assistant!**
