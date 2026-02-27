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

## 2.1 Cross-Tool Synergy (Existing Tools)

A key advantage of building inside the existing Aura server is leveraging tools that are already built. The Weekend Orchestrator should not operate in isolation - the agent should combine weekend tools with existing tools for richer recommendations.

| Existing Tool | Weekend Use Case |
|---------------|-----------------|
| `weather.get_daily` | Check forecast before recommending outdoor trails. Rainy Saturday? Suggest indoor concerts instead. |
| `calendar.list_events` / `calendar.find_free_time` | Identify open weekends before planning. No point scouting trails if Saturday is fully booked. |
| `calendar.create_event` | **Write-back**: When user accepts a plan, auto-create calendar events for the trip, concert, trail outing. |
| `mobility.get_commute` | Estimate drive time from home to trailhead or concert venue. |
| `todo.create` | Save a proposed weekend plan as a todo item for later review ("Research Airbnbs in Denver"). |

This cross-referencing happens at the **agent layer** (not the server), but the spec should make the data dependencies explicit so tool outputs are compatible.

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

## 9. Mock Data for Local Development

Following the existing pattern (see `weather.py` `_get_mock_weather_data()`), each weekend tool should return realistic mock data when API keys are missing. This enables frontend and agent development without requiring every developer to have Bandsintown/Outdooractive keys.

```python
# Pattern from existing weather tool:
if not self.settings.bandsintown_app_id:
    logger.warning("No Bandsintown API key configured, returning mock data")
    return self._get_mock_concert_data(city)
```

**Mock data fixtures** should be stored in `tests/fixtures/weekend/` for reuse in both dev mode and tests:
- `mock_trails.json` - 3-5 sample trails with realistic data
- `mock_concerts.json` - 3-5 sample events with varied ticket statuses
- `mock_pois.json` - 10-15 sample POIs across categories

---

## 10. Rate Limiting

| Provider | Rate Limit | Strategy |
|----------|-----------|----------|
| Bandsintown | 1 req/sec (undocumented soft limit) | Cache aggressively (1hr TTL), add 1s delay between batch artist lookups |
| Outdooractive | 1000 req/day (free tier) | Cache 24hr, batch requests where possible |
| Google Maps Places | Pay-per-use ($17/1000 calls for Nearby Search) | Cache 12hr, limit POI results to `duration_days * 8` max |
| Google Maps Directions | Pay-per-use ($5/1000 calls) | Cache 15min, reuse existing mobility tool infrastructure |

### Google Maps API Cost Estimation

The `generate_itinerary` tool makes the most API calls. Estimated cost per itinerary:

| Operation | Calls | Cost per 1000 | Estimate |
|-----------|-------|---------------|----------|
| Nearby Search (per interest category) | ~4 | $17 | $0.068 |
| Place Details (top results) | ~12 | $17 | $0.204 |
| Directions (transit estimates) | ~6 | $5 | $0.030 |
| **Total per itinerary** | | | **~$0.30** |

With caching, repeated lookups for the same city are free for 12 hours. Recommend a soft limit of **20 itinerary generations per day** during development to cap spend.

---

## 11. Seasonal & Contextual Awareness

Trail and activity recommendations should be context-aware:

| Factor | How It Affects Recommendations | Data Source |
|--------|-------------------------------|-------------|
| **Weather** | Rain/snow → deprioritize outdoor trails, promote indoor events | `weather.get_daily` (existing tool) |
| **Season** | Winter → ski trails, snowshoeing; Summer → water activities, shade preference | Date-based logic |
| **Time of day** | Sunset time affects trail feasibility, evening = concert window | Computed from location/date |
| **Trail conditions** | Seasonal closures, wildfire alerts, flood warnings | Outdooractive API metadata / NWS alerts |

This logic lives in the **agent orchestration layer** (Phase 2), not the server tools. The server returns raw data; the agent applies judgment.

---

## 12. Example Conversation Flows

These examples show how the tools compose in the agent layer.

### Flow 1: Simple Trail Search
```
User: "Find me some good cycling trails near San Jose"

Agent calls: weekend.get_trails(location="San Jose, CA", activity_type="cycling")
Agent calls: weather.get_daily(location="San Jose, CA", when="today")

Agent: "I found 4 cycling trails near San Jose. Here are the top picks:
  1. Coyote Creek Trail - 12 mi, easy, ★ 4.6
  2. Los Gatos Creek Trail - 9 mi, easy, ★ 4.4
  3. Sierra Vista Loop - 18 mi, hard, ★ 4.8 (1,200 ft elevation)

  Weather looks great for it - 72°F, sunny, 0% rain chance."
```

### Flow 2: Full Weekend Planning (The "Friday Morning Routine")
```
Agent (proactive, Friday 9am):

Agent calls: calendar.find_free_time(start_date="2026-02-28", end_date="2026-03-01")
→ Saturday 8am-10pm free, Sunday 8am-6pm free

Agent calls: weekend.get_concerts(location="San Francisco, CA", artists=["Khruangbin", "Tycho"])
→ Tycho at The Fillmore, Saturday 8pm, tickets available

Agent calls: weekend.get_trails(location="San Francisco, CA", activity_type="hiking")
→ Lands End Trail, Marin Headlands Loop, Mt Tam Summit

Agent calls: weather.get_daily(location="San Francisco, CA", when="tomorrow")
→ 65°F, partly cloudy, 10% rain

Agent: "Your weekend is wide open! Here's what I found:

  🎵 Saturday Night: Tycho is playing at The Fillmore at 8pm - tickets still available.

  🥾 Saturday Morning: The weather looks perfect for a hike. Marin Headlands Loop
     (6.2 mi, moderate, ★ 4.7) would wrap up by noon, giving you the afternoon to relax.

  Sunday is free too - want me to draft a full plan, or just book the concert?"
```

### Flow 3: Multi-Day Trip Planning
```
User: "Plan a long weekend trip to Denver - I want hiking, live music, and good food"

Agent calls: weekend.get_trails(location="Denver, CO", activity_type="hiking")
Agent calls: weekend.get_concerts(location="Denver, CO", radius_miles=30)
Agent calls: weekend.generate_itinerary(destination="Denver, CO", duration_days=3,
              interests=["outdoors", "live music", "food"])
Agent calls: weather.get_daily(location="Denver, CO", when="tomorrow")

Agent: "Here's a 3-day Denver weekend plan:

  **Friday**: Fly in, check into hotel. Dinner at The Wolf's Tailor (★ 4.7, $$$$).
  Live music: Local band at Red Rocks (8pm, tickets $45).

  **Saturday**: Morning hike at Bear Creek Trail (5.4 mi, moderate, 1,100 ft gain).
  Afternoon: Explore RiNo Art District. Dinner at Hop Alley (★ 4.5, $$$).

  **Sunday**: Brunch at Snooze (★ 4.3, $$). Drive to Boulder for a light hike
  at Chautauqua Park (3.2 mi, easy). Head to airport.

  Weather: 58°F Saturday, partly cloudy. Perfect hiking weather.

  Want me to add these to your calendar?"
```

---

## 13. Graceful Degradation Matrix

What happens when things go wrong:

| Failure | Impact | Fallback Behavior |
|---------|--------|-------------------|
| Bandsintown API down | No concert data | Return empty events list with `error: "Concert data temporarily unavailable"`. Agent can still plan around trails + POIs. |
| Outdooractive API down | No trail data | Fall back to Google Places search for "hiking trails near {city}". Less rich data (no elevation/difficulty) but functional. |
| Google Places API down | No POI data for itinerary | Return error. Itinerary tool cannot function without POIs. Agent should inform user and offer trail/concert-only plan. |
| Google Directions API down | No transit estimates | Return POIs without transit data (`transit_estimates: null`). Agent can still present the itinerary without drive times. |
| Redis down | No caching | Fall back to in-memory cache (existing infrastructure handles this automatically). |
| Multiple APIs down | Severely degraded | Agent should be transparent: "I'm having trouble reaching some services. Here's what I could find..." and present partial results. |

---

## 14. Calendar Write-Back (Accepted Plans)

When the user says "book it" or "add to calendar", the agent should create calendar events using the existing `calendar.create_event` tool. This requires no new server work - it's agent orchestration.

Example write-back for an accepted weekend trip:

```python
# Agent creates these events after user approval:
calendar.create_event(
    title="🥾 Marin Headlands Hike",
    start="2026-03-01T08:00:00",
    end="2026-03-01T12:00:00",
    description="Marin Headlands Loop - 6.2 mi, moderate. Trailhead parking at..."
)
calendar.create_event(
    title="🎵 Tycho @ The Fillmore",
    start="2026-03-01T19:30:00",
    end="2026-03-01T23:00:00",
    description="Doors 7:30pm. Tickets: [link]"
)
```

The agent should ask for confirmation before creating events, and include relevant details (trailhead directions, ticket links, restaurant addresses) in event descriptions.

---

## 15. Open Questions

- [ ] **Outdooractive vs. Google Places for trails**: Outdooractive has richer trail data (elevation, difficulty, GPX routes) but requires an additional API key. Google Places is already integrated but returns generic "park" results. Start with Google Places and upgrade?
- [ ] **Spotify integration for concert matching**: Phase 3 mentions cross-referencing "Recently Played" with concert listings. This would require Spotify API OAuth. Worth the complexity for v1, or defer?
- [ ] **Proactive notifications**: Should the "Friday Morning Routine" run on a cron schedule and push notifications, or only trigger when the user asks? Cron requires infrastructure changes (task scheduler).
- [ ] **Multi-destination / road trips**: Should `generate_itinerary` support multi-city routes (e.g., "SF → Tahoe → Reno")? This significantly increases complexity. Could be a v2 feature.
- [ ] **Budget tracking**: Should tools return price estimates (concert tickets, gas cost, restaurant price levels)? Google Places returns `price_level` (1-4), Bandsintown sometimes returns ticket prices. Worth surfacing?
- [ ] **Shareable plans**: Should accepted itineraries be exportable (e.g., as a shareable link, PDF, or .ics file)? Nice-to-have for v2.

---

## 16. Success Criteria

**v1 (Tools working)**:
- [ ] Agent can answer "Find me hiking trails near Boulder" with real data
- [ ] Agent can answer "Are any of my favorite artists playing in Denver this month?"
- [ ] Agent can answer "Plan a weekend trip to Denver with hiking and live music"

**v2 (Orchestration working)**:
- [ ] Agent proactively suggests weekend plans based on calendar gaps
- [ ] Agent cross-references trail conditions, concerts, and weather in a single proposal
- [ ] User preferences influence recommendations without explicit prompting

---

## 17. File Manifest (Planned Changes)

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
    fixtures/weekend/           # NEW - Mock data directory
      mock_trails.json          # NEW - Sample trail data
      mock_concerts.json        # NEW - Sample concert data
      mock_pois.json            # NEW - Sample POI data

packages/agent/
  src/daily_ai_agent/
    agent/tools.py              # MODIFY - Add 3 new LangChain tools
    agent/orchestrator.py       # MODIFY - Register new tools
    agent/prompts/              # NEW - Weekend planner prompt templates (if needed)

packages/ui/
  app/components/
    weekend/                    # NEW - Weekend planner components (Phase 4)
      WeekendPlannerWidget.tsx  # NEW - Dashboard widget
      ItineraryView.tsx         # NEW - Day-by-day plan view
      TrailCard.tsx             # NEW - Trail recommendation card
      ConcertCard.tsx           # NEW - Concert event card

data/
  weekend_preferences.json      # NEW - User preferences (MCP Resource, Phase 3)

.env.example                    # MODIFY - Add BANDSINTOWN_APP_ID, OUTDOORACTIVE_API_KEY
```
