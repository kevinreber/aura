"""Tests for the weekend preferences reader."""

import json
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _clear_prefs_cache():
    """Clear the lru_cache between tests so each test gets a fresh load."""
    from daily_ai_agent.services.preferences import clear_preferences_cache

    clear_preferences_cache()
    yield
    clear_preferences_cache()


@pytest.fixture
def temp_prefs_file(monkeypatch, tmp_path):
    """Create a temporary prefs file and point the loader at it."""
    prefs_path = tmp_path / "data" / "weekend_preferences.json"
    prefs_path.parent.mkdir()

    def _make(contents: dict):
        prefs_path.write_text(json.dumps(contents))
        from daily_ai_agent.services import preferences as prefs_module

        monkeypatch.setattr(prefs_module, "_find_prefs_path", lambda: prefs_path)
        return prefs_path

    return _make


def test_returns_defaults_when_file_missing(monkeypatch, tmp_path):
    """When the prefs file doesn't exist, fall back to all-categories-enabled."""
    from daily_ai_agent.services import preferences as prefs_module

    nonexistent = tmp_path / "missing.json"
    monkeypatch.setattr(prefs_module, "_find_prefs_path", lambda: nonexistent)

    prefs = prefs_module.load_preferences()

    assert prefs.enabled_categories == ["trails", "concerts", "itinerary"]
    assert prefs.pinned_artists == []
    assert prefs.budget_level == "moderate"


def test_loads_user_prefs_from_file(temp_prefs_file):
    """When the file exists, return its contents typed as WeekendPreferences."""
    from daily_ai_agent.services.preferences import load_preferences

    temp_prefs_file({
        "enabled_categories": ["trails"],
        "pinned_artists": ["Tycho", "Khruangbin"],
        "excluded_artists": ["Genre I Hate"],
        "activity_preferences": ["hiking"],
        "max_drive_hours": 6,
        "budget_level": "premium",
        "home_base": "Boulder, CO",
    })

    prefs = load_preferences()

    assert prefs.enabled_categories == ["trails"]
    assert prefs.pinned_artists == ["Tycho", "Khruangbin"]
    assert prefs.excluded_artists == ["Genre I Hate"]
    assert prefs.max_drive_hours == 6
    assert prefs.home_base == "Boulder, CO"


def test_partial_prefs_get_defaults_for_missing_fields(temp_prefs_file):
    """If the user only sets some fields, the rest fall back to defaults."""
    from daily_ai_agent.services.preferences import load_preferences

    temp_prefs_file({"enabled_categories": ["concerts"]})

    prefs = load_preferences()

    assert prefs.enabled_categories == ["concerts"]
    assert prefs.pinned_artists == []  # default
    assert prefs.budget_level == "moderate"  # default


def test_invalid_json_falls_back_to_defaults(monkeypatch, tmp_path):
    """Corrupt prefs file shouldn't crash the agent — log + use defaults."""
    from daily_ai_agent.services import preferences as prefs_module

    bad_file = tmp_path / "bad.json"
    bad_file.write_text("this is not valid json {{{")

    monkeypatch.setattr(prefs_module, "_find_prefs_path", lambda: bad_file)

    prefs = prefs_module.load_preferences()

    assert prefs.enabled_categories == ["trails", "concerts", "itinerary"]


def test_get_enabled_categories_helper(temp_prefs_file):
    """Convenience helper returns just the enabled_categories list."""
    from daily_ai_agent.services.preferences import get_enabled_categories

    temp_prefs_file({"enabled_categories": ["trails", "itinerary"]})

    assert get_enabled_categories() == ["trails", "itinerary"]


# ==================== Orchestrator filter integration ====================


def test_orchestrator_filter_drops_disabled_weekend_tools():
    """When concerts are disabled, get_weekend_concerts should be filtered out."""
    from daily_ai_agent.agent.orchestrator import _filter_tools_by_enabled_categories
    from daily_ai_agent.agent.tools import get_all_tools

    all_tools = get_all_tools()
    filtered = _filter_tools_by_enabled_categories(
        all_tools, enabled=["trails", "itinerary"]  # concerts disabled
    )

    tool_names = {t.name for t in filtered}
    assert "get_weekend_trails" in tool_names  # enabled
    assert "generate_weekend_itinerary" in tool_names  # enabled
    assert "get_weekend_concerts" not in tool_names  # disabled


def test_orchestrator_filter_keeps_non_weekend_tools():
    """Always-on tools (weather, calendar) survive any category filter."""
    from daily_ai_agent.agent.orchestrator import _filter_tools_by_enabled_categories
    from daily_ai_agent.agent.tools import get_all_tools

    all_tools = get_all_tools()
    # Disable everything weekend-related
    filtered = _filter_tools_by_enabled_categories(all_tools, enabled=[])

    tool_names = {t.name for t in filtered}
    # Weekend tools all gone
    assert "get_weekend_trails" not in tool_names
    assert "get_weekend_concerts" not in tool_names
    assert "generate_weekend_itinerary" not in tool_names
    # But weather/calendar/todo etc still present
    assert "get_weather" in tool_names
    assert "get_calendar" in tool_names
    assert "get_todos" in tool_names


def test_orchestrator_filter_with_all_categories_enabled_keeps_everything():
    """Default config (all enabled) should preserve all 13 tools."""
    from daily_ai_agent.agent.orchestrator import _filter_tools_by_enabled_categories
    from daily_ai_agent.agent.tools import get_all_tools

    all_tools = get_all_tools()
    filtered = _filter_tools_by_enabled_categories(
        all_tools, enabled=["trails", "concerts", "itinerary"]
    )

    assert len(filtered) == len(all_tools)
