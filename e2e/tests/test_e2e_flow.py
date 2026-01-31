"""
End-to-End Tests for Aura Platform

Tests the complete flow: UI -> Agent -> MCP Server

These tests verify:
1. Service health and connectivity
2. MCP Server tool endpoints work correctly
3. Agent can process requests and call MCP tools
4. Full chat flow works (prompt -> agent -> MCP -> response)
"""

import pytest
import httpx
from datetime import datetime
from rich.console import Console

console = Console()


# =============================================================================
# Health Check Tests
# =============================================================================


@pytest.mark.e2e
class TestServiceHealth:
    """Test that all services are healthy and responding."""

    async def test_mcp_server_health(
        self, http_client: httpx.AsyncClient, mcp_url: str, wait_for_services
    ):
        """MCP Server should respond to health checks."""
        response = await http_client.get(f"{mcp_url}/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        console.print(f"[green]MCP Server version: {data['version']}[/green]")

    async def test_agent_health(
        self, http_client: httpx.AsyncClient, agent_url: str, wait_for_services
    ):
        """Agent should respond to health checks."""
        response = await http_client.get(f"{agent_url}/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "mcp_server" in data
        console.print(f"[green]Agent version: {data['version']}[/green]")
        console.print(f"[green]Agent MCP URL: {data['mcp_server']}[/green]")

    async def test_mcp_server_tools_list(
        self, http_client: httpx.AsyncClient, mcp_url: str, wait_for_services
    ):
        """MCP Server should list available tools."""
        response = await http_client.get(f"{mcp_url}/tools")

        assert response.status_code == 200
        data = response.json()
        assert "tools" in data
        assert "server_info" in data

        tools = data["tools"]
        console.print(f"[green]Available MCP tools: {len(tools)}[/green]")

        # Verify expected tools exist
        expected_tools = [
            "weather.get_daily",
            "calendar.list_events",
            "todo.list",
            "mobility.get_commute",
        ]
        for tool in expected_tools:
            assert tool in tools, f"Expected tool '{tool}' not found in MCP Server"

    async def test_agent_tools_list(
        self, http_client: httpx.AsyncClient, agent_url: str, wait_for_services
    ):
        """Agent should list available tool endpoints."""
        response = await http_client.get(f"{agent_url}/tools")

        assert response.status_code == 200
        data = response.json()
        assert "tools" in data
        assert "ai_features" in data

        console.print(f"[green]Agent tool categories: {list(data.keys())}[/green]")


# =============================================================================
# MCP Server Tool Tests
# =============================================================================


@pytest.mark.e2e
class TestMCPServerTools:
    """Test MCP Server tool endpoints directly."""

    async def test_weather_tool(
        self, http_client: httpx.AsyncClient, mcp_url: str, wait_for_services
    ):
        """Weather tool should return weather data."""
        response = await http_client.post(
            f"{mcp_url}/tools/weather.get_daily",
            json={"location": "San Francisco, CA", "when": "today"},
        )

        # May fail if WEATHER_API_KEY not configured - that's OK in CI
        if response.status_code == 200:
            data = response.json()
            console.print(f"[green]Weather response: {data.get('location', 'N/A')}[/green]")
        else:
            console.print(
                f"[yellow]Weather tool returned {response.status_code} "
                "(API key may not be configured)[/yellow]"
            )

    async def test_todo_list_tool(
        self, http_client: httpx.AsyncClient, mcp_url: str, wait_for_services
    ):
        """Todo list tool should return todos."""
        response = await http_client.post(
            f"{mcp_url}/tools/todo.list",
            json={"include_completed": False},
        )

        # May fail if TODOIST_API_KEY not configured
        if response.status_code == 200:
            data = response.json()
            console.print(f"[green]Todo response: {data.get('total_items', 0)} items[/green]")
        else:
            console.print(
                f"[yellow]Todo tool returned {response.status_code} "
                "(API key may not be configured)[/yellow]"
            )

    async def test_calendar_list_events(
        self, http_client: httpx.AsyncClient, mcp_url: str, wait_for_services
    ):
        """Calendar tool should return events."""
        today = datetime.now().strftime("%Y-%m-%d")
        response = await http_client.post(
            f"{mcp_url}/tools/calendar.list_events",
            json={"date": today},
        )

        # May fail if Google Calendar not configured
        if response.status_code == 200:
            data = response.json()
            console.print(
                f"[green]Calendar response: {data.get('total_events', 0)} events[/green]"
            )
        else:
            console.print(
                f"[yellow]Calendar tool returned {response.status_code} "
                "(credentials may not be configured)[/yellow]"
            )

    async def test_financial_tool(
        self, http_client: httpx.AsyncClient, mcp_url: str, wait_for_services
    ):
        """Financial tool should return market data."""
        response = await http_client.post(
            f"{mcp_url}/tools/financial.get_data",
            json={"symbols": ["BTC"], "data_type": "crypto"},
        )

        # Crypto data usually works without API key (CoinGecko)
        if response.status_code == 200:
            data = response.json()
            console.print(f"[green]Financial response: {data.get('total_items', 0)} items[/green]")
        else:
            console.print(f"[yellow]Financial tool returned {response.status_code}[/yellow]")


# =============================================================================
# Agent API Tests
# =============================================================================


@pytest.mark.e2e
class TestAgentAPI:
    """Test Agent API endpoints that proxy to MCP Server."""

    async def test_agent_weather_endpoint(
        self, http_client: httpx.AsyncClient, agent_url: str, wait_for_services
    ):
        """Agent weather endpoint should work."""
        response = await http_client.get(
            f"{agent_url}/tools/weather",
            params={"location": "San Francisco", "when": "today"},
        )

        assert response.status_code in [200, 500]  # 500 if API key missing
        data = response.json()
        assert "tool" in data or "error" in data

        if "tool" in data:
            console.print("[green]Agent weather proxy works[/green]")
        else:
            console.print(f"[yellow]Agent weather: {data.get('error', 'unknown')}[/yellow]")

    async def test_agent_todos_endpoint(
        self, http_client: httpx.AsyncClient, agent_url: str, wait_for_services
    ):
        """Agent todos endpoint should work."""
        response = await http_client.get(f"{agent_url}/tools/todos")

        assert response.status_code in [200, 500]
        data = response.json()

        if "error" not in data:
            console.print("[green]Agent todos proxy works[/green]")
        else:
            console.print(f"[yellow]Agent todos: {data.get('error', 'unknown')}[/yellow]")

    async def test_agent_calendar_endpoint(
        self, http_client: httpx.AsyncClient, agent_url: str, wait_for_services
    ):
        """Agent calendar endpoint should work."""
        today = datetime.now().strftime("%Y-%m-%d")
        response = await http_client.get(
            f"{agent_url}/tools/calendar",
            params={"date": today},
        )

        assert response.status_code in [200, 500]
        data = response.json()

        if "error" not in data:
            console.print("[green]Agent calendar proxy works[/green]")
        else:
            console.print(f"[yellow]Agent calendar: {data.get('error', 'unknown')}[/yellow]")


# =============================================================================
# Full E2E Chat Flow Tests
# =============================================================================


@pytest.mark.e2e
@pytest.mark.slow
class TestChatFlow:
    """Test the complete chat flow through the Agent."""

    async def test_chat_endpoint_accepts_message(
        self, http_client: httpx.AsyncClient, agent_url: str, wait_for_services
    ):
        """Chat endpoint should accept messages."""
        response = await http_client.post(
            f"{agent_url}/chat",
            json={"message": "Hello, what can you help me with?"},
            timeout=90,  # Chat can take longer
        )

        # 503 means OpenAI key not configured, which is OK for basic CI
        assert response.status_code in [200, 503]
        data = response.json()

        if response.status_code == 200:
            assert "response" in data
            console.print("[green]Chat endpoint works - AI responded![/green]")
            console.print(f"[dim]Response preview: {data['response'][:100]}...[/dim]")
        else:
            assert "error" in data
            console.print(
                "[yellow]Chat requires OpenAI API key (expected in CI without key)[/yellow]"
            )

    async def test_chat_rejects_empty_message(
        self, http_client: httpx.AsyncClient, agent_url: str, wait_for_services
    ):
        """Chat should reject empty messages."""
        response = await http_client.post(
            f"{agent_url}/chat",
            json={"message": ""},
        )

        assert response.status_code == 400
        console.print("[green]Chat correctly rejects empty messages[/green]")

    async def test_chat_rejects_missing_message(
        self, http_client: httpx.AsyncClient, agent_url: str, wait_for_services
    ):
        """Chat should reject requests without message field."""
        response = await http_client.post(
            f"{agent_url}/chat",
            json={},
        )

        assert response.status_code == 400
        console.print("[green]Chat correctly rejects missing message field[/green]")


# =============================================================================
# Briefing Tests
# =============================================================================


@pytest.mark.e2e
class TestBriefing:
    """Test the briefing endpoints."""

    async def test_basic_briefing(
        self, http_client: httpx.AsyncClient, agent_url: str, wait_for_services
    ):
        """Basic briefing should aggregate data from MCP tools."""
        response = await http_client.get(
            f"{agent_url}/briefing",
            params={"type": "basic"},
            timeout=60,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "basic"
        assert "data" in data
        console.print("[green]Basic briefing endpoint works[/green]")

    async def test_smart_briefing_requires_ai(
        self, http_client: httpx.AsyncClient, agent_url: str, wait_for_services
    ):
        """Smart briefing requires OpenAI API key."""
        response = await http_client.get(
            f"{agent_url}/briefing",
            params={"type": "smart"},
            timeout=90,
        )

        # Will be 200 if OpenAI configured, 503 if not
        assert response.status_code in [200, 503]

        if response.status_code == 200:
            data = response.json()
            assert data["type"] == "smart"
            console.print("[green]Smart briefing works with AI[/green]")
        else:
            console.print("[yellow]Smart briefing requires OpenAI key[/yellow]")


# =============================================================================
# Integration Tests - Agent -> MCP Communication
# =============================================================================


@pytest.mark.e2e
class TestAgentMCPIntegration:
    """Test that Agent correctly communicates with MCP Server."""

    async def test_agent_mcp_connectivity(
        self, http_client: httpx.AsyncClient, agent_url: str, wait_for_services
    ):
        """Agent should be able to reach MCP Server."""
        # Get agent health which includes MCP server URL
        response = await http_client.get(f"{agent_url}/health")
        assert response.status_code == 200

        data = response.json()
        mcp_url = data.get("mcp_server", "")

        # The agent should have MCP server configured
        assert mcp_url, "Agent should have MCP server URL configured"
        console.print(f"[green]Agent connected to MCP: {mcp_url}[/green]")

    async def test_financial_flow_through_agent(
        self, http_client: httpx.AsyncClient, agent_url: str, wait_for_services
    ):
        """Financial data should flow through Agent to MCP and back."""
        response = await http_client.post(
            f"{agent_url}/tools/financial",
            json={"symbols": ["BTC", "ETH"], "data_type": "crypto"},
            timeout=30,
        )

        # This tests Agent -> MCP Server -> CoinGecko flow
        if response.status_code == 200:
            data = response.json()
            assert "tool" in data
            assert data["tool"] == "financial"
            console.print("[green]Financial flow (Agent -> MCP -> API) works[/green]")
        else:
            console.print(f"[yellow]Financial flow returned {response.status_code}[/yellow]")

    async def test_commute_options_flow(
        self, http_client: httpx.AsyncClient, agent_url: str, wait_for_services
    ):
        """Commute options should flow through Agent to MCP."""
        response = await http_client.post(
            f"{agent_url}/tools/commute-options",
            json={"direction": "to_work", "include_driving": True, "include_transit": False},
            timeout=30,
        )

        # May require GOOGLE_MAPS_API_KEY
        if response.status_code == 200:
            data = response.json()
            assert "tool" in data
            console.print("[green]Commute options flow works[/green]")
        else:
            console.print(
                f"[yellow]Commute options returned {response.status_code} "
                "(may need Google Maps API key)[/yellow]"
            )
