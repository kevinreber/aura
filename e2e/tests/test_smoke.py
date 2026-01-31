"""
Smoke Tests for Aura Platform

Quick, lightweight tests that verify basic functionality without
requiring external API keys. These run fast and are suitable for
CI/CD pipelines.
"""

import pytest
import httpx


@pytest.mark.smoke
class TestSmoke:
    """Quick smoke tests for basic service functionality."""

    async def test_mcp_server_responds(
        self, http_client: httpx.AsyncClient, mcp_url: str, wait_for_services
    ):
        """MCP Server should respond to basic requests."""
        response = await http_client.get(f"{mcp_url}/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    async def test_agent_responds(
        self, http_client: httpx.AsyncClient, agent_url: str, wait_for_services
    ):
        """Agent should respond to basic requests."""
        response = await http_client.get(f"{agent_url}/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    async def test_mcp_tools_endpoint(
        self, http_client: httpx.AsyncClient, mcp_url: str, wait_for_services
    ):
        """MCP Server tools endpoint should work."""
        response = await http_client.get(f"{mcp_url}/tools")
        assert response.status_code == 200
        data = response.json()
        assert "tools" in data
        assert len(data["tools"]) > 0

    async def test_agent_tools_endpoint(
        self, http_client: httpx.AsyncClient, agent_url: str, wait_for_services
    ):
        """Agent tools endpoint should work."""
        response = await http_client.get(f"{agent_url}/tools")
        assert response.status_code == 200
        data = response.json()
        assert "tools" in data

    async def test_agent_version_endpoint(
        self, http_client: httpx.AsyncClient, agent_url: str, wait_for_services
    ):
        """Agent version endpoint should work."""
        response = await http_client.get(f"{agent_url}/version")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "name" in data

    async def test_chat_validation(
        self, http_client: httpx.AsyncClient, agent_url: str, wait_for_services
    ):
        """Chat endpoint should validate input properly."""
        # Test empty message
        response = await http_client.post(f"{agent_url}/chat", json={"message": ""})
        assert response.status_code == 400

        # Test missing message
        response = await http_client.post(f"{agent_url}/chat", json={})
        assert response.status_code == 400

        # Test whitespace-only message
        response = await http_client.post(f"{agent_url}/chat", json={"message": "   "})
        assert response.status_code == 400

    async def test_mcp_server_invalid_tool(
        self, http_client: httpx.AsyncClient, mcp_url: str, wait_for_services
    ):
        """MCP Server should handle invalid tool requests."""
        response = await http_client.post(
            f"{mcp_url}/tools/nonexistent.tool",
            json={},
        )
        assert response.status_code == 404

    async def test_agent_cors_headers(
        self, http_client: httpx.AsyncClient, agent_url: str, wait_for_services
    ):
        """Agent should include proper headers."""
        response = await http_client.get(f"{agent_url}/health")
        assert response.status_code == 200
        # Response should be JSON
        assert "application/json" in response.headers.get("content-type", "")
