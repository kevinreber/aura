"""Read user weekend preferences from data/weekend_preferences.json.

The prefs file lives at the monorepo root and is gitignored — see
WEEKEND_ORCHESTRATOR_SPEC.md Section 20. This module loads it lazily and
exposes typed accessors. Missing files fall back to sensible defaults
(all categories enabled, no pinned/excluded artists) so the agent works
out-of-the-box for new installs.
"""

import json
import os
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
    """Locate weekend_preferences.json.

    Resolution order:
      1. WEEKEND_PREFS_PATH env var (explicit override — recommended for prod)
      2. Walk up from this file looking for data/weekend_preferences.json
      3. Fall back to data/weekend_preferences.json relative to cwd

    The fallback never throws — callers handle FileNotFoundError downstream
    to apply defaults so the agent works on first run before a prefs file
    exists.

    Bug history: previously hardcoded `parents[5]` for the local monorepo
    layout, which raised IndexError in Docker (where the path depth is
    shorter, e.g. /app/src/daily_ai_agent/services/preferences.py has only
    4 parents). Caused agent to crash on startup in any non-local deploy.
    """
    override = os.environ.get("WEEKEND_PREFS_PATH")
    if override:
        return Path(override)

    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "data" / "weekend_preferences.json"
        if candidate.exists():
            return candidate

    # File not found in any ancestor. Return a path-shaped non-existent
    # location — callers will FileNotFoundError and apply defaults.
    return Path.cwd() / "data" / "weekend_preferences.json"


def load_preferences() -> WeekendPreferences:
    """Load weekend preferences with defaults on missing file or parse error.

    Reads the file fresh on every call so live UI toggles take effect immediately
    without an agent restart. The file is small (<1KB) — JSON parsing cost is
    negligible.
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
    """No-op kept for backwards compatibility with existing tests.

    The cache was removed so that UI toggles take effect immediately. This
    function used to invalidate the lru_cache; now it does nothing because
    every load_preferences() call reads the file fresh.
    """
    return None
