#!/usr/bin/env python3
"""weekend_planner.py — Build #1 of the planner agent curriculum.

Vault-aware Saturday planner. Demonstrates a hand-rolled agent loop using
Anthropic's tool-use API:

    snapshot ──► planner (tools loop) ──► critic (reflection) ──► itinerary

We deliberately do NOT use LangChain here. The point of Build #1 is to
*see* the agent loop — the request/response, tool_use blocks, tool_result
blocks, stop_reason — without a framework hiding it.

Tools are mocked in this version. Build #2 swaps in real Aura MCP tools.

Usage:
    # Generate a fresh snapshot + plan
    uv run --with anthropic scripts/weekend_planner.py \\
        "plan a quiet Saturday in SF - low energy, no driving over an hour" \\
        --date 2026-06-06

    # Reuse a saved snapshot (cheaper, faster, easier to iterate on the planner)
    uv run --with anthropic scripts/weekend_planner.py \\
        "plan a quiet Saturday in SF - low energy, no driving over an hour" \\
        --snapshot-file snapshots/quiet-sat.md \\
        --date 2026-06-06

Env:
    ANTHROPIC_API_KEY must be set.
"""

import argparse
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

# Import the sibling snapshot module.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from vault_snapshot import generate_snapshot  # noqa: E402

DEFAULT_MODEL = "claude-sonnet-4-6"
MAX_AGENT_ITERATIONS = 8


# ============================================================================
# Mocked tools — realistic SF data so we can validate the loop without API
# keys for Google Places, Ticketmaster, etc. Build #2 will swap these for
# real Aura MCP tool calls.
# ============================================================================

def tool_get_weather(date: str, location: str) -> dict:
    return {
        "date": date,
        "location": location,
        "high_f": 65,
        "low_f": 52,
        "conditions": "partly cloudy",
        "precip_chance_pct": 10,
        "sunset_local": "20:18",
    }


def tool_search_outdoor(location: str, activity_type: str,
                         max_distance_mi: int = 25) -> list[dict]:
    options = [
        {
            "name": "Lands End Coastal Trail",
            "type": "walk/run",
            "distance_mi": 3.4,
            "elevation_gain_ft": 350,
            "difficulty": "easy",
            "drive_from_mission_min": 22,
            "notes": "Cliff views, golden-hour-worthy. Crowds moderate.",
        },
        {
            "name": "Glen Canyon Park",
            "type": "walk/run",
            "distance_mi": 2.0,
            "elevation_gain_ft": 200,
            "difficulty": "easy",
            "drive_from_mission_min": 12,
            "notes": "Quiet urban canyon. Camera-friendly, low traffic.",
        },
        {
            "name": "Marin Headlands - Coastal Loop",
            "type": "trail run",
            "distance_mi": 6.2,
            "elevation_gain_ft": 1100,
            "difficulty": "moderate",
            "drive_from_mission_min": 38,
            "notes": "Views; pushes 'low energy' brief.",
        },
        {
            "name": "Mission Cliffs Climbing Gym",
            "type": "indoor climbing",
            "distance_mi": 0.5,
            "elevation_gain_ft": 0,
            "difficulty": "self-regulated",
            "drive_from_mission_min": 5,
            "notes": "Walkable. 60-120 min session typical.",
        },
    ]
    if activity_type == "climbing":
        return [o for o in options if "climbing" in o["type"]]
    return options


def tool_search_events(location: str, date: str,
                        categories: list[str] | None = None) -> list[dict]:
    return [
        {
            "title": "Bon Entendeur (DJ set)",
            "venue": "The Midway",
            "neighborhood": "Dogpatch",
            "start": f"{date}T22:00",
            "end": f"{date}T02:00",
            "category": "music/electronic",
            "drive_from_mission_min": 12,
            "notes": "French house, late-night. High energy.",
        },
        {
            "title": "SFMOMA — Brutalism: Drawings retrospective",
            "venue": "SFMOMA",
            "neighborhood": "SoMa",
            "start": f"{date}T10:00",
            "end": f"{date}T17:00",
            "category": "art/architecture",
            "drive_from_mission_min": 10,
            "notes": "Architectural drawings exhibit. Quiet weekday-feel.",
        },
        {
            "title": "Andytown Roasters cupping session",
            "venue": "Andytown Roasters",
            "neighborhood": "Outer Sunset",
            "start": f"{date}T11:00",
            "end": f"{date}T12:30",
            "category": "food/coffee",
            "drive_from_mission_min": 22,
            "notes": "Quiet, hands-on. Low energy, social-optional.",
        },
        {
            "title": "Sutro Tower fog photography meetup",
            "venue": "Twin Peaks viewpoint",
            "neighborhood": "Twin Peaks",
            "start": f"{date}T17:30",
            "end": f"{date}T19:30",
            "category": "photography",
            "drive_from_mission_min": 9,
            "notes": "Blue hour + fog. Self-paced, camera-out.",
        },
    ]


def tool_get_travel_time(origin: str, destination: str,
                          depart_at: str) -> dict:
    # Hardcoded Mission-centric times for the prototype.
    table = {
        ("Mission", "Lands End"): 22,
        ("Mission", "Glen Canyon"): 12,
        ("Mission", "Marin Headlands"): 38,
        ("Mission", "Mission Cliffs"): 5,
        ("Mission", "The Midway"): 12,
        ("Mission", "SFMOMA"): 10,
        ("Mission", "Andytown"): 22,
        ("Mission", "Twin Peaks"): 9,
        ("Mission", "Outer Sunset"): 22,
        ("Mission", "Dogpatch"): 12,
        ("Mission", "SoMa"): 10,
    }
    minutes = 15  # default fallback
    for (o, d), mins in table.items():
        if o.lower() in origin.lower() and d.lower() in destination.lower():
            minutes = mins
            break
    return {
        "origin": origin,
        "destination": destination,
        "depart_at": depart_at,
        "duration_min": minutes,
        "traffic": "light",
    }


# ============================================================================
# Tool registry — what we tell the model + how we execute
# ============================================================================

TOOL_DEFINITIONS = [
    {
        "name": "get_weather",
        "description": "Get weather forecast for a date and location.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "ISO date YYYY-MM-DD"},
                "location": {"type": "string"},
            },
            "required": ["date", "location"],
        },
    },
    {
        "name": "search_outdoor_activities",
        "description": "Find outdoor activities (trails, parks, gyms) near a location.",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {"type": "string"},
                "activity_type": {
                    "type": "string",
                    "enum": ["hiking", "running", "climbing", "any"],
                },
                "max_distance_mi": {"type": "integer", "default": 25},
            },
            "required": ["location", "activity_type"],
        },
    },
    {
        "name": "search_events",
        "description": "Find events (music, art, food, photography, ...) on a date near a location.",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {"type": "string"},
                "date": {"type": "string", "description": "ISO date YYYY-MM-DD"},
                "categories": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["location", "date"],
        },
    },
    {
        "name": "get_travel_time",
        "description": "Realistic travel time between two SF locations at a given departure time.",
        "input_schema": {
            "type": "object",
            "properties": {
                "origin": {"type": "string"},
                "destination": {"type": "string"},
                "depart_at": {"type": "string", "description": "ISO datetime"},
            },
            "required": ["origin", "destination", "depart_at"],
        },
    },
]

TOOL_IMPLS = {
    "get_weather": tool_get_weather,
    "search_outdoor_activities": tool_search_outdoor,
    "search_events": tool_search_events,
    "get_travel_time": tool_get_travel_time,
}


def execute_tool(name: str, args: dict) -> str:
    impl = TOOL_IMPLS.get(name)
    if impl is None:
        return json.dumps({"error": f"unknown tool: {name}"})
    try:
        return json.dumps(impl(**args))
    except TypeError as e:
        return json.dumps({"error": f"bad arguments to {name}: {e}"})


# ============================================================================
# Phase 1: planner agent loop
# ============================================================================

PLANNER_SYSTEM_PROMPT = """\
You are the planning step of a personal weekend planner agent for Kevin.

Inputs you'll receive:
  1. A personality snapshot (who Kevin is, current context)
  2. An intent (what he wants from this weekend)
  3. A target date

Your job: produce a structured itinerary with 2-4 blocks for the target date.
Use the tools to research actual options before drafting blocks.

GROUNDING RULES (strictly enforced — the critic will reject lies):
- Every block must declare HOW it's grounded:
  * "tool"     — the venue/activity came directly from a tool result. The
                 evidence MUST quote specific facts that appeared in the
                 tool's JSON response (venue name, time, distance, etc.).
  * "snapshot" — the block was derived from the personality snapshot alone
                 (e.g., "slow morning at home"). No tool result backs it.
                 Evidence MUST quote a specific phrase from the snapshot.
  * "invented" — the block is a reasonable inference but neither a tool nor
                 the snapshot directly supports the specific venue/details.
                 Use this honestly when you reach beyond what was returned.
- Do NOT mark a block as "tool" if the venue wasn't actually in a tool result.
  Marking an invented venue as "tool" is the single worst failure mode.
- If the right activity exists but no tool surfaced a specific venue, mark
  the block "invented" and say so. Honesty beats fake confidence.

Other rules:
- Honor explicit constraints in the intent (drive time, energy level, etc.).
- Sequence blocks with realistic travel time. Check travel for non-trivial
  transitions using get_travel_time.
- When done researching, output the final itinerary as JSON inside a fenced
  block: ```json ... ```

JSON shape:
{
  "date": "YYYY-MM-DD",
  "blocks": [
    {
      "start": "HH:MM",
      "end": "HH:MM",
      "title": "...",
      "location": "...",
      "why_this_fits": "1 sentence tying to the snapshot",
      "grounding": "tool" | "snapshot" | "invented",
      "evidence": ["specific quote from tool result or snapshot", "..."]
    }
  ],
  "notes": "Any caveats or callouts for Kevin."
}
"""


def plan_intent(intent: str, snapshot: str, target_date: str,
                model: str = DEFAULT_MODEL,
                max_iters: int = MAX_AGENT_ITERATIONS) -> tuple[dict, list[dict]]:
    """Hand-rolled agent loop.

    Returns (itinerary, tool_log) where tool_log is a list of
    {name, input, result} dicts recording every tool call. The critic uses
    the log to validate that grounding claims match what actually ran.
    """
    import anthropic
    client = anthropic.Anthropic()

    # The snapshot is large and stable across iterations — cache it so
    # iterations 2+ pay ~10% the input cost. System prompt is also cached.
    system = [
        {
            "type": "text",
            "text": PLANNER_SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        },
    ]
    initial_user_msg = [
        {
            "type": "text",
            "text": f"## Personality snapshot\n\n{snapshot}",
            "cache_control": {"type": "ephemeral"},
        },
        {
            "type": "text",
            "text": (
                f"## Intent\n\n{intent}\n\n"
                f"## Target date\n\n{target_date}\n\n"
                f"Plan it. Use tools to research before drafting blocks."
            ),
        },
    ]
    messages: list[dict] = [{"role": "user", "content": initial_user_msg}]
    tool_log: list[dict] = []

    for iteration in range(max_iters):
        print(f"\n--- agent iteration {iteration + 1} ---", file=sys.stderr)
        resp = client.messages.create(
            model=model,
            max_tokens=2000,
            system=system,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )
        usage = resp.usage
        print(
            f"  [usage] in={usage.input_tokens} "
            f"cache_read={getattr(usage, 'cache_read_input_tokens', 0)} "
            f"cache_create={getattr(usage, 'cache_creation_input_tokens', 0)} "
            f"out={usage.output_tokens}",
            file=sys.stderr,
        )

        messages.append({"role": "assistant", "content": resp.content})

        for block in resp.content:
            if block.type == "text" and block.text.strip():
                print(f"  [thinking] {block.text.strip()[:300]}",
                      file=sys.stderr)

        if resp.stop_reason == "end_turn":
            text = "".join(b.text for b in resp.content if b.type == "text")
            return parse_itinerary(text), tool_log

        tool_results = []
        for block in resp.content:
            if block.type == "tool_use":
                print(f"  → {block.name}({json.dumps(block.input)})",
                      file=sys.stderr)
                result_str = execute_tool(block.name, block.input)
                preview = result_str if len(result_str) < 200 \
                    else result_str[:200] + "..."
                print(f"    ← {preview}", file=sys.stderr)
                tool_log.append({
                    "name": block.name,
                    "input": block.input,
                    "result": result_str,
                })
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_str,
                })
        messages.append({"role": "user", "content": tool_results})

    raise RuntimeError(f"agent loop exceeded {max_iters} iterations")


def parse_itinerary(text: str) -> dict:
    """Pull JSON from a ```json ... ``` fenced block. Tolerant of formatting."""
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError as e:
            return {"raw": text, "_warning": f"JSON parse error: {e}"}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw": text, "_warning": "no JSON block found"}


# ============================================================================
# Phase 2: critic / reflection
# ============================================================================

CRITIC_SYSTEM_PROMPT = """\
You are the critic step of a planner agent. You receive a proposed itinerary,
the personality snapshot it was meant to fit, the original intent, AND the
complete log of tool calls that the planner ran during research.

Your job has two parts:

PART 1 — GROUNDING VALIDATION (the most important check):
For each block claiming grounding == "tool":
  - Find the venue/activity in the tool log. Does any tool result actually
    contain this name?
  - If yes: confirm the evidence quotes match what the tool returned.
  - If no: this is a hallucinated venue. You must either:
      a) replace it with a venue that IS in the tool log, OR
      b) downgrade grounding to "invented" and update evidence to be honest
         ("no tool surfaced this; included as a plausible inference").

For each block claiming grounding == "snapshot":
  - Confirm the evidence quotes a phrase that appears in the personality
    snapshot. If it can't be quoted, downgrade to "invented".

PART 2 — STANDARD PLANNER CHECKS:
  1. Explicit intent constraints (drive time, energy level, time-of-day).
  2. Personality fit — does each block match the snapshot?
  3. Logistics — do block times leave room for travel? Are venues open?
  4. Drift — does any block feel like a generic suggestion?

OUTPUT FORMAT:
- Briefly list the grounding-validation results (per block: ✓ verified / ✗ violation + fix).
- List any logistic/fit issues.
- Return the final itinerary as JSON inside a ```json ... ``` block. Even if
  no changes were made, return the JSON so downstream consumers always have it.
"""


def critique_and_refine(itinerary: dict, snapshot: str, intent: str,
                         target_date: str, tool_log: list[dict],
                         model: str = DEFAULT_MODEL) -> dict:
    import anthropic
    client = anthropic.Anthropic()

    print("\n--- reflection pass ---", file=sys.stderr)

    # Format tool log compactly so the critic can scan it.
    tool_log_text = "\n\n".join(
        f"### Call {i + 1}: {entry['name']}({json.dumps(entry['input'])})\n"
        f"```json\n{entry['result']}\n```"
        for i, entry in enumerate(tool_log)
    ) or "(no tool calls were made)"

    resp = client.messages.create(
        model=model,
        max_tokens=2500,
        system=CRITIC_SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": (
                f"## Personality snapshot\n\n{snapshot}\n\n"
                f"## Original intent\n\n{intent}\n\n"
                f"## Target date\n\n{target_date}\n\n"
                f"## Tool log (what the planner actually researched)\n\n"
                f"{tool_log_text}\n\n"
                f"## Proposed itinerary\n\n```json\n"
                f"{json.dumps(itinerary, indent=2)}\n```"
            ),
        }],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    print(text, file=sys.stderr)

    refined = parse_itinerary(text)
    if refined.get("_warning"):
        return itinerary
    return refined


# ============================================================================
# Programmatic grounding check (belt-and-suspenders after the critic LLM)
# ============================================================================

def validate_grounding(itinerary: dict, snapshot: str,
                        tool_log: list[dict]) -> list[str]:
    """Check each block's grounding claim against the tool log + snapshot.

    Returns a list of human-readable violations. Empty list = all blocks
    are honestly grounded. This is mechanical pattern-matching, not an LLM
    call — it can't catch every kind of drift, but it will catch the
    "claimed tool, didn't appear in tool log" failure mode that cost us
    Sightglass Coffee last run.
    """
    violations = []
    blocks = itinerary.get("blocks", [])
    # Concatenate all tool result text for cheap substring checks.
    tool_text = " ".join(e["result"] for e in tool_log).lower()
    snapshot_lower = snapshot.lower()

    for i, block in enumerate(blocks):
        grounding = block.get("grounding")
        evidence = block.get("evidence", [])
        title = block.get("title", f"block {i}")

        if grounding not in ("tool", "snapshot", "invented"):
            violations.append(
                f"Block {i} ({title}): grounding={grounding!r} is not one of "
                f"tool/snapshot/invented"
            )
            continue
        if not evidence:
            violations.append(
                f"Block {i} ({title}): grounding={grounding!r} but no evidence provided"
            )
            continue

        # For "tool" grounding, at least one evidence string should be findable
        # in the tool log. We allow loose matching — if the first 4 meaningful
        # words of the evidence appear contiguously, accept.
        if grounding == "tool":
            if not any(_loose_match(e.lower(), tool_text) for e in evidence):
                violations.append(
                    f"Block {i} ({title}): claims grounding=tool but no "
                    f"evidence substring was found in the tool log"
                )

        # For "snapshot" grounding, same check against the snapshot.
        elif grounding == "snapshot":
            if not any(_loose_match(e.lower(), snapshot_lower) for e in evidence):
                violations.append(
                    f"Block {i} ({title}): claims grounding=snapshot but no "
                    f"evidence substring was found in the snapshot"
                )

    return violations


def _normalize_for_match(s: str) -> str:
    """Lowercase + collapse all non-alphanumeric runs into single spaces.

    Lets us match prose evidence like  "Event title: 'Andytown Roasters'"
    against JSON  '"title": "Andytown Roasters"'  without false negatives
    from quote/punctuation differences.
    """
    return re.sub(r"\W+", " ", s.lower()).strip()


def _loose_match(needle: str, haystack: str, words: int = 4) -> bool:
    """Does any `words`-token contiguous slice of needle appear in haystack?

    Operates on normalized forms (alphanumeric tokens, lowercase). If the
    needle is shorter than `words` tokens, matches the whole normalized
    needle as a substring instead.
    """
    n_tokens = _normalize_for_match(needle).split()
    haystack_norm = _normalize_for_match(haystack)
    if not n_tokens or not haystack_norm:
        return False
    if len(n_tokens) < words:
        return " ".join(n_tokens) in haystack_norm
    for i in range(len(n_tokens) - words + 1):
        if " ".join(n_tokens[i:i + words]) in haystack_norm:
            return True
    return False


# ============================================================================
# CLI
# ============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("intent", help="What you want planned")
    parser.add_argument("--date", default=date.today().isoformat(),
                        help="Target date YYYY-MM-DD (default: today)")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--snapshot-file", type=Path,
                        help="Use a pre-generated snapshot file instead of regenerating")
    parser.add_argument("--output", type=Path,
                        help="Write final itinerary JSON to file")
    parser.add_argument("--skip-critic", action="store_true",
                        help="Skip the reflection pass (debug only)")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY not set")

    print(f"Intent: {args.intent}", file=sys.stderr)
    print(f"Date:   {args.date}", file=sys.stderr)

    if args.snapshot_file:
        print(f"Snapshot: reading {args.snapshot_file}", file=sys.stderr)
        snapshot = args.snapshot_file.read_text()
    else:
        print("Snapshot: generating fresh...", file=sys.stderr)
        snapshot = generate_snapshot(args.intent)

    proposed, tool_log = plan_intent(args.intent, snapshot, args.date,
                                      model=args.model)

    if args.skip_critic:
        final = proposed
    else:
        final = critique_and_refine(proposed, snapshot, args.intent,
                                     args.date, tool_log, model=args.model)

    # Programmatic belt-and-suspenders check after the critic LLM. Even if
    # the critic missed a grounding violation, this should catch it.
    print("\n--- mechanical grounding check ---", file=sys.stderr)
    violations = validate_grounding(final, snapshot, tool_log)
    if violations:
        print(f"  ⚠ {len(violations)} grounding violation(s) found:",
              file=sys.stderr)
        for v in violations:
            print(f"    - {v}", file=sys.stderr)
        final.setdefault("notes", "")
        final["_grounding_violations"] = violations
    else:
        print("  ✓ all blocks pass grounding check", file=sys.stderr)

    print("\n=== FINAL ITINERARY ===")
    print(json.dumps(final, indent=2))

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(final, indent=2))
        print(f"\n[saved to {args.output}]", file=sys.stderr)


if __name__ == "__main__":
    main()
