# Daily MCP Server 🌅

A high-performance Model Context Protocol (MCP) server providing comprehensive daily productivity tools for AI agents. Features **complete Calendar CRUD** operations, **intelligent commute intelligence**, **live traffic data**, and real-world API integrations. Built with Flask and Python for optimal performance and AI agent productivity.

## 🚀 **Latest Enhancement: Complete Commute Intelligence System!**

✨ **NEW**: **Comprehensive traffic & transit integration** with real-time data and personalized routing!

### 🚗🚂 **Commute Intelligence Features**

- 🗺️ **Real-Time Traffic Data** - Google Maps API with live conditions
- 🚂 **Live Caltrain Schedules** - Official GTFS data with real train times
- 🚌 **Complete Shuttle Integration** - MV Connector timetables
- 🏠 **Personalized Addresses** - Door-to-door routing with your locations
- 🤖 **AI Recommendations** - Smart commute comparisons and suggestions
- ⚡ **Multi-Modal Planning** - Compare driving vs transit seamlessly

### 🎯 **Commute Intelligence Capabilities**

- 🚗 **Real-Time Driving**: Live traffic, route optimization, arrival predictions
- 🚂 **Live Transit Data**: Caltrain GTFS schedules with real train numbers
- 🚌 **Shuttle Integration**: Complete MV Connector timetables and connections
- 🏠 **Personal Routing**: Door-to-door accuracy with configured addresses
- ⏰ **Smart Timing**: Departure recommendations and transfer coordination
- 🤖 **AI Comparisons**: "Drive 45min vs Transit 63min" intelligent suggestions

### 🎯 **Key Features**

- ✅ **Complete Commute Intelligence** - Real traffic + transit integration 🆕
- ✅ **Live GTFS Data** - Official Caltrain schedules with caching 🆕
- ✅ **Personal Address Config** - Door-to-door routing accuracy 🆕
- ✅ **Advanced Caching System** - Redis + in-memory fallback
- ✅ **Complete Calendar CRUD** - Create, read, update, delete events
- ✅ **Smart Time Finding** - AI-powered scheduling with conflict detection
- ✅ **Real API Integrations** - Google Maps, Calendar, Weather, Financial APIs
- ✅ **Production Ready** - Deployed on Railway with health monitoring

## 🛠️ Available Tools

### 📊 **Read Operations**

#### 🌤️ Weather (`weather.get_daily`)

Get daily weather forecasts powered by OpenWeatherMap with intelligent caching.

- **Input**: `location` (string), `when` ("today" | "tomorrow")
- **Output**: Temperature highs/lows, precipitation chance, detailed summary
- **Real API**: ✅ OpenWeatherMap integration
- **Caching**: 🔥 Geocoding (7 days), Forecasts (30 min) - dramatically faster for repeated locations

#### 🚗 Basic Mobility (`mobility.get_commute`)

Get basic commute information between any two locations.

- **Input**: `origin`, `destination`, `mode` (driving/transit/walking/bicycling)
- **Output**: Duration, distance, route summary, traffic conditions
- **Real API**: ✅ Google Maps Directions API
- **Caching**: 🔥 Routes cached for 15 minutes - eliminates repeated API calls

#### 🚗🚂 **Commute Intelligence (`mobility.get_commute_options`)** 🆕

**Get comprehensive commute analysis with driving AND transit options!**

- **Input**: `direction` (to_work/from_work), `departure_time`, `include_driving`, `include_transit`
- **Output**: Complete commute analysis with AI recommendations
- **Features**:
  - 🏠 **Personal Addresses** - Uses configured home/work locations
  - 🚗 **Real-Time Driving** - Live traffic with Google Maps API
  - 🚂 **Live Caltrain Data** - Official GTFS schedules with real train numbers
  - 🚌 **MV Connector Shuttles** - Complete timetables and connections
  - ⏰ **Smart Timing** - Coordinated departure and transfer times
  - 🤖 **AI Recommendations** - "Drive 43min vs Transit 63min - drive recommended"
- **Perfect For**: _"How should I get to work?"_, _"What's the best way home?"_
- **Real APIs**: ✅ Google Maps + Caltrain GTFS + MV Connector data

#### 🚌 **Shuttle Schedules (`mobility.get_shuttle_schedule`)** 🆕

**Get detailed MV Connector shuttle schedules between specific stops.**

- **Input**: `origin`, `destination` (Mountain View Caltrain ↔ LinkedIn Transit Center ↔ LinkedIn 950|1000), `departure_time`
- **Output**: Next departures, travel times, service hours, frequency
- **Features**:
  - 🚌 **Complete Timetables** - All departure times from official schedules
  - ⏰ **Real-Time Queries** - Next available shuttles from current time
  - 📍 **All 3 Stops** - Mountain View Caltrain, LinkedIn Transit Center, LinkedIn 950|1000
  - 🕐 **Service Hours** - Morning (6:50 AM - 10:58 AM), Evening (3:16 PM - 6:42 PM)
- **Perfect For**: _"When's the next shuttle to LinkedIn?"_, _"What time does the shuttle leave MV Caltrain?"_
- **Data Source**: ✅ Official MV Connector timetables

#### 💰 Financial (`financial.get_data`)

Live stock and cryptocurrency data with smart caching to prevent rate limits.

- **Input**: `symbols` (array), `data_type` (stocks/crypto/mixed)
- **Output**: Real-time prices, changes, market status, portfolio summary
- **Real APIs**: ✅ Alpha Vantage (stocks) + CoinGecko (crypto)
- **Caching**: 🔥 Stocks (5 min), Crypto (2 min) - critical for Alpha Vantage's 5 calls/minute limit

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

#### 📅+ Calendar Create (`calendar.create_event`)

**Create new calendar events with intelligent conflict detection!**

- **Input**: `title`, `start_time`, `end_time`, `description`, `location`, `attendees`, `calendar_name`
- **Output**: Created event details, conflict warnings, Google Calendar URL
- **Features**:
  - ⚠️ **Smart Conflict Detection** - Warns about overlapping events
  - 🎯 **Multi-Calendar Support** - Target specific calendars (primary, work, etc.)
  - 🔗 **Real Integration** - Events appear in Google Calendar instantly
  - 📧 **Attendee Management** - Email invitations and notifications
- **Real API**: ✅ Google Calendar Events API with write permissions

#### 📅✏️ Calendar Update (`calendar.update_event`) 🆕

**Update existing calendar events with granular field changes!**

- **Input**: `event_id` (required), `title`, `start_time`, `end_time`, `description`, `location`, `attendees`, `calendar_name`
- **Output**: Updated event details, change tracking, conflict warnings for new times
- **Features**:
  - 🎯 **Partial Updates** - Only change the fields you specify
  - 📝 **Change Tracking** - See exactly what was modified
  - ⚠️ **Smart Conflict Detection** - Excludes the event being updated from conflicts
  - 🔄 **Real-Time Sync** - Changes appear in Google Calendar instantly
  - 📊 **Before/After Comparison** - Returns both original and updated event details
- **Real API**: ✅ Google Calendar Events API with update permissions

#### 📅🗑️ Calendar Delete (`calendar.delete_event`) 🆕

**Safely delete calendar events with confirmation details!**

- **Input**: `event_id`, `calendar_name` (optional)
- **Output**: Deleted event details for audit trail, success confirmation
- **Features**:
  - 🛡️ **Safe Deletion** - Retrieves event details before deletion for confirmation
  - 📋 **Audit Trail** - Returns complete event details for logging
  - ⚠️ **Error Handling** - Proper 404 responses for missing events
  - 🔗 **Real Integration** - Events removed from Google Calendar instantly
- **Real API**: ✅ Google Calendar Events API with delete permissions

### 🧠 **Smart Scheduling**

#### 📅🔍 Find Free Time (`calendar.find_free_time`) 🆕

**AI-powered smart scheduling that finds optimal available time slots!**

- **Input**: `duration_minutes`, `start_date`, `end_date`, `earliest_time`, `latest_time`, `preferred_time`, `max_results`
- **Output**: Ranked available time slots with preference scoring, conflict context
- **Features**:
  - 🎯 **Intelligent Time Finding** - Finds gaps between existing events
  - ⏰ **Duration-Based Search** - Specify exact time needed (30min - 8 hours)
  - 📅 **Multi-Day Search** - Search across date ranges for flexibility
  - 🕐 **Time Window Filtering** - Restrict to business hours or custom windows
  - 🌅 **Preference Scoring** - Prioritize morning, afternoon, or evening slots
  - 🚫 **All-Day Event Filtering** - Workouts and holidays don't block time slots
  - 🌍 **Timezone-Aware** - Proper handling of Google Calendar timezone data
  - 📊 **Conflict Context** - See events before/after each available slot
- **Perfect For**:
  - _"Find me 60 minutes free tomorrow afternoon"_
  - _"When can I schedule a 2-hour deep work session this week?"_
  - _"Show me 30-minute slots available between meetings"_
- **Real API**: ✅ Google Calendar integration with smart gap analysis

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

# Edit .env with your API keys and addresses
# Required for full functionality:
WEATHER_API_KEY=your_openweathermap_api_key
GOOGLE_MAPS_API_KEY=your_google_maps_api_key

# Personal addresses for accurate commute routing:
HOME_ADDRESS=123 Main St, Your City, State ZIP
WORK_ADDRESS=456 Work Ave, Work City, State ZIP
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

### Test Basic Mobility Tool

```bash
curl -X POST http://localhost:8000/tools/mobility.get_commute \
  -H "Content-Type: application/json" \
  -d '{"origin": "San Francisco", "destination": "Oakland", "mode": "driving"}'
```

### 🆕 Test Commute Intelligence

```bash
# Get complete morning commute analysis
curl -X POST http://localhost:8000/tools/mobility.get_commute_options \
  -H "Content-Type: application/json" \
  -d '{
    "direction": "to_work",
    "departure_time": "8:00 AM",
    "include_driving": true,
    "include_transit": true
  }'

# Get evening commute options
curl -X POST http://localhost:8000/tools/mobility.get_commute_options \
  -H "Content-Type: application/json" \
  -d '{
    "direction": "from_work",
    "departure_time": "5:00 PM",
    "include_driving": true,
    "include_transit": true
  }'
```

### 🆕 Test Shuttle Schedules

```bash
# Get next shuttles from Mountain View Caltrain to LinkedIn
curl -X POST http://localhost:8000/tools/mobility.get_shuttle_schedule \
  -H "Content-Type: application/json" \
  -d '{
    "origin": "mountain_view_caltrain",
    "destination": "linkedin_transit_center",
    "departure_time": "9:00 AM"
  }'
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

### 🆕 Test Calendar Event Update

```bash
curl -X POST http://localhost:8000/tools/calendar.update_event \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "your_event_id_here",
    "title": "Updated Team Meeting",
    "start_time": "2024-01-15T15:00:00",
    "end_time": "2024-01-15T16:00:00",
    "location": "Conference Room B"
  }'
```

### 🆕 Test Calendar Event Deletion

```bash
curl -X POST http://localhost:8000/tools/calendar.delete_event \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "your_event_id_here",
    "calendar_name": "primary"
  }'
```

### 🆕 Test Smart Time Finding

```bash
curl -X POST http://localhost:8000/tools/calendar.find_free_time \
  -H "Content-Type: application/json" \
  -d '{
    "duration_minutes": 60,
    "start_date": "2024-01-15",
    "end_date": "2024-01-16",
    "earliest_time": "09:00",
    "latest_time": "18:00",
    "preferred_time": "afternoon",
    "max_results": 3
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

### Google APIs (Maps & Calendar Tools)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable APIs:
   - **Directions API** (for real-time traffic & routing) 🆕
   - **Distance Matrix API** (for batch travel time calculations) 🆕
   - **Calendar API** (for calendar read/write)
4. Create credentials:
   - **API Key** for Maps APIs (secure with IP/HTTP referrer restrictions)
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

### 🏠 Personal Address Configuration

**For accurate commute routing, configure your real addresses:**

1. **Edit `.env` file** with your actual locations:

   ```bash
   HOME_ADDRESS=123 Your Street, Your City, State ZIP
   WORK_ADDRESS=456 Work Address, Work City, State ZIP

   # Caltrain stations (optional - defaults provided)
   HOME_CALTRAIN_STATION=South San Francisco
   WORK_CALTRAIN_STATION=Mountain View
   ```

2. **Address Format Best Practices**:

   - ✅ Use full addresses: `"123 Main St, South San Francisco, CA 94080"`
   - ✅ Include apartment/suite numbers for precision
   - ❌ Avoid vague locations: `"South SF"` or `"LinkedIn"`

3. **Benefits of Real Addresses**:
   - 🎯 **Door-to-door accuracy** instead of city-to-city estimates
   - 🚶 **Precise walking distances** to transit stations
   - 🚗 **Real traffic conditions** for your exact route
   - 🤖 **Better AI recommendations** based on your locations

**Note**: The server works without API keys/addresses using mock data for development/testing.

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
│   ├── clients/         # API clients (Google Calendar, Caltrain GTFS) 🆕
│   ├── utils/           # Shared utilities (caching, HTTP, shuttle data) 🆕
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

| Tool                    | Status      | API Provider                    | Features                                        |
| ----------------------- | ----------- | ------------------------------- | ----------------------------------------------- |
| 🌤️ Weather              | ✅ **Live** | OpenWeatherMap                  | Current conditions, forecasts                   |
| 🚗 Basic Mobility       | ✅ **Live** | Google Maps Directions          | Real-time traffic, routes                       |
| 🚗🚂 **Commute Intel**  | ✅ **Live** | **Google Maps + Caltrain GTFS** | **Complete commute analysis & recommendations** |
| 🚌 **Shuttle Schedule** | ✅ **Live** | **MV Connector Official Data**  | **Complete timetables, real-time queries**      |
| 📅 Calendar Read        | ✅ **Live** | Google Calendar                 | Multi-calendar support                          |
| 📅+ Calendar Write      | ✅ **Live** | Google Calendar                 | Event creation, conflict detection              |
| 💰 Financial            | ✅ **Live** | Alpha Vantage + CoinGecko       | Stocks + crypto prices                          |
| ✅ Todo                 | 🔄 **Mock** | Todoist (planned)               | Smart categorization                            |

## 🎯 **Current Capabilities**

- ✅ **8 Tools Total** - All with real API integration 🆕
- ✅ **Complete Commute Intelligence** - Real traffic + transit data 🆕
- ✅ **Live GTFS Integration** - Official Caltrain schedules 🆕
- ✅ **Personal Address Routing** - Door-to-door accuracy 🆕
- ✅ **Multi-Modal Planning** - Drive vs transit comparisons 🆕
- ✅ **Complete Calendar CRUD** - Create, read, update, delete events
- ✅ **Smart Time Finding** - AI-powered scheduling with conflict detection
- ✅ **Multi-Calendar Support** - Primary, Runna, Family calendars
- ✅ **Production Deployment** - Railway.app with auto-deployment

## 🔮 **Future Enhancements**

- 🚂 **Real-Time Delays** - Live Caltrain delay information from 511.org
- 🗺️ **Route Optimization** - Alternative route suggestions during traffic
- 📝 **Todo Write Operations** - Create, update, complete tasks
- 🧠 **Natural Language** - Enhanced parsing for relative times ("next Friday")
- 🎯 **Commute Learning** - Personalized recommendations based on patterns
- 👥 **Multi-tenancy** - Multiple user support
- 📱 **Push Notifications** - Traffic alerts and schedule changes

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

This isn't just another API - it's a **complete productivity assistant backend** with **real commute intelligence**:

- 🤖 **AI Agent Ready** - Purpose-built for LLM integration
- 🚗🚂 **Complete Commute Intelligence** - Real traffic + transit with AI recommendations 🆕
- 🏠 **Personalized Routing** - Door-to-door accuracy with your addresses 🆕
- 🔄 **Read + Write** - Both information retrieval AND action taking
- 🧠 **Smart Features** - Conflict detection, multi-calendar support, commute planning
- ⚡ **Real Integrations** - Google Maps, Caltrain GTFS, MV Connector, Calendar, Weather, Financial APIs
- 📱 **Production Deployed** - Working system you can use daily
- 🎯 **Personal Use** - Designed for individual productivity

### 🚀 **Perfect for Morning Routine AI Agents**

- _"How should I get to work?"_ → **43min driving (light traffic) vs 63min transit (next train 8:15 AM)**
- _"When's my next meeting?"_ → **Team sync at 2 PM in Conference Room A**
- _"What's the weather?"_ → **Partly cloudy, 72°F high, 20% rain chance**
- _"When should I leave for my 9 AM meeting?"_ → **Leave at 8:05 AM (driving) or catch 7:44 AM train**

**Happy coding!** 🚀 This MCP server demonstrates modern AI agent architecture with real-world integrations, commute intelligence, and write capabilities.
