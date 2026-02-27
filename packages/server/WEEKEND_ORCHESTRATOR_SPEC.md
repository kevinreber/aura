# Weekend Orchestrator - Feature Spec

**Status**: Draft
**Date**: 2026-02-27
**Scope**: New tool module for the existing Aura MCP Server + Agent orchestration layer

---

## 1. Problem Statement

Weekend planning carries a "planning tax" - the cognitive overhead of scouting trails, checking concert listings, and stitching together multi-day itineraries across multiple apps and websites. The Weekend Orchestrator eliminates this by giving the AI agent tools to do the research and propose cohesive plans.

## 2. Architecture Decision

### Integrate into existing Aura MCP Server (Recommended)

Rather than spinning up a separate MCP server, these tools should be added as a new module within `packages/server/mcp_server/tools/`. This approach:

- Reuses existing infrastructure (caching, HTTP client, config, logging)
- Shares the same MCP/SSE transport already consumed by the agent
- Avoids fragmenting the monorepo with a second server process
- Follows the established pattern used by weather, calendar, mobility, todo, and financial tools

### Layer Separation

| Layer | Package | Responsibility |
|-------|---------|----------------|
| **Tools** (data fetching) | `packages/server` | Call external APIs, return structured data |
| **Orchestration** (intelligence) | `packages/agent` | "Friday Morning Routine", cross-tool reasoning, proactive suggestions |
| **UI** (presentation) | `packages/ui` | Weekend planner widget, itinerary view |

---

## 3. Tool Definitions

### 3.1 `weekend.get_trails`

Scout outdoor trails and activities near a given location.

**Primary Provider**: [Outdooractive API](https://developers.outdooractive.com/) (public API with free tier)
**Fallback Provider**: Google Maps Places API (search for trails/parks, already integrated)

> **Note on AllTrails/Komoot**: Neither offers a stable public API. AllTrails requires scraping (fragile, TOS risk). Komoot has an undocumented API that can break without notice. Outdooractive has an official developer program. If Outdooractive proves insufficient, Apify scraping of AllTrails is a last resort but should not be the primary strategy.

```
Input:
  location: str           # City or region (e.g., "Boulder, CO")
  activity_type: str      # "hiking" | "running" | "cycling" | "all"
  max_distance_miles: int  # Max trail distance (default: 25)
  difficulty: str | None  # "easy" | "moderate" | "hard" | None (any)

Output:
  trails: list[Trail]
    - name: str
    - distance_miles: float
    - elevation_gain_ft: int
    - difficulty: str
    - rating: float
    - url: str
    - location: str
  source: str             # Which provider was used
  cached: bool
```

**Cache TTL**: 24 hours (trail data doesn't change frequently)

### 3.2 `weekend.get_concerts`

Find upcoming concerts and live music events for tracked artists or by location.

**Primary Provider**: [Bandsintown API](https://artists.bandsintown.com/support/api-installation)

> **Note on Songkick**: Songkick's public API was deprecated. Bandsintown is the actively maintained alternative with a free developer API.

```
Input:
  location: str           # City (e.g., "Denver, CO")
  artists: list[str]      # Specific artists to track (optional)
  radius_miles: int       # Search radius (default: 50)
  date_range_days: int    # How far ahead to look (default: 14)

Output:
  events: list[ConcertEvent]
    - artist: str
    - venue: str
    - date: str           # ISO date
    - time: str | None
    - ticket_url: str | None
    - ticket_status: str  # "available" | "sold_out" | "unknown"
    - on_sale_date: str | None
  cached: bool
```

**Cache TTL**: 1 hour (event listings update frequently near show dates)

### 3.3 `weekend.generate_itinerary`

Generate a structured multi-day itinerary for a destination.

**Provider**: Google Maps Places API + Google Maps Directions API (both already integrated in `mobility.py`)

> **Note on Layla AI**: Layla is a consumer travel product, not an API service. Instead, this tool should aggregate POI data from Google Places and return structured data. The AI agent (LLM layer) handles the narrative synthesis and optimization - that's what LLMs are good at.

```
Input:
  destination: str        # City or region (e.g., "Denver, CO")
  duration_days: int      # Number of days (1-7)
  interests: list[str]    # e.g., ["outdoors", "live music", "craft beer", "food"]
  base_location: str | None  # Hotel/Airbnb address for transit estimates

Output:
  destination: str
  duration_days: int
  points_of_interest: list[POI]
    - name: str
    - category: str       # "restaurant" | "attraction" | "nightlife" | "outdoors"
    - rating: float
    - address: str
    - hours: str | None
    - price_level: int | None  # 1-4
    - description: str
  transit_estimates: list[TransitEstimate] | None  # Only if base_location provided
    - from_location: str
    - to_location: str
    - drive_time_min: int
    - distance_miles: float
  cached: bool
```

**Cache TTL**: 12 hours (place data is relatively stable)

> **Design Note**: This tool intentionally returns raw POIs and transit data rather than a formatted itinerary. The agent's LLM synthesizes the day-by-day plan using this data plus context from `get_trails` and `get_concerts`. This keeps the MCP server as a pure data layer.

---

## 4. Implementation Plan

### Phase 1: Foundation (Server-Side Tools)

**Location**: `packages/server/mcp_server/`

#### Step 1: Schemas

Create `mcp_server/schemas/weekend.py`:
- `TrailSearchInput` / `TrailSearchOutput`
- `ConcertSearchInput` / `ConcertSearchOutput`
- `ItineraryInput` / `ItineraryOutput`
- Supporting models: `Trail`, `ConcertEvent`, `POI`, `TransitEstimate`

#### Step 2: Tool Implementation

Create `mcp_server/tools/weekend.py`:
- `WeekendTools` class following existing tool patterns
- Methods: `get_trails()`, `get_concerts()`, `generate_itinerary()`
- Use existing `HttpClient` wrapper from `utils/http_client.py`
- Use existing cache infrastructure from `utils/cache.py`

#### Step 3: Registration

- Register tools in `mcp_server/server.py`
- Add routes in `mcp_server/app.py`
- Update `__init__.py` files

#### Step 4: Tests

Create `tests/test_tools/test_weekend.py`:
- Mock external API responses
- Test cache behavior
- Test error handling (API down, rate limited, invalid input)

### Phase 2: Agent Integration

**Location**: `packages/agent/src/daily_ai_agent/`

#### Step 5: LangChain Tools

Add to `agent/tools.py`:
- `TrailScoutTool` - wraps `weekend.get_trails`
- `ConcertAlertTool` - wraps `weekend.get_concerts`
- `ItineraryTool` - wraps `weekend.generate_itinerary`

Register in `agent/orchestrator.py`.

#### Step 6: Weekend Planner Prompt

Create a specialized prompt/chain that:
1. Checks calendar for free weekends (using existing `calendar.find_free_time`)
2. Calls `weekend.get_trails` and `weekend.get_concerts` for the user's location
3. Cross-references interests with available activities
4. Uses `weekend.generate_itinerary` if a trip is warranted
5. Synthesizes a cohesive weekend proposal

This is the "Friday Morning Routine" - an agent-layer orchestration, not a server tool.

### Phase 3: User Preferences (Resource)

**Location**: `packages/server/mcp_server/`

Add an MCP Resource for user weekend preferences:

```json
{
  "favorite_artists": ["Khruangbin", "Tycho", "Bonobo"],
  "activity_preferences": ["cycling", "hiking"],
  "max_drive_hours": 4,
  "budget_level": "moderate",
  "home_base": "San Francisco, CA"
}
```

Stored as a local JSON file, exposed as an MCP resource the agent can read.

### Phase 4: UI Integration

**Location**: `packages/ui/app/`

- Weekend planner dashboard widget
- Itinerary view component
- Concert alert cards
- Trail recommendation cards

---

## 5. API Key Requirements

| Service | Key Required | Free Tier | Notes |
|---------|-------------|-----------|-------|
| Bandsintown | App ID | Yes (free) | Register at artists.bandsintown.com |
| Outdooractive | API Key | Yes (limited) | Developer program application |
| Google Maps Places | API Key | $200/mo credit | Already integrated in Aura |
| Google Maps Directions | API Key | $200/mo credit | Already integrated in Aura |

**New `.env` variables**:
```bash
BANDSINTOWN_APP_ID=your_app_id
OUTDOORACTIVE_API_KEY=your_key    # Optional if using Google Places fallback
```

---

## 6. Caching Strategy

Follows existing patterns in `mcp_server/utils/cache.py`:

| Data Type | TTL | Rationale |
|-----------|-----|-----------|
| Trail data | 24 hours | Trails don't change day-to-day |
| Concert listings | 1 hour | Ticket status and new shows update frequently |
| POI / Places data | 12 hours | Business hours and ratings are relatively stable |
| Transit estimates | 15 minutes | Aligns with existing commute cache TTL |
| User preferences | No cache | Read from local file, always fresh |

---

## 7. Error Handling

Follow existing patterns:

- **API unavailable**: Return empty results with `error` field, log warning. Don't crash.
- **Rate limited**: Return cached data if available, otherwise inform caller of limit.
- **Invalid location**: Return structured error with suggestion (e.g., "Did you mean Denver, CO?")
- **Missing API key**: Skip that provider, fall back to alternatives, log info-level notice.

---

## 8. Security & Privacy

- **Location granularity**: Only send city/zip to external APIs, never exact addresses
- **Artist preferences**: Stored locally in a JSON file, never sent to third parties
- **API keys**: Managed through existing Pydantic Settings / `.env` pattern
- **No user tracking**: Tools are stateless; the agent handles session context

---

## 9. Open Questions

- [ ] **Outdooractive vs. Google Places for trails**: Outdooractive has richer trail data (elevation, difficulty, GPX routes) but requires an additional API key. Google Places is already integrated but returns generic "park" results. Start with Google Places and upgrade?
- [ ] **Spotify integration for concert matching**: Phase 3 mentions cross-referencing "Recently Played" with concert listings. This would require Spotify API OAuth. Worth the complexity for v1, or defer?
- [ ] **Proactive notifications**: Should the "Friday Morning Routine" run on a cron schedule and push notifications, or only trigger when the user asks? Cron requires infrastructure changes (task scheduler).

---

## 10. Success Criteria

**v1 (Tools working)**:
- [ ] Agent can answer "Find me hiking trails near Boulder" with real data
- [ ] Agent can answer "Are any of my favorite artists playing in Denver this month?"
- [ ] Agent can answer "Plan a weekend trip to Denver with hiking and live music"

**v2 (Orchestration working)**:
- [ ] Agent proactively suggests weekend plans based on calendar gaps
- [ ] Agent cross-references trail conditions, concerts, and weather in a single proposal
- [ ] User preferences influence recommendations without explicit prompting

---

## 11. File Manifest (Planned Changes)

```
packages/server/
  mcp_server/
    schemas/weekend.py          # NEW - Pydantic models
    tools/weekend.py            # NEW - WeekendTools class
    server.py                   # MODIFY - Register new tools
    app.py                      # MODIFY - Add routes
    config.py                   # MODIFY - Add new API key settings
    tools/__init__.py           # MODIFY - Export WeekendTools
    schemas/__init__.py         # MODIFY - Export weekend schemas
  tests/
    test_tools/test_weekend.py  # NEW - Unit tests

packages/agent/
  src/daily_ai_agent/
    agent/tools.py              # MODIFY - Add 3 new LangChain tools
    agent/orchestrator.py       # MODIFY - Register new tools

packages/ui/
  app/components/               # NEW - Weekend planner components (Phase 4)

.env.example                    # MODIFY - Add BANDSINTOWN_APP_ID, OUTDOORACTIVE_API_KEY
```
