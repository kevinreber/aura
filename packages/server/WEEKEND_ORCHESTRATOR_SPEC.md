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
- [ ] **Spotify integration for concert matching**: Phase 3 mentions cross-referencing "Recently Played" with concert listings. This would require Spotify API OAuth. See Section 19 for the full design proposal — recommendation is to ship JSON-based v1, then add Spotify in v1.5.
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

---

## 18. Follow-Up Actions (Pre-Development Checklist)

These are the manual steps you need to complete before development can begin.

### API Keys & Accounts to Set Up

- [ ] **Bandsintown App ID** (Required for concerts)
  1. Go to https://www.bandsintown.com/for-artists
  2. Sign up for a developer/artist account
  3. Navigate to API settings and create an App ID
  4. Add `BANDSINTOWN_APP_ID=your_app_id` to your `.env`

- [ ] **Outdooractive API Key** (Optional - only if using as primary trail provider)
  1. Go to https://developers.outdooractive.com/
  2. Apply for the developer program (may take a few days for approval)
  3. Create a project and generate an API key
  4. Add `OUTDOORACTIVE_API_KEY=your_key` to your `.env`
  5. **Note**: If skipping this, Google Places will be used as the trail provider — it's already configured via your `GOOGLE_MAPS_API_KEY`

- [ ] **Google Maps Places API** (Likely already enabled)
  1. Go to https://console.cloud.google.com/apis/library
  2. Verify that **Places API** and **Places API (New)** are enabled on the same project as your existing `GOOGLE_MAPS_API_KEY`
  3. Your existing key should work — no new key needed, but Places may not be enabled yet
  4. Check your billing dashboard for the $200/month free credit status

### Google Maps API Enablement Check

Your existing `GOOGLE_MAPS_API_KEY` is used for Directions (mobility tool). The itinerary tool additionally needs:

| API | Current Status | Action |
|-----|---------------|--------|
| Directions API | Already enabled (used by mobility tool) | No action needed |
| Places API | Likely NOT enabled | Enable in Google Cloud Console |
| Places API (New) | Likely NOT enabled | Enable for newer Nearby Search endpoints |
| Geocoding API | Already enabled (used by weather tool indirectly) | No action needed |

To check: `curl "https://maps.googleapis.com/maps/api/place/nearbysearch/json?location=37.7749,-122.4194&radius=5000&type=park&key=$GOOGLE_MAPS_API_KEY"` — if you get a `REQUEST_DENIED` error, Places API needs to be enabled.

### Environment File Updates

Add these to your `.env` (and `.env.example` will be updated during implementation):

```bash
# Weekend Orchestrator (add to MCP Server section)
BANDSINTOWN_APP_ID=your_bandsintown_app_id
OUTDOORACTIVE_API_KEY=your_outdooractive_key  # Optional, falls back to Google Places
```

### Render / Production Deployment

- [ ] Add `BANDSINTOWN_APP_ID` to Render environment variables for `aura-server-sxxd` service
- [ ] Add `OUTDOORACTIVE_API_KEY` to Render environment variables (if using)
- [ ] Verify Google Places API is enabled on the production GCP project (may be a different project than local dev)

### Decision Points to Resolve

Before starting Phase 1, decide on these open questions:

- [ ] **Trail provider for v1**: Start with Google Places (zero setup) or Outdooractive (richer data, requires approval)? Recommendation: Start with Google Places, upgrade later.
- [ ] **Spotify integration**: Defer to v1.5 or set up OAuth now? See Section 19 for full design. If pursuing now:
  1. Go to https://developer.spotify.com/dashboard
  2. Create an app, get Client ID + Secret
  3. Add `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` to `.env`
  4. Implement Authorization Code OAuth flow with refresh token storage
- [ ] **Proactive vs. on-demand**: Decide if the "Friday Morning Routine" should be cron-triggered or only user-initiated for v1

### User Preferences File

Create `data/weekend_preferences.json` with your personal defaults:

```json
{
  "favorite_artists": ["Artist1", "Artist2", "Artist3"],
  "activity_preferences": ["hiking", "cycling"],
  "max_drive_hours": 4,
  "budget_level": "moderate",
  "home_base": "San Francisco, CA"
}
```

This file is read by the MCP server as a Resource (Phase 3) and should **not** be committed to git (add to `.gitignore`).

---

## 19. Future Enhancement: Spotify as Source of Truth for Artist Interests

**Status**: Proposed for v1.5 (post-Phase 1, pre-cron)
**Tracked as**: Open Question in Section 15

### Motivation

The Phase 3 design stores favorite artists in a static JSON file (`weekend_preferences.json`). This is fast to ship, but it has a maintenance problem: the user has to remember to add artists they care about. New obsessions don't get caught until the user manually edits the file. This makes the file a **lagging indicator** of the user's actual taste.

Spotify already has the source-of-truth (SOT) for what the user listens to. Querying Spotify directly eliminates the manual maintenance step and makes the agent's concert recommendations track the user's evolving taste automatically.

### Relevant Spotify Web API Endpoints

| Endpoint | Use Case | Signal Strength |
|----------|----------|-----------------|
| `GET /me/top/artists?time_range=medium_term&limit=50` | Top 50 artists over last ~6 months. Updates daily. | High — broad candidate pool |
| `GET /me/top/artists?time_range=short_term` | Last ~4 weeks. Captures current obsessions. | High — recency-weighted |
| `GET /me/following?type=artist` | Artists the user explicitly follows. | **Highest** — intentional "I'd see them live" signal |
| `GET /me/tracks` (saved tracks) | User's saved library. | Medium — implicit love |
| `GET /artists/{id}/related-artists` | Similar-artist expansion for discovery. | Medium — discovery layer |
| `GET /recommendations?seed_artists=...` | Spotify's algorithm suggests similar artists/tracks. | Medium — discovery layer |

### Implicit vs. Explicit Signal Tradeoff

The key design caveat: **Spotify reveals what you listen to, not what you'd pay to see live.** Listening habits and concert intent diverge:

- Heavy listeners of ambient/lo-fi/study music likely won't buy concert tickets to those artists.
- Conversely, a user might want to see a band they rarely stream (e.g., a one-off festival headliner).
- `/me/following` is a stronger live-intent signal than `/me/top/artists`, because following is intentional.

This means Spotify should **augment, not replace**, explicit user preferences.

### Recommended Hybrid Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Artist Interest Resolution                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  /me/following (Spotify)        ← Highest confidence            │
│         +                                                        │
│  /me/top/artists medium_term    ← Broader candidate pool        │
│         +                                                        │
│  weekend_preferences.json:                                       │
│    - pinned_artists: []         ← Explicit always-alert list    │
│    - excluded_artists: []       ← Never recommend these         │
│         ↓                                                        │
│  De-duplicated, ranked artist list                               │
│         ↓                                                        │
│  Bandsintown lookup per artist                                   │
└─────────────────────────────────────────────────────────────────┘
```

The JSON file stops being the SOT and becomes an **override layer** — pins and excludes only.

### Proposed Tool: `weekend.get_user_artists`

A new server tool that returns the resolved artist list:

```
Input:
  source_priority: list[str]    # ["following", "top_medium", "top_short", "pinned"]
  limit: int                    # Max artists to return (default: 30)
  exclude_genres: list[str]     # Genre filter (optional)

Output:
  artists: list[Artist]
    - name: str
    - spotify_id: str
    - source: str               # "following" | "top_artists" | "pinned"
    - rank: int                 # Higher = stronger signal
    - genres: list[str]
  source: str                   # "spotify" | "json_fallback"
  cached: bool
```

The agent calls this **before** `weekend.get_concerts`, then passes the artist names through.

### OAuth Implementation Cost

Real and non-trivial:

- **Spotify Authorization Code Flow** with `user-top-read`, `user-follow-read`, `user-library-read` scopes
- **Refresh token storage** — needs encryption at rest (Fernet or similar)
- **Initial setup**: One-time browser-based authorization, redirect URI handling
- **Operational complexity**: Token refresh logic, handling expired/revoked tokens
- **Estimated effort**: 1–2 hours of implementation + testing

For a personal single-user tool, OAuth is one-time setup, so this is more friction than complexity. For a multi-tenant version (future), token-per-user storage becomes a real concern.

### Phased Recommendation

**v1 (Phase 1–3, current spec)**: Ship JSON-only. Zero OAuth setup keeps the critical path short. Validates the trail/concert/itinerary tools end-to-end.

**v1.5 (this enhancement)**: Add `weekend.get_user_artists` tool with Spotify integration. JSON file demoted to override layer. Agent prefers Spotify when configured, falls back to JSON when not.

**v2 (cron-driven proactive)**: Combined with the "Friday Morning Routine" cron, the agent automatically catches new artists the user has started listening to and surfaces upcoming shows without any manual prompt.

### Why Not Build It Now

1. **OAuth is on the critical path** — adding it to v1 delays the testable slice by 1–2 hours minimum, plus debugging.
2. **Mock data + JSON file is enough** to validate the agent flow end-to-end, which is what Phase 1 needs to prove.
3. **The interface stays clean** — adding `weekend.get_user_artists` later doesn't break `weekend.get_concerts`. They're decoupled.

### Why Not Defer Past v1.5

1. **The maintenance problem is real** — JSON files for taste data go stale within weeks.
2. **Discovery is a real value-add** — `/artists/{id}/related-artists` lets the agent surface "Tycho is touring, and you might also like ODESZA who's playing nearby" without any manual curation.
3. **OAuth complexity is one-time** — once it works, it works. Doesn't need ongoing maintenance.

### Implementation Checklist (when v1.5 begins)

- [ ] Register Spotify app at https://developer.spotify.com/dashboard
- [ ] Add `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SPOTIFY_REDIRECT_URI` to `.env`
- [ ] Implement OAuth flow in `mcp_server/clients/spotify.py`
- [ ] Add encrypted token storage (Fernet + key in env)
- [ ] Create `mcp_server/tools/weekend.py::get_user_artists()` method
- [ ] Update `weekend_preferences.json` schema: rename `favorite_artists` → `pinned_artists`, add `excluded_artists`
- [ ] Update agent's "Friday Morning Routine" prompt to call `get_user_artists` before `get_concerts`
- [ ] Cache top_artists/following responses for 24 hours (data updates daily anyway)

### Open Questions for v1.5

- [ ] Should the agent weight `/me/following` artists higher than `/me/top/artists` automatically, or treat them equally?
- [ ] Should `short_term` (4 weeks) override `medium_term` for ranking, to capture current obsessions faster?
- [ ] Genre-based fallback: if no top artists are touring, should the agent recommend any indie/electronic show in town based on the user's genre profile?
- [ ] Multi-source dedup: when an artist appears in both `following` and `top_artists`, which source wins for the `source` field in the output?

---

## 20. User-Toggleable Categories (Preferences Architecture)

**Status**: Proposed for Phase 2/4 (agent reads prefs in Phase 2, UI exposes toggles in Phase 4)

### Motivation

The Weekend Orchestrator's value to a user grows with the number of category-specific tools (`get_trails`, `get_concerts`, `generate_itinerary`, and future additions like food tours, festivals, sports, comedy, art shows). Not every user wants every category — a non-music-listener doesn't need concert alerts, a non-hiker doesn't need trail recommendations.

A user-facing toggle list lets each user pick which categories Aura considers when planning their weekend. Toggles cut noise, save API calls (the agent skips disabled categories entirely), and make Aura feel personalized rather than one-size-fits-all.

### Architecture by Layer

This is a **preferences architecture**, not a server-side feature. The MCP server stays general-purpose so it remains usable from external MCP clients (Claude Desktop, Cursor) where Aura-specific prefs aren't relevant.

| Layer | Responsibility |
|-------|----------------|
| **Server** (`packages/server`) | Stays category-agnostic — exposes all tools regardless of user prefs. Optionally exposes a `/weekend/categories` endpoint that returns the catalog of available categories so the UI doesn't have to hardcode them. |
| **Agent** (`packages/agent`) | Reads `enabled_categories` from `weekend_preferences.json` before tool selection. Skips disabled categories at the orchestration layer. The "Friday Morning Routine" prompt is updated to respect toggles. |
| **UI** (`packages/ui`) | Settings panel with checkboxes per category. Reads category catalog from `/weekend/categories`, reads/writes user prefs to disk via the agent or a dedicated prefs endpoint. |

### Schema Update: `weekend_preferences.json`

Extends the schema introduced in Section 3 (Phase 3) by adding `enabled_categories` and renaming/clarifying related fields:

```json
{
  "enabled_categories": ["trails", "concerts", "itinerary"],
  "pinned_artists": ["Khruangbin", "Tycho"],
  "excluded_artists": [],
  "activity_preferences": ["hiking", "cycling"],
  "max_drive_hours": 4,
  "budget_level": "moderate",
  "home_base": "San Francisco, CA"
}
```

**Schema notes:**

- `enabled_categories` is the new toggle field. Default for a fresh install: all three v1 categories enabled.
- `pinned_artists` replaces `favorite_artists` (clearer — these are explicit overrides, not a maintained "favorites list"). Aligns with Section 19's hybrid Spotify approach.
- `excluded_artists` is also new, paired with `pinned_artists` as the override layer.
- File still lives at `data/weekend_preferences.json` and remains gitignored.

### `/weekend/categories` Discovery Endpoint

Optional but recommended — makes adding new categories a backend-only change:

```
GET /weekend/categories

Response:
{
  "categories": [
    {
      "id": "trails",
      "label": "Trails & Outdoors",
      "description": "Hiking, cycling, and outdoor activity recommendations",
      "default_enabled": true,
      "tools": ["weekend.get_trails"]
    },
    {
      "id": "concerts",
      "label": "Live Music",
      "description": "Concerts and live music events for your favorite artists",
      "default_enabled": true,
      "tools": ["weekend.get_concerts"]
    },
    {
      "id": "itinerary",
      "label": "Multi-day Trips",
      "description": "Full weekend trip planning with points of interest",
      "default_enabled": true,
      "tools": ["weekend.generate_itinerary"]
    }
  ]
}
```

When you add `weekend.get_food_tours` or `weekend.get_sports_events` later, you add an entry here and the UI picks it up without any frontend redeploy.

### Agent Behavior

Before tool selection, the agent loads `weekend_preferences.json` and intersects `enabled_categories` with the categories registered in `/weekend/categories`. Disabled categories are removed from the candidate tool list — the LLM never even sees them, so it can't accidentally call them.

For the "Friday Morning Routine" specifically, the prompt should:

1. Load enabled categories
2. Loop through them in priority order (trails → concerts → itinerary)
3. Call only the tools mapped to enabled categories
4. Synthesize a recommendation using only the data returned

### Future Categories (Backlog)

These are illustrative — not part of v1. They're listed here so the schema accommodates them gracefully:

| Category ID | Tool(s) | Notes |
|---|---|---|
| `festivals` | `weekend.get_festivals` | Music festivals, food fests — separate from individual concerts |
| `food_tours` | `weekend.get_food_tours` | Curated multi-stop food experiences, brewery tours, cocktail crawls |
| `sports` | `weekend.get_sports_events` | Local games, climbing comps, races |
| `art` | `weekend.get_art_events` | Gallery openings, exhibits, artist talks |
| `comedy` | `weekend.get_comedy` | Stand-up shows, improv, comedy clubs |
| `theater` | `weekend.get_theater` | Plays, musicals, dance performances |

Each future category gets a new tool + a new entry in `/weekend/categories`. No schema migrations.

### Phased Recommendation

**v1 (Phase 1, current)**: No code change needed. Document the schema in this section so Phase 2 wires against the right shape.

**v1.5 (Phase 2)**: Agent reads `weekend_preferences.json`, including `enabled_categories`, before tool selection. JSON file edited by hand for testing — no UI yet.

**v2 (Phase 4)**: UI surfaces the toggle list. `/weekend/categories` endpoint added to server. Settings page reads/writes user prefs.

### Open Questions

- [ ] **Where does the prefs file live in the deployed multi-user version?** Local file works for single-user dev; production needs per-user storage (database row, encrypted blob, or per-user file).
- [ ] **Is "category" the right granularity?** Should users toggle individual *tools* (`get_trails` on, `get_concerts` off) or higher-level categories (`outdoors` covering trails + parks + bike rides)? Current design says category, but a single category can map to multiple tools.
- [ ] **Should disabled categories still surface in proactive suggestions?** ("You have concerts disabled, but Tycho is at the Fillmore Saturday — want me to enable it for this weekend?") This is a UX question, not architectural.
- [ ] **Default-enabled vs. opt-in for new categories.** When a future category like `festivals` is added, should existing users have it default to on (discoverable) or off (no surprise behavior changes)? Recommend opt-in with a one-time onboarding prompt.
