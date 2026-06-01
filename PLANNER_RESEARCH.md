# Personal Planner Agent — Exploration Notes

Worktree: `worktree-planner-agent-research`
Date: 2026-05-30
Status: Exploration / learning project, not high priority

## What this is

A personal exploration to:
1. **Build a planner that actually reduces the planning tax** for Kevin's real use cases.
2. **Learn agent-building patterns** along the way — both the *agent-loop architecture* side and the *personalization* side.

Not a product. Not a B2B play. Reference other services only for *brainstorming inspiration*, not competitive analysis.

## Two test cases (different shapes, same agent)

| | Weekend mode | Spain mode (long stint) |
|---|---|---|
| Horizon | 1–2 days, recurring | 12 weeks, evolving |
| Cadence | Friday-morning push | Weekly draft with checkpoints |
| Decision granularity | A handful of blocks | Hundreds of micro-decisions |
| What "good" feels like | "I took advantage of Saturday" | "I lived like a local, not a tourist" |
| Failure mode | Generic TripAdvisor slop | Either above + planner ran out of ideas in week 3 |

The shared thing: **a real model of Kevin**. Without that, both modes produce slop.

## The model-of-Kevin: brain-vault as personality input

Confirmed: agent can read the vault.

Why this is the right input:
- `Projects/kevin-reber.md` already has interests, hobbies, fitness, music, social profiles.
- `Activity/` and `Reflections/` are an evolving record of what Kevin actually does and how he felt about it.
- `Backlog/ideas.md` shows aspirational stuff.
- It's *self-maintaining* — Kevin already writes to the vault, so personality stays fresh for free.

Augment with a thin **trip-specific intent** layer for each plan ("for Spain, bias toward slow travel and food, less hiking than usual; for this weekend, low energy, no driving over an hour"). Vault = stable personality. Intent = the moment's flavor.

Future: a feedback channel that updates the vault (or a sidecar) when the user reacts to a plan. Out of scope for v0.

## Agent-pattern curriculum

Three builds that each exercise a new agent pattern. Each produces something useful on its own — no need to commit to all three up front.

### Build 1 — Vault-aware Saturday planner *(starting point)*

Smallest thing that exercises both learning goals.

**Agent patterns introduced:**
- **ReAct loop** (think → tool → observe → think) — already there in LangChain.
- **Reflection / self-critique** — agent generates a plan, critiques it ("does this match Kevin's stated low-energy preference? does the travel time fit?"), revises before returning.
- **Vault-as-context** — agent reads a curated subset of the vault on each invocation.

**What it does:**
- Input: "plan my Saturday" + optional intent flavor.
- Reads vault personality snippets (preferences, recent activity).
- Calls existing weekend tools (trails, concerts, places, weather, calendar).
- Drafts a plan, runs one self-critique pass, returns a structured itinerary with blocks + drive times.

**Why this first:** small scope, all dependencies exist, exercises personality + a non-trivial loop in one go. Ships in a weekend.

### Build 2 — Plan-then-execute multi-day

Add real planning structure beyond chat.

**New agent patterns:**
- **Plan-then-execute** — agent first writes a high-level plan ("Sat morning: outdoor; Sat afternoon: food/culture; Sun: low-key"), then fans out each block to tool calls. Cleaner separation than ReAct alone.
- **Validation + repair loop** — the haversine + travel-time checks from `ORCHESTRATOR_DESIGN.md`. Drop, substitute, or shift if blocks don't fit.
- **Structured output** — Pydantic itinerary schema instead of prose. Enables the UI to render blocks and the "save each block to calendar" pattern.

**What it does:** Saturday + Sunday plans with proper validation, returned as structured data the UI can render as cards.

### Build 3 — Long-horizon stint planner (Spain)

The actually-hard one. Where most of the learning lives.

**New agent patterns:**
- **Nested horizons** — month theme → weekly arc → daily blocks → block details. Each layer planned independently; deeper layers only fan out when their time comes.
- **Memory across sessions** — agent retains plan state, what was tried, what got executed vs. skipped. Probably a simple JSON/SQLite store before reaching for vector DBs.
- **Human-in-the-loop checkpoints** — agent drafts a week, pings Kevin for review, refines, then drafts the next. Doesn't try to plan 12 weeks in one shot.
- **Replanning on signal** — "this week I'm sick" → agent adapts upcoming days without re-doing the whole stint.

**What it does:** "I'm in Sevilla for 3 months — plan it out." Returns a 12-week skeleton, expands week-by-week as time approaches, learns from accept/skip signals.

## Inspiration to borrow from (not compete with)

For the **planner UX / output**:
- **Wanderlog / TripIt** — day-by-day blocks with drive times. Solid visual pattern worth stealing.
- **Mindtrip** — chat → itinerary → "tweak this block" flow. Closest UX to what would feel good for Spain mode.
- **Google Trips** (deprecated but the bones were great) — auto-grouping of nearby POIs into half-day clusters.

For the **personalization / taste-learning** problem:
- **Beli** (restaurant app) — its rank-what-you've-eaten-and-the-algorithm-learns mechanic is a great model for the feedback loop.
- **Letterboxd** — same idea, applied to films. The "your taste profile" view is worth studying.

For **agent-loop patterns specifically** (the learning side):
- **Claude Code / Cursor agents** — for plan → execute → check → repair patterns on multi-step work. More relevant than any travel app.
- **Anthropic's "Computer Use" demos** — for autonomous long-horizon work with checkpoints.
- **Vimcal AI / Reclaim** — for the "agent owns blocks on your calendar" trust gradient.

## Open questions

- **What's in the vault snippet the agent reads each call?** All of `kevin-reber.md`? Plus last 30 days of `Activity/`? Cost vs. quality tradeoff — bigger context = better plan, more tokens. Probably build a `vault_personality_snapshot()` helper that curates ~5–10k tokens of relevant context.
- **Where does plan state live?** Aura's existing storage (Postgres? files on Fly volume?) or something new? Build 3 needs persistent multi-session state.
- **What's the feedback mechanism?** Calendar reactions, a Friday-evening "how was last weekend" prompt, or implicit signal (did the calendar event survive untouched)?
- **How does Spain mode handle location-not-home?** Vault personality is mostly framed around SF; need a clean way to swap "home context" temporarily without polluting the vault.
- **Trust gradient for autonomy.** Build 1 suggests; Build 2 auto-creates calendar events; Build 3... books reservations? Probably never goes that far in v0.

## Where to start

Build 1, but only after deciding on the vault-snippet curation strategy (the first open question). That decision shapes everything downstream — the agent's quality is bounded by what it knows about Kevin, and what it knows comes from how well the snippet is curated.

Suggested first concrete step: prototype `vault_personality_snapshot(intent_hint: str) → str` as a standalone script. Run it with different intents ("plan a quiet Saturday", "plan a 3-month Sevilla stint") and eyeball the output. If the snippets feel like "yes, this is me and this is what I'd want for this trip," the agent has a chance. If they feel generic, fix that before anything else.
