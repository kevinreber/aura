# Orchestrator Agent Design

Design notes for the next-generation planning capabilities of the Aura agent: a **weekend planner** and an on-demand **"nearby now"** mode, built on a shared substrate.

Status: Design / RFC. Not yet implemented.

---

## Problem

The current agent (`agent/orchestrator.py`) is a single-turn tool-calling LangChain agent. It works well for direct queries ("what's the weather", "show my calendar"), but two upcoming use cases stretch beyond that pattern:

1. **Weekend planning** — "Plan my weekend." Multi-day, scheduled, returns an itinerary with logistics and conflicts resolved.
2. **Nearby now** — "What's going on around me right now?" Real-time, location-bounded, on-demand, returns a ranked snapshot.

Both require decomposing a vague intent into parallel tool calls (events + weather + maps + calendar conflicts + venues), validating feasibility, and synthesizing a coherent answer.

## Decision: one orchestrator, two modes

Treat the two use cases as sibling **planners** inside the existing agent rather than separate services. They share ~80% of the substrate (location grounding, tool registry, user prefs, fan-out logic) and differ along three axes.

| | Weekend planner | Nearby now |
|---|---|---|
| **Horizon** | Multi-day, scheduled | Right now, on-demand |
| **Output** | Itinerary (ordered, with logistics, conflicts resolved) | Snapshot list (ranked, filterable) |
| **Latency budget** | 10–30s acceptable; user expects "planning" | Needs to feel instant or stream |
| **Trigger** | Cron / Friday push / "plan my weekend" | User taps button or asks |

**Tradeoff:** keeping them in one agent means a single deployment and shared improvements (better location grounding helps both), but requires clear intent routing so the chat agent picks the right planner. Split into a separate service only when the weekend planner needs background execution semantics (long-running, async, push notifications) that nearby-now doesn't.

### Why not a separate microservice?

- Process isolation isn't the bottleneck — planning quality is.
- Currently using GPT-4o-mini via OpenAI API, so there is no GPU workload that would justify Hugging Face Spaces or AMD GPU hosting.
- Stick with Railway (where the rest of the stack lives) until requirements diverge.

## Proposed code structure

```
packages/agent/src/daily_ai_agent/agent/
  orchestrator.py          # existing — entry point, intent routing
  context/
    location.py            # NEW — LocationContext (GPS, fallback to home/work)
    preferences.py         # NEW — UserPreferences (vegetarian, "no driving >30min", etc.)
    budget.py              # NEW — TimeBudget construction from calendar
  planners/
    weekend.py             # NEW — multi-day itinerary planner
    nearby.py              # NEW — snapshot planner
  validation/
    travel.py              # NEW — validate_itinerary + repair strategies
  synthesis/
    itinerary.py           # NEW — render Itinerary → user-facing format
    snapshot.py            # NEW — render ranked list → user-facing format
  tools.py                 # existing — get_commute already wired
```

The `tools.py` registry is shared. Planners differ in their prompt, response schema, and validation loop; the underlying tool calls are identical.

---

## Travel-aware validation (weekend planner)

The current agent has the *capability* to check travel time (`get_commute` in `packages/server/mcp_server/tools/mobility.py` returns Google Directions data with live traffic) but does not *automatically* incorporate it as a planning constraint. As a result, today the planner could happily suggest "Yosemite this Saturday" without checking that it's a 4-hour each-way drive.

### Gaps to close

- Planner does not automatically call mobility for proposed activities.
- No notion of a **time budget** (waking hours minus calendar conflicts) that travel must fit within.
- No round-trip math or "depart by X to be home by Y" reasoning.
- No traffic-time-of-day awareness — Friday 5pm SF→Yosemite is very different from Saturday 6am.
- `get_commute` defaults `departure_time` to `"now"`; needs to accept a future timestamp for itinerary validation.

### Data model

```python
@dataclass
class TimeBudget:
    date: date
    available_windows: list[tuple[datetime, datetime]]  # waking hours minus calendar conflicts
    home_base: Location

@dataclass
class CandidateActivity:
    name: str
    location: Location
    duration: timedelta
    earliest_start: datetime | None  # e.g., venue opens at 10am
    latest_end: datetime | None
    flexibility: Literal["fixed", "flexible"]  # ticketed vs drop-in

@dataclass
class Leg:
    from_loc: Location
    to_loc: Location
    depart_at: datetime
    duration: timedelta
    mode: Literal["driving", "transit", "walking"]
    traffic_status: str

@dataclass
class Itinerary:
    legs: list[Leg]
    activities: list[tuple[CandidateActivity, datetime]]  # activity + scheduled start
    total_travel_time: timedelta
    feasibility: Literal["fits", "tight", "infeasible"]
    issues: list[str]  # human-readable problems
```

### Validation loop

```python
async def validate_itinerary(
    candidates: list[CandidateActivity],
    budget: TimeBudget,
    mobility: MobilityClient,
) -> Itinerary:
    # 1. Cheap upfront filter — haversine, no API calls
    pruned = [
        c for c in candidates
        if rough_round_trip_hours(budget.home_base, c.location) <= budget.total_hours
    ]

    # 2. Order by geography (greedy nearest-neighbor or simple cluster)
    sequence = order_by_proximity(budget.home_base, pruned)

    # 3. Walk the sequence, calling mobility for real travel times
    cursor = budget.available_windows[0][0]
    cursor_loc = budget.home_base
    legs, scheduled, issues = [], [], []

    for activity in sequence:
        leg = await mobility.get_commute(
            origin=cursor_loc,
            destination=activity.location,
            departure_time=cursor,  # important: time-of-day affects traffic
        )
        arrival = cursor + leg.duration

        # Honor venue hours
        if activity.earliest_start and arrival < activity.earliest_start:
            arrival = activity.earliest_start  # we'd wait

        end = arrival + activity.duration
        if not fits_in_window(arrival, end, budget.available_windows):
            issues.append(f"{activity.name}: would end at {end}, past available window")
            continue

        legs.append(leg)
        scheduled.append((activity, arrival))
        cursor, cursor_loc = end, activity.location

    # 4. Close the loop — return-home leg
    return_leg = await mobility.get_commute(cursor_loc, budget.home_base, departure_time=cursor)
    legs.append(return_leg)

    # 5. Classify
    feasibility = classify(scheduled, issues, return_leg, budget)
    return Itinerary(legs, scheduled, sum_durations(legs), feasibility, issues)
```

### Repair strategies

When the planner returns `infeasible` or `tight`, try in order before giving up:

1. **Drop lowest-priority activity** — if Yosemite + 2 SF activities don't fit, drop the SF ones.
2. **Suggest overnight** — if round-trip travel > 6h, propose a multi-day itinerary with a lodging tool call.
3. **Substitute closer alternative** — "you wanted nature; here's Muir Woods instead."
4. **Shift to different day** — try Sunday, or split across the weekend.
5. **Surface the tradeoff** — return infeasible with a clear "this is 10h of driving for 4h on-site, want to make it overnight?"

### Test prompt

The Yosemite-from-SF case is a strong canary for the planner. It forces one of:

- (a) reject as infeasible for a day trip,
- (b) propose an overnight with lodging,
- (c) suggest closer alternatives ("Muir Woods or Mt. Tam give you a similar vibe with 1hr drive").

---

## Nearby-now mode

Same substrate, different planner shape:

- Pulls `LocationContext` (GPS from UI, fallback to home/work).
- Fans out to events / Yelp / Eventbrite / Ticketmaster / weather / transit in parallel.
- Ranks results by distance, time relevance, and user preferences.
- **Streams partial results** to UI so it doesn't feel like a 20s black box.
- Cached at the `geohash + time-bucket` level for repeated queries.
- Tolerates partial failure: one API down should not fail the whole answer.

---

## Considerations before building

1. **Validation cost** — every candidate × every reorder = many Google Directions calls. The existing 15-min route cache helps; also cap candidates (e.g., top-8 after upfront filter) and prefer batching where possible.
2. **Departure-time sensitivity** — Directions returns very different durations for `Friday 5pm` vs `Saturday 7am`. Ensure `departure_time` is *the actual planned departure*, not `"now"`, when validating future itineraries. Requires extending `get_commute`.
3. **Intent routing** — orchestrator entry point needs to distinguish "plan my weekend" (weekend planner) from "what's around me" (nearby) from "what's the weather" (current single-turn agent). Likely a small classifier prompt up front.
4. **Streaming UX** — both planners benefit from streaming progress updates ("checking events… checking traffic to Yosemite… 4h drive each way, suggesting overnight instead"). Plan the UI contract early.

## Suggested build order

1. `context/budget.py` + `context/location.py` — pure data, no new APIs, unlocks everything else.
2. Upfront haversine filter in `validation/travel.py` — no API calls, immediate value.
3. Extend `get_commute` to accept future `departure_time`.
4. Full `validate_itinerary` loop with one repair strategy (drop-lowest-priority).
5. `planners/weekend.py` wired end-to-end against a fixed candidate list.
6. Add event-discovery tools, then real candidate generation.
7. `planners/nearby.py` reusing the substrate.
8. Streaming progress to UI.

## Open questions

- Where does the user-preferences store live? (Postgres? Redis? Flat file per user?)
- How do we handle multi-user prefs once the app is not single-user?
- Background execution model for weekend planner — sync request/response, or job + push notification when ready?
- Do we want a feedback loop (user thumbs-down an activity → planner learns)?

---

## Related docs

- `AI_AGENT_STRATEGY.md` — current agent architecture
- `CLAUDE.md` — agent package conventions
- `../server/COMMUTE_INTELLIGENCE.md` — mobility tool capabilities
