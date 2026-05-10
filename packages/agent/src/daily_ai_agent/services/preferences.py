"""Read user weekend preferences from data/weekend_preferences.json.

The prefs file lives at the monorepo root and is gitignored — see
WEEKEND_ORCHESTRATOR_SPEC.md Section 20. This module loads it lazily and
exposes typed accessors. Missing files fall back to sensible defaults
(all categories enabled, no pinned/excluded artists) so the agent works
out-of-the-box for new installs.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from loguru import logger
from pydantic import BaseModel, Field


# Default categories when the prefs file is missing entirely.
# Must match the IDs in /weekend/categories on the server.
DEFAULT_ENABLED_CATEGORIES = ["trails", "concerts", "itinerary"]


class WeekendPreferences(BaseModel):
    """User-facing weekend preferences."""

    enabled_categories: List[str] = Field(default_factory=lambda: list(DEFAULT_ENABLED_CATEGORIES))
    pinned_artists: List[str] = Field(default_factory=list)
    excluded_artists: List[str] = Field(default_factory=list)
    activity_preferences: List[str] = Field(default_factory=list)
    max_drive_hours: int = Field(default=4)
    budget_level: str = Field(default="moderate")
    home_base: Optional[str] = Field(default=None)


def _find_prefs_path() -> Path:
    """Locate weekend_preferences.json at the monorepo root.

    The agent runs from packages/agent/, so we walk up to find data/.
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "data" / "weekend_preferences.json"
        if candidate.exists():
            return candidate
    # Fall back to the conventional location even if the file doesn't exist —
    # callers handle FileNotFoundError to apply defaults.
    return Path(__file__).resolve().parents[5] / "data" / "weekend_preferences.json"


@lru_cache(maxsize=1)
def load_preferences() -> WeekendPreferences:
    """Load weekend preferences with defaults on missing file or parse error.

    Cached for the process lifetime — if the file changes mid-process the
    cache won't reflect it. Restart the agent to pick up edits.
    """
    path = _find_prefs_path()

    try:
        with path.open() as f:
            raw = json.load(f)
        prefs = WeekendPreferences(**raw)
        logger.info(
            f"Loaded weekend preferences from {path} "
            f"(enabled: {prefs.enabled_categories})"
        )
        return prefs
    except FileNotFoundError:
        logger.info(
            f"No weekend_preferences.json at {path} — using defaults "
            f"(all categories enabled, no pinned artists)"
        )
        return WeekendPreferences()
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(
            f"Failed to parse weekend_preferences.json: {e} — using defaults"
        )
        return WeekendPreferences()


def get_enabled_categories() -> List[str]:
    """Return the list of category IDs the user has enabled."""
    return load_preferences().enabled_categories


def clear_preferences_cache() -> None:
    """Clear the prefs cache (useful for tests + after live edits)."""
    load_preferences.cache_clear()
