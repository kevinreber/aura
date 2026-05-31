# Changelog - Daily MCP Server

All notable changes to the Daily MCP Server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.0] - 2026-05-31 — Brain-Vault Integration

Adds tools that let the agent answer questions from a personal markdown
knowledge base (Kevin's `~/Projects/brain-vault/`) and renames every MCP
tool to `namespace_action` form so Claude Desktop's chat API can route
to them.

### Added — Brain-Vault MCP tools

Three new ripgrep-backed tools that operate on the markdown tree at
`VAULT_ROOT`:

- **`vault_search`** — full-text search via `rg --json`, ranked hits with surrounding context, optional folder scoping, `.auraignore` exclusion support.
- **`vault_read`** — read a single markdown file. Caps at 1 MB (`_MAX_READ_BYTES = 1_000_000`), rejects absolute paths and `..` traversal.
- **`vault_list`** — one-level directory listing. Hides dotfiles by default.

All three tools share path-traversal guards in `_resolve_vault_path` and
raise `VaultUnavailableError` if `VAULT_ROOT` isn't configured. Shipped
in [#22](https://github.com/kevinreber/aura/pull/22) with three
follow-up review passes (correctness / security / style polish).

### Added — Brain-vault git sync

The server can now keep the vault fresh in production where there's no
bind-mount available:

- Set `VAULT_GIT_URL` + `VAULT_GIT_TOKEN` (fine-grained PAT, `Contents: Read-only` on one repo).
- On boot, if `VAULT_ROOT` is empty, the server clones the repo via an asyncio background task.
- Subsequently `git pull`s every 15 minutes (`SYNC_INTERVAL_SECS = 15 * 60`).
- Worst-case end-to-end freshness: ~30 minutes (vault → GitHub + GitHub → Fly).
- Bind-mount detected (populated dir, no `.git`) → server warns and skips sync.
- All sync failures are logged and swallowed; the server never refuses to boot.

Shipped in [#26](https://github.com/kevinreber/aura/pull/26).

### Changed — Tool name format

Renamed every MCP tool from `namespace.action` to `namespace_action` for
Claude Desktop chat-API compatibility. Claude Desktop validates tool
names against `^[a-zA-Z0-9_-]{1,64}$`, which rejects dots — meaning the
old names loaded fine but errored on actual use.

Affected tools (all):

- `weather.get_daily` → `weather_get_daily`
- `mobility.get_commute` → `mobility_get_commute`
- `mobility.get_commute_options` → `mobility_get_commute_options`
- `mobility.get_shuttle_schedule` → `mobility_get_shuttle_schedule`
- `calendar.list_events` / `list_events_range` / `create_event` / `update_event` / `delete_event` / `find_free_time` → underscore form
- `todo.list` / `create` / `update` / `complete` / `delete` → underscore form
- `financial.get_data` → `financial_get_data`
- `weekend.get_trails` / `get_concerts` / `generate_itinerary` → underscore form

Shipped in [#24](https://github.com/kevinreber/aura/pull/24) (closes #23).

### Fixed

- **Pre-create `/vault` directory owned by `appuser` in the prod image** so the asyncio sync task can clone into it without permission errors. ([#27](https://github.com/kevinreber/aura/pull/27))
- **Bump git command timeout from 60s to 300s** for cold vault clones on Fly's first-boot. The default was too aggressive for large vaults. (commit d6aefc6)

## [0.5.0] - 2025-08-23 - 🚗🚂 **MAJOR: Complete Commute Intelligence System**

### 🎉 **COMMUTE REVOLUTION: Real Traffic & Transit Integration**

A complete transformation of the mobility system with real-time traffic data, live transit schedules, and AI-powered commute intelligence.

- **🚗 Real-Time Traffic Data**: Google Maps API integration with live conditions
- **🚂 Live Caltrain Schedules**: Official GTFS data with real train numbers
- **🚌 Complete Shuttle Integration**: MV Connector timetables from official sources
- **🏠 Personal Address Configuration**: Door-to-door routing accuracy
- **🤖 AI Commute Recommendations**: Intelligent comparisons and suggestions

### ✨ **New Tools & Features**

#### **🚗🚂 Comprehensive Commute Analysis**

- **`mobility_get_commute_options`** - Complete morning/evening commute intelligence
  - Real-time driving conditions with traffic analysis
  - ⛽ **NEW**: EPA-based fuel consumption estimates (26 MPG average)
  - 🗺️ **NEW**: Clean route format ("South SF → LinkedIn" vs highway names)
  - Live Caltrain schedules with next departures
  - MV Connector shuttle connections and timing
  - AI recommendations comparing all options
  - Personalized routing using configured addresses

#### **🚌 Shuttle Schedule Integration**

- **`mobility_get_shuttle_schedule`** - MV Connector schedule queries
  - Complete timetables for all 3 stops (MV Caltrain ↔ LinkedIn Transit Center ↔ LinkedIn 950|1000)
  - Real-time next departure calculations
  - Service hours validation (morning 6:50 AM - 10:58 AM, evening 3:16 PM - 6:42 PM)
  - 📅 **NEW**: Weekend detection (Monday-Friday service only)
  - Travel time matrix between all stops

#### **🏠 Personal Address Configuration**

- **Address-based routing** with home/work configuration
- **Environment variable support** for `HOME_ADDRESS` and `WORK_ADDRESS`
- **Smart fallbacks** to generic locations for development
- **Production validation** ensures addresses are configured

### 🛠️ **Enhanced Architecture**

#### **🚂 Caltrain GTFS Client** (`mcp_server/clients/caltrain.py`)

- **Official GTFS data** downloaded from Trillium Transit
- **Smart caching** with 12-hour TTL and daily updates
- **Station lookup** with fuzzy matching capabilities
- **Schedule queries** between any two stations
- **Real train numbers** and arrival predictions
- **Error handling** with mock data fallbacks

#### **🚌 MV Connector Data** (`mcp_server/utils/shuttle_data.py`)

- **Complete schedule extraction** from official timetables
- **All departure times** for inbound (morning) and outbound (evening) routes
- **Travel time calculations** between all stop combinations
- **Service validation** with real-time status checking
- **Next departure logic** with day rollover handling

#### **📋 Enhanced Schemas** (`mcp_server/schemas/mobility.py`)

- **`CommuteInput/Output`** - Comprehensive commute analysis
- **`ShuttleScheduleInput/Output`** - Detailed shuttle queries
- **`CaltrainDeparture`** - Structured train departure data
- **`TransitOption`** - Multi-modal transit analysis
- **`DrivingOption`** - Enhanced driving conditions

### 🎯 **Real-World Integration**

#### **📊 Data Sources**

- **Google Maps Directions API** - Real-time traffic and routing
- **Caltrain GTFS Feed** - Official schedules from https://data.trilliumtransit.com/
- **MV Connector Timetables** - Official shuttle schedules
- **Smart Caching** - Redis integration with appropriate TTLs

#### **🤖 AI Intelligence**

- **Context-aware recommendations** based on real-time conditions
- **Time comparisons** - "Drive 43min vs Transit 63min"
- **Traffic-aware suggestions** - Heavy traffic = prefer transit
- **Personalized routing** using configured home/work addresses

### 📚 **Documentation & Setup**

#### **📖 New Documentation**

- **`COMMUTE_INTELLIGENCE.md`** - Comprehensive setup and usage guide
- **Updated `README.md`** - Complete feature overview and examples
- **Configuration examples** - Address setup and API key management
- **Testing scripts** - Validation and troubleshooting tools

#### **⚙️ Configuration Enhancements**

- **Address validation** in production environment
- **Google Maps API setup** documentation
- **Interactive setup tools** for address configuration
- **Environment variable templates** updated

### 🧪 **Testing & Quality**

#### **🔍 Comprehensive Testing**

- **End-to-end workflow validation** with real addresses
- **API integration testing** for Google Maps and Caltrain GTFS
- **Mock data fallbacks** ensure reliability
- **Configuration validation** tools

### 💡 **Perfect for AI Agents**

Your AI assistant can now answer:

- _"How should I get to work?"_ → **Real-time traffic vs transit comparison**
- _"When's the next train to Mountain View?"_ → **Live Caltrain schedules**
- _"What time should I leave for my 9 AM meeting?"_ → **Coordinated departure timing**
- _"Is there traffic on my commute?"_ → **Current conditions and alternatives**

### 🚀 **Performance & Reliability**

- **Intelligent caching** reduces API costs and improves speed
- **Graceful fallbacks** when external APIs unavailable
- **Rate limiting protection** for Google Maps API usage
- **Error handling** ensures system stability

---

## [0.4.0] - 2025-08-21 - 🚀 **MAJOR: Advanced Caching System**

### 🎉 **PERFORMANCE REVOLUTION: Intelligent Caching Layer**

- **🔥 60-90% API Call Reduction**: Dramatically reduced external API calls through intelligent caching
- **⚡ Instant Response Times**: Cached data returns instantly for repeated requests
- **🛡️ Rate Limiting Protection**: Complete solution for Alpha Vantage's 5 calls/minute limit
- **📊 Redis + In-Memory Fallback**: Production-ready caching with reliability built-in

### ✨ **New Features**

- **Advanced Cache Service** (`mcp_server/utils/cache.py`)

  - Redis primary cache with async support
  - In-memory fallback for development/reliability
  - Smart TTL values optimized per data type
  - JSON serialization for complex objects
  - Automatic cache invalidation for calendar operations

- **Cache Monitoring**
  - `GET /cache/stats` - Real-time cache performance metrics
  - Debug logging for cache hits/misses/operations
  - Memory usage tracking

### 🔧 **Enhanced Tools with Caching**

- **Weather Tool**:

  - Geocoding cached for 7 days (coordinates never change)
  - Weather forecasts cached for 30 minutes
  - Eliminates repeated location lookups

- **Financial Tool**:

  - Stock data cached for 5 minutes (market volatility consideration)
  - Crypto data cached for 2 minutes (higher volatility)
  - **Critical for Alpha Vantage rate limits** - prevents API quota exhaustion

- **Mobility Tool**:

  - Direction routes cached for 15 minutes
  - Traffic-aware caching duration
  - Major savings for common commute routes

- **Calendar Tool**:
  - Events cached for 10 minutes with smart invalidation
  - Cache automatically cleared when events are created/updated/deleted
  - Range queries optimized for dashboard loading

### 📊 **Performance Improvements**

- **API Call Reduction**:

  - Financial: Up to 100% reduction for cached symbols
  - Weather: Up to 50% reduction (geocoding cached)
  - Calendar: Up to 100% reduction for recent queries
  - Mobility: Up to 100% reduction for common routes

- **Response Time Improvements**:
  - Cache hits: ~0.1ms (in-memory) to ~1ms (Redis)
  - API calls avoided: 500ms-5000ms saved per cached response
  - Dashboard loading: Significantly faster for repeated data

### 🔧 **Configuration & Deployment**

- **Optional Redis Configuration**:

  ```bash
  REDIS_URL=redis://localhost:6379  # Optional - uses in-memory if not set
  CACHE_TTL=300  # Default TTL override
  ```

- **Production Ready**:
  - Graceful degradation when Redis unavailable
  - No breaking changes to existing API
  - Comprehensive error handling

### 📚 **Documentation**

- **Added CACHING_GUIDE.md**: Complete implementation guide with TTL strategy, monitoring, and troubleshooting

## [0.3.0] - 2025-08-20 - 🚀 **PHASE 2.1 COMPLETE: Full Calendar CRUD**

### 🎉 **MAJOR MILESTONE: Complete Calendar Management**

- **Full Calendar CRUD Operations**: Create, Read, Update, Delete calendar events
- **Production-Ready Calendar Integration**: Real Google Calendar API integration with comprehensive error handling
- **Enhanced Conflict Detection**: Smart conflict detection for both creation and updates
- **Change Tracking**: Detailed tracking of what fields are modified during updates

### ✨ **New Tools**

- `calendar_update_event` - Update existing calendar events with granular field updates

  - Partial updates (only change specified fields)
  - Enhanced conflict detection (excludes event being updated)
  - Change tracking (reports exactly what was modified)
  - Support for all event properties (title, time, location, attendees, etc.)

- `calendar_delete_event` - Delete calendar events safely
  - Pre-deletion event retrieval for confirmation
  - Comprehensive error handling (404 for missing events, 403 for permissions)
  - Event details returned for audit trail

### 🔧 **API Enhancements**

- **New Endpoints**:
  - `POST /tools/calendar_update_event` - Update calendar events
  - `POST /tools/calendar_delete_event` - Delete calendar events
- **Enhanced Schemas**: `CalendarUpdateInput/Output` and `CalendarDeleteInput/Output`
- **Improved Error Responses**: Proper HTTP status codes (404 for missing events)
- **Advanced Validation**: Field-level validation for updates with timezone awareness

### 🐛 **Critical Bug Fixes**

- **Fixed Calendar Reading Bug**: Resolved duplicate `_convert_google_event` method causing parameter mismatch
- **Event Discovery Issue**: Calendar events now properly readable (was showing "no events" despite events existing)
- **Method Signature Conflicts**: Eliminated conflicting method signatures in Google Calendar client

### 📊 **Enhanced Capabilities**

- **Complete Calendar Management**: Users can now fully manage their calendar through AI
- **Smart Conflict Resolution**: Advanced logic to prevent double-booking during updates
- **Audit Trail**: Complete tracking of calendar operations for debugging and compliance
- **Production Reliability**: Robust error handling and graceful degradation

### 🔄 **Updated Tool Capabilities**

- **Read Operations**:

  - `weather_get_daily` - Weather forecasts via OpenWeatherMap
  - `calendar_list_events` - Single date calendar events (✅ **FIXED**)
  - `calendar_list_events_range` - Multi-day calendar events
  - `todo_list` - Task management with filtering
  - `mobility_get_commute` - Travel times via Google Maps
  - `financial_get_data` - Stock/crypto prices

- **Write Operations**:
  - `calendar_create_event` - Create calendar events with conflict detection
  - `calendar_update_event` - **NEW**: Update existing events with change tracking
  - `calendar_delete_event` - **NEW**: Delete calendar events safely

### 🎯 **User Experience Improvements**

**AI Assistant can now handle complete calendar management:**

- _"Remove my 4pm workout tomorrow"_ ✅
- _"Move my meeting to 3pm"_ ✅
- _"Update the location to Conference Room B"_ ✅
- _"Add Sarah to my client presentation"_ ✅
- _"Cancel that duplicate lunch meeting"_ ✅

### 🚀 **Production Impact**

- **Zero Downtime**: Hot deployment of new features
- **Backward Compatibility**: All existing integrations continue working
- **Enhanced Monitoring**: Improved logging for calendar operations
- **Performance**: Optimized calendar client initialization

---

## [0.2.0] - 2025-08-20 - 🎉 **PHASE 1.5 COMPLETE: First Write Tool**

### 🚀 **Major Features Added**

- **Calendar Event Creation**: Added `calendar_create_event` tool - first write operation!
- **Smart Conflict Detection**: Automatically detects overlapping events when creating new ones
- **Multi-Calendar Support**: Works with Primary, Runna, Family, and other Google calendars
- **Enhanced Google Calendar Integration**: Added write permissions and full CRUD capabilities

### ✨ **New Tools**

- `calendar_create_event` - Create new calendar events with rich metadata
  - Support for title, start/end times, location, description, attendees
  - Automatic conflict detection with existing events
  - Multi-calendar targeting (primary, work, personal, etc.)
  - All-day event support

### 🔧 **API Enhancements**

- **New Endpoint**: `POST /tools/calendar_create_event`
- **Enhanced Schemas**: `CalendarCreateInput` and `CalendarCreateOutput` with comprehensive validation
- **Improved Error Handling**: Graceful fallbacks when Google Calendar API unavailable
- **OAuth Scope Updates**: Added `calendar.events` scope for write permissions

### 📊 **Infrastructure Improvements**

- **MCP Server Registration**: New tool properly registered in server tool registry
- **Swagger Documentation**: Comprehensive API documentation for new endpoint
- **Logging Enhancements**: Detailed logging for event creation and conflict detection
- **Schema Validation**: Full Pydantic validation for all calendar operations

### 🔄 **Tool Capabilities**

- **Read Operations**:

  - `weather_get_daily` - Weather forecasts via OpenWeatherMap
  - `calendar_list_events` - Single date calendar events
  - `calendar_list_events_range` - Multi-day calendar events (efficient batching)
  - `todo_list` - Task management with filtering
  - `mobility_get_commute` - Travel times via Google Maps
  - `financial_get_data` - Stock/crypto prices via Alpha Vantage & CoinGecko

- **Write Operations**:
  - `calendar_create_event` - Create calendar events with conflict detection

### 🐛 **Bug Fixes**

- Fixed timezone handling in calendar operations
- Improved datetime parsing for various formats
- Enhanced error messages for API failures

### 📱 **Deployment**

- **Production Ready**: Deployed to Railway with auto-deployment
- **Environment Variables**: Proper secrets management for API keys
- **Health Monitoring**: Enhanced health check endpoints

---

## [0.1.0] - 2025-08-18 - 🎯 **PHASE 0 COMPLETE: MVP Foundation**

### 🚀 **Initial Release**

- **MCP Server Foundation**: Flask-based Model Context Protocol server
- **5 Core Read Tools**: Weather, Calendar, Financial, Mobility, Todos
- **Google Calendar Integration**: Real-time calendar data from multiple calendars
- **External API Integrations**: OpenWeatherMap, Google Maps, Alpha Vantage, CoinGecko

### ✨ **Core Features**

- **Health Monitoring**: `/health` endpoint for service monitoring
- **Tool Discovery**: `/tools` endpoint for dynamic tool discovery
- **Interactive Documentation**: Swagger UI at `/docs`
- **CORS Support**: Cross-origin requests for frontend integration
- **Rate Limiting**: Built-in rate limiting for API protection

### 🔧 **Technical Foundation**

- **Flask + AsyncIO**: Async support for concurrent API calls
- **Pydantic Validation**: Schema validation for all inputs/outputs
- **Structured Logging**: Loguru-based logging with tool call tracking
- **Configuration Management**: Environment-based configuration
- **Docker Support**: Containerized deployment

### 📊 **External Integrations**

- **Google Calendar API**: Multi-calendar support (Primary, Runna, Family)
- **OpenWeatherMap**: Real-time weather and forecasting
- **Google Maps**: Commute times and traffic information
- **Alpha Vantage**: Stock market data
- **CoinGecko**: Cryptocurrency prices

### 🚀 **Deployment**

- **Railway.app**: Production deployment with auto-scaling
- **Environment Variables**: Secure API key management
- **GitHub Integration**: Auto-deployment on push to main

---

## [Unreleased] - 🔮 **Future Enhancements**

### 🎯 **Phase 2 - Smart Scheduling & Enhanced Features**

- **Smart Scheduling**: AI-powered optimal meeting time suggestions
- **Natural Language Parsing**: Better understanding of relative times ("next Tuesday", "in 2 hours")
- **Calendar Update/Delete**: Complete CRUD operations for calendar events
- **Multi-tenancy**: Support for multiple users with isolated data
- **Event Reminders**: Automated reminder system
- **Recurring Events**: Support for recurring calendar events

### 🔧 **Technical Improvements**

- **Response Caching**: Redis-based caching for frequently accessed data
- **Circuit Breakers**: Resilient external API integration
- **Metrics Collection**: Prometheus metrics for monitoring
- **Enhanced Testing**: Comprehensive test suite with mocking
- **Performance Optimization**: Async optimizations and connection pooling

### 🌟 **Advanced Features**

- **Voice Integration**: Voice command support for event creation
- **Email Integration**: Calendar invitations and notifications
- **Team Scheduling**: Multi-user calendar coordination
- **AI-Powered Insights**: Daily/weekly schedule optimization suggestions

---

## Development Notes

### **Architecture**

- **MCP Protocol**: Model Context Protocol for AI agent integration
- **Tool-Based Design**: Modular tools for specific capabilities
- **Schema-First**: Pydantic schemas ensure type safety and validation
- **Async-First**: Built for concurrent operations and scalability

### **Code Organization**

```
mcp_server/
├── tools/          # Individual tool implementations
├── schemas/        # Pydantic schemas for validation
├── clients/        # External API clients (Google, etc.)
├── utils/          # Shared utilities (logging, HTTP)
└── config.py       # Configuration management
```

### **External Dependencies**

- **Google Calendar API**: OAuth2 authentication with read/write scopes
- **OpenWeatherMap API**: Weather data with free tier limits
- **Google Maps API**: Direction and traffic data
- **Financial APIs**: Alpha Vantage (stocks) + CoinGecko (crypto)

### **Environment Variables**

See `.env.example` for required configuration variables.
