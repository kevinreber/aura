#!/usr/bin/env python3
"""vault_personality_snapshot — prototype for the planner agent's personality model.

Reads brain-vault, takes an intent_hint, returns a curated taste profile.

This is NOT yet an agent — it's a single LLM call that synthesizes vault content
into a structured snapshot the downstream planner will consume. The agent loop
comes next; this is the input layer.

Usage:
    uv run --with anthropic scripts/vault_snapshot.py "3 months in Sevilla"
    uv run --with anthropic scripts/vault_snapshot.py "plan a quiet Saturday in SF"
    uv run --with anthropic scripts/vault_snapshot.py "..." --no-llm  # dump raw input

Env:
    ANTHROPIC_API_KEY must be set in the shell environment.
"""

import argparse
import os
import sys
from datetime import date, timedelta
from pathlib import Path

VAULT_DEFAULT = Path.home() / "Projects" / "brain-vault"
STABLE_NOTE = "Projects/kevin-reber.md"
DEFAULT_RECENT_DAYS = 14
DEFAULT_REFLECTION_DAYS = 90
DEFAULT_MODEL = "claude-sonnet-4-6"

CURATOR_SYSTEM_INSTRUCTIONS = """\
You are the personality-curator step of a personal planner agent.

You receive (1) Kevin's stable identity note and (2) recent activity/reflection
notes from his second-brain vault. Produce a *trip-aware* personality snapshot
the downstream planner can use to propose activities that feel personal to
Kevin — not generic recommendations.

Rules:
- Extract STABLE INTERESTS that translate across geography (sports, music,
  architecture, photography, creative practice, work rhythm).
- Extract CURRENT CONTEXT from recent activity (energy level, current
  obsessions, recent gripes, time pressures).
- DROP location-specific anchors that don't apply to the intent context
  (named SF/NYC spots, specific commute routes).
- Note ENERGY + CONSTRAINTS the planner needs (e.g., timezone-offset
  implications, current training mileage, work-from-anywhere constraints).
- Be specific. "Likes music" is useless; "French-house bias, top artists
  include X/Y/Z, late-night listener" is useful.
- Output markdown, ~600-800 words. Structured but flexible — skip sections
  with no signal.

The downstream planner has tools for weather, calendar, maps, events, and
trails. Your job is *taste profile*, not knowledge or recommendations.
Don't propose specific places; describe who Kevin is.
"""


def read_stable_identity(vault: Path) -> str:
    path = vault / STABLE_NOTE
    if not path.exists():
        raise SystemExit(f"Stable identity note missing: {path}")
    return path.read_text()


def files_within(folder: Path, days: int, suffix_strip: str = "") -> list[Path]:
    """Return .md files whose YYYY-MM-DD prefix is within the last `days` days."""
    if not folder.exists():
        return []
    cutoff = date.today() - timedelta(days=days)
    found = []
    for f in sorted(folder.glob("*.md")):
        stem = f.stem
        if suffix_strip and stem.endswith(suffix_strip):
            stem = stem[: -len(suffix_strip)]
        # Take leading YYYY-MM-DD if present.
        try:
            file_date = date.fromisoformat(stem[:10])
        except ValueError:
            continue
        if file_date >= cutoff:
            found.append(f)
    return found


def assemble_vault_corpus(vault: Path, days: int, reflection_days: int) -> str:
    parts = ["# STABLE IDENTITY\n\n## Projects/kevin-reber.md\n\n"]
    parts.append(read_stable_identity(vault))

    parts.append(f"\n\n# RECENT ACTIVITY (last {days} days)\n")
    # Activity filenames are YYYY-MM-DD.md (work) or YYYY-MM-DD-personal.md.
    for f in files_within(vault / "Activity", days, suffix_strip="-personal"):
        rel = f.relative_to(vault)
        parts.append(f"\n## {rel}\n\n{f.read_text()}\n")

    parts.append(f"\n\n# RECENT REFLECTIONS (last {reflection_days} days)\n")
    for f in files_within(vault / "Reflections", reflection_days):
        rel = f.relative_to(vault)
        parts.append(f"\n## {rel}\n\n{f.read_text()}\n")

    return "".join(parts)


def call_claude(corpus: str, intent: str, model: str) -> str:
    try:
        import anthropic
    except ImportError:
        raise SystemExit(
            "anthropic SDK not installed. Run with:\n"
            "  uv run --with anthropic scripts/vault_snapshot.py ..."
        )
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY not set in environment")

    client = anthropic.Anthropic()
    # Cache the system prompt + vault corpus — they're stable across calls
    # with different intent hints. Only the user message varies, so iteration
    # over intents hits cache and stays cheap.
    resp = client.messages.create(
        model=model,
        max_tokens=3500,
        system=[
            {"type": "text", "text": CURATOR_SYSTEM_INSTRUCTIONS},
            {
                "type": "text",
                "text": corpus,
                "cache_control": {"type": "ephemeral"},
            },
        ],
        messages=[
            {
                "role": "user",
                "content": (
                    f"Produce the personality snapshot for this intent:\n\n"
                    f"INTENT: {intent}\n"
                ),
            }
        ],
    )

    usage = resp.usage
    print(
        f"[usage] input={usage.input_tokens} "
        f"cache_create={getattr(usage, 'cache_creation_input_tokens', 0)} "
        f"cache_read={getattr(usage, 'cache_read_input_tokens', 0)} "
        f"output={usage.output_tokens}",
        file=sys.stderr,
    )
    return resp.content[0].text


def generate_snapshot(
    intent: str,
    vault_path: Path = VAULT_DEFAULT,
    days: int = DEFAULT_RECENT_DAYS,
    reflection_days: int = DEFAULT_REFLECTION_DAYS,
    model: str = DEFAULT_MODEL,
) -> str:
    """Library entry point — assemble corpus, curate via Claude, return snapshot.

    Used by weekend_planner.py and any other agent that needs a personality
    profile. Same behavior as the CLI default path, no I/O side effects.
    """
    corpus = assemble_vault_corpus(vault_path, days, reflection_days)
    return call_claude(corpus, intent, model)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("intent", help='e.g. "3 months in Sevilla"')
    parser.add_argument("--vault-path", type=Path, default=VAULT_DEFAULT)
    parser.add_argument("--days", type=int, default=DEFAULT_RECENT_DAYS,
                        help="days of Activity/ to include")
    parser.add_argument("--reflection-days", type=int,
                        default=DEFAULT_REFLECTION_DAYS)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--no-llm", action="store_true",
                        help="dump raw corpus instead of calling Claude")
    parser.add_argument("--output", type=Path,
                        help="also write snapshot to this file")
    args = parser.parse_args()

    corpus = assemble_vault_corpus(
        args.vault_path, args.days, args.reflection_days
    )

    if args.no_llm:
        print(corpus)
        return

    snapshot = call_claude(corpus, args.intent, args.model)
    print(snapshot)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(snapshot)
        print(f"\n[saved to {args.output}]", file=sys.stderr)


if __name__ == "__main__":
    main()
