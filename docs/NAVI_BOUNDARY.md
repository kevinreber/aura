# Aura ↔ Navi Boundary

**Status:** Draft · **Date:** 2026-07-04

This document defines the conceptual and architectural boundary between **Aura**
and **Navi**, and the rules we follow to keep them separable.

## Mental model

- **Aura** is the *app* and the *primary conversational agent* — the thing the
  user talks to. It owns the chat UI, auth, the general assistant persona, and
  the everyday tools (weather, calendar, todos, commute, financial).
- **Navi** is the *planning orchestrator* — a specialized sub-agent that turns a
  fuzzy intent ("plan my Saturday", "a weekend near me") into a concrete plan by
  scouting trails, finding concerts, and stitching multi-day itineraries.
  Formerly called the "Weekend Planner" / "Weekend Orchestrator".

**The one-line split:** **Aura is the *operator*, Navi is the *composer*.**
Aura reads and acts on things that *already exist* in your world (stocks,
calendar, todos, commute, weather) — reactive, present-tense, transactional; it
is the system of *record + action*. Navi *generates net-new proposals* from your
intent + taste (RAG) + world data — proactive, future-tense, generative; it is a
system of *suggestion*. **Aura tells you what *is*; Navi suggests what *could
be*.** Both are real agents (LLM + tools + reasoning loop); the difference is
role, not kind.

> **Naming:** "Navi" is after Link's guide companion in *The Legend of Zelda*,
> and echoes *navigate*. Reads as "Aura Navi" or just "Navi".

**The core principle:** Aura *calls* Navi; Navi is not baked into Aura's core.
We keep the seam clean so that Navi can one day be **extracted from Aura and run
as its own standalone product** with minimal untangling. Every design choice in
the planning feature should preserve that optionality.

```
┌──────────────────────────────┐        ┌──────────────────────────────┐
│              AURA            │  calls │             NAVI             │
│  (app + primary chat agent)  │──────▶ │   (planning orchestrator)    │
│                              │  via   │                              │
│  • chat UI + auth boundary   │ narrow │  • plan trails/concerts/     │
│  • general assistant persona │ contract│   itineraries               │
│  • everyday tools:           │        │  • its own prefs + prompt    │
│    weather, calendar, todos, │◀────── │  • depends on capabilities,  │
│    commute, financial        │ capes  │    not on Aura internals     │
└──────────────────────────────┘        └──────────────────────────────┘
        Aura owns the user.                Navi owns the plan.
```

## Where the line falls (responsibilities)

| Concern | Owner | Notes |
|---|---|---|
| Chat surface, auth, session, general persona | **Aura** | Navi never re-implements auth. |
| Everyday tools (weather, calendar, todos, commute, financial) | **Aura** | Navi *consumes* some of these as capabilities (see below). |
| Trail / concert / POI discovery + itinerary synthesis | **Navi** | Navi's core value. |
| Planning preferences (categories, artists, drive hours, budget, home base) | **Navi** | Navi owns its own prefs schema + storage. |
| Planning-specific prompt/routing logic | **Navi** | Should not live in Aura's shared system prompt. |
| Writing a finished plan to calendar / todos | **Aura capability** | Navi asks; Aura performs the write via a capability interface. |

## The schedule overlap — "Navi proposes, Aura disposes"

Calendar is the one place Aura and Navi genuinely overlap. We resolve it by
**ownership + direction of flow**, not by splitting the calendar in two:

- **Aura owns the calendar** (read *and* write). It is the source of truth for
  the user's real commitments.
- **Navi only *reads* the calendar as a constraint** ("free Saturday, busy
  Sunday afternoon") to shape a plan. **Navi never writes to the calendar
  directly.**
- When a plan is accepted, **Navi hands it back and Aura commits it** (the
  write-back).

The mantra: **Navi proposes, Aura disposes.** Calendar *reads* flow **into** Navi
as context; calendar *writes* flow back **through** Aura. This dissolves the
"who owns the schedule" question — Navi never mutates real state. Concretely,
Navi depends on a read-only `CalendarReader` (constraint) and hands accepted
plans to a `CalendarWriter` that **Aura** implements (see capabilities below).
The same rule generalizes to todos/commute: Navi may *read* a few as planning
constraints, but owns and writes none of them.

**Who conducts:** the user always talks to Aura. When a request needs both
("plan a hike Saturday *and* put it on my calendar"), **Aura conducts** — it
calls Navi for the plan, then performs the writes itself. Peer capabilities,
hierarchical control: Aura owns the user and the actions; Navi owns the plan.

## Capabilities Navi depends on (the dependency contract)

Navi needs a few things Aura already provides. To stay extractable, Navi should
depend on **capability interfaces**, never on Aura-owned modules directly:

- `WeatherProvider` — "is Saturday good for outdoors?" (today: Aura's weather tool)
- `Geocoder` / `TravelTime` — trail distances, drive times (today: commute/maps)
- `CalendarReader` — read-only free/busy constraint (today: Aura's calendar)
- `CalendarWriter` / `TodoWriter` — write-back of a finished plan (today: Aura's calendar/todo tools)
- `PlacesProvider` / `EventsProvider` — trails/POIs (Google Places) and concerts (Ticketmaster)

Navi *owns* (not delegated to Aura) two of its own domain services:

- `ReferenceIngest` + `ReferenceStore` — user-provided references (see below).
- `AvailabilityService` — days off / free days, source-agnostic (see below).

When Navi runs *inside* Aura, Aura injects implementations backed by its own MCP
tools. When Navi is extracted, those same interfaces are satisfied by Navi's own
providers (or Navi calls Aura's MCP server as an external client). Either way,
Navi's code does not change.

## Standalone PoC — Navi as its own RAG agent

Navi can grow into its own repo/service (its own AI agent) that Aura still calls.
Full rationale in the vault decision `navi-002`; the load-bearing pieces:

### User-provided references (RAG) — schema-on-ingest

Users drop a link or screenshot (e.g. an Instagram itinerary); Navi keeps it as
durable, searchable taste/reference knowledge — or plans from it immediately.

- **Never force the user to structure input; impose structure at ingest.**
  Schema-on-ingest, not schema-on-input — an LLM normalizes messy input.
- **One canonical `Reference`** with two layers:
  - *Structured metadata* (`kind`, `title`, `locations[]`+geo, `activities[]`,
    `season_months`, `duration`, `price_tier`, `tags[]`, `source`) → **SQL filtering**.
  - *LLM-written `summary`* → **embedded** for semantic search (keep `body_raw`
    for grounding + re-extraction). Embed the clean summary, not raw captions
    (Anthropic Contextual Retrieval pattern).
- **Controlled vocab** for high-value facets + **open `tags[]`** for the long tail.
- **Ingestion = a connector registry** (`SourceConnector.can_handle/extract`):
  web (defuddle), YouTube (transcript), and **Instagram/TikTok via user-shared
  screenshot → Claude vision OCR** (do *not* scrape — ToS + brittle).
  Endpoint: `POST /references?mode=store|plan`.

### Availability (days off) — source-agnostic

Navi owns an `Availability` model (free / off / blackout / preferred-travel),
**decoupled from any work calendar** (work calendars are often unshareable).
Fed by optional sources: manual entry, `.ics` upload, personal-calendar mirror
(Aura already reads it), and a public-holiday API. **Store only free/off/blackout
+ labels, never work event contents.**

### Storage / RAG

**Supabase Postgres + `pgvector`** — one store for structured filters *and*
semantic search. Start relational with keyword/BM25 (already built for the
vault); **enable embeddings only when keyword recall visibly fails.** Vectors are
an optimization, not a prerequisite — the PoC is not gated on them. Hybrid
retrieval: metadata pre-filter → semantic rank.

## Current state (coupling to unwind)

As of 2026-07-04, Navi's pieces live *inside* Aura's packages and share Aura's
runtime. This is fine for now, but it's the coupling a future extraction pays down:

- **Server** — `packages/server/mcp_server/tools/weekend.py`,
  `schemas/weekend.py`; MCP tools `weekend_get_trails` / `weekend_get_concerts` /
  `weekend_generate_itinerary` are registered in the *same* MCP server as
  weather/calendar/etc., and exposed as REST in `app.py`.
- **Agent** — LangChain wrappers `TrailScoutTool` / `ConcertAlertTool` /
  `ItineraryTool` in `agent/tools.py` sit in the *same* tool list as every other
  tool. `agent/orchestrator.py` holds Navi-specific routing (WEEKEND PLANNING,
  trail-distance follow-ups, calendar write-back) inline in the **shared** system
  prompt, plus preference-gating (`_CATEGORY_TO_TOOL_NAMES`,
  `_filter_tools_by_preferences`). Prefs load via `services/preferences.py`.
- **UI** — Navi surfaces as the "Weekend" tab in
  `app/components/aura/AuraShell.tsx` (`WEEKEND_CATS` in `aura/types.ts`),
  riding Aura's shared chat + the `/api/v1/preferences` proxy.

Coupling that specifically blocks extraction today:
1. Navi's tools are indistinguishable from Aura's in one flat MCP server + tool list.
2. Navi's prompt/routing logic is interleaved into Aura's single shared prompt.
3. Navi reaches Aura's calendar/weather/commute tools *directly*, not through interfaces.
4. Navi has no independent surface — it's a tab inside `AuraShell`.

## Target boundary (what "clean" looks like)

The goal is a single, narrow contract with everything Navi-specific behind it.

1. **Namespace Navi.** Collect Navi's code under dedicated module paths — e.g.
   `packages/server/mcp_server/navi/…` and `packages/agent/.../navi/…` — so the
   entire feature is greppable and movable as a unit. (Tool wire-names like
   `weekend_get_trails` can stay for back-compat; they're not user-visible.)
2. **One entry point.** Aura invokes Navi through a single high-level call
   (e.g. `navi.plan(intent, context)` or one `navi_plan` MCP tool) rather than by
   hand-wiring three low-level tools + prompt fragments into its own loop. Navi's
   internal tool orchestration becomes Navi's business.
3. **Navi owns its prompt + prefs.** Planning routing lives in a Navi-owned
   prompt module; Navi owns its preferences schema and storage. Aura's shared
   prompt shrinks to "for planning, delegate to Navi."
4. **Depend on capabilities, not modules.** Navi's calendar/weather/commute
   access goes through the capability interfaces above, injected by Aura.
5. **Separable surface.** Navi's UI (the "Weekend"/Navi tab) is a self-contained
   component fed by a Navi-scoped proxy route, so it can move to its own app shell.

**Extraction litmus test:** could you `git mv` the `navi/` folders into a new repo,
provide implementations of the capability interfaces, and have it run — without
editing Aura's core? The closer we are to "yes", the cleaner the boundary.

## Rules of thumb (apply on every change)

- ✅ Put new planning logic under a Navi namespace, behind the Navi entry point.
- ✅ When Navi needs a calendar/weather/commute action, route it through a
  capability interface — don't import an Aura tool directly.
- ✅ Keep Navi-specific prompt text out of Aura's shared system prompt.
- ❌ Don't let Aura's core read Navi's internal state, or vice-versa, except
  through the defined contract.
- ❌ Don't add a hard import from Aura core → Navi internals (or the reverse).

## Migration path (incremental, non-breaking)

None of this needs to happen at once. Rough order, each step shippable on its own:

1. **Namespace** the existing weekend files under `navi/` (mechanical move; wire-names unchanged).
2. **Extract** Navi's prompt/routing + preference-gating out of `orchestrator.py` into a Navi prompt module.
3. **Introduce capability interfaces** for calendar/weather/commute/places/events; inject Aura's implementations.
4. **Collapse** the three low-level tools behind one `navi.plan(...)` entry point (keep the low-level tools internal).
5. **Isolate the UI** surface behind a Navi-scoped route/proxy.

## Related

- `PLANNER_RESEARCH.md` — the planner-agent vision (Builds 1–3) Navi grows toward.
- `packages/server/WEEKEND_ORCHESTRATOR_SPEC.md` — the original feature spec.
- `packages/agent/ORCHESTRATOR_DESIGN.md` — agent-layer orchestration design.
- Vault decisions: `navi-001` (naming + boundary + operator/composer split),
  `navi-002` (standalone RAG-agent PoC: ingestion, availability, storage).
