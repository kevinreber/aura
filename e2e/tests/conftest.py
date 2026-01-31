"""
E2E Test Configuration and Fixtures

This module provides fixtures for end-to-end testing of the Aura platform,
testing the complete flow: UI -> Agent -> MCP Server
"""

import os
import asyncio
import time
from typing import Generator, AsyncGenerator

import pytest
import httpx
from rich.console import Console

console = Console()

# Service URLs from environment or defaults
UI_URL = os.getenv("E2E_UI_URL", "http://localhost:5173")
AGENT_URL = os.getenv("E2E_AGENT_URL", "http://localhost:8001")
MCP_SERVER_URL = os.getenv("E2E_MCP_SERVER_URL", "http://localhost:8000")

# Timeouts
HEALTH_CHECK_TIMEOUT = int(os.getenv("E2E_HEALTH_CHECK_TIMEOUT", "120"))
REQUEST_TIMEOUT = int(os.getenv("E2E_REQUEST_TIMEOUT", "60"))


class ServiceHealth:
    """Track health status of all services."""

    def __init__(self):
        self.ui_healthy = False
        self.agent_healthy = False
        self.mcp_server_healthy = False
        self.redis_healthy = False

    @property
    def all_healthy(self) -> bool:
        return self.agent_healthy and self.mcp_server_healthy

    @property
    def full_stack_healthy(self) -> bool:
        return self.ui_healthy and self.agent_healthy and self.mcp_server_healthy


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def service_urls() -> dict:
    """Get service URLs from environment."""
    return {
        "ui": UI_URL,
        "agent": AGENT_URL,
        "mcp_server": MCP_SERVER_URL,
    }


@pytest.fixture(scope="session")
async def http_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create an async HTTP client for the test session."""
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        yield client


@pytest.fixture(scope="session")
async def wait_for_services(http_client: httpx.AsyncClient, service_urls: dict) -> ServiceHealth:
    """Wait for all services to be healthy before running tests."""
    health = ServiceHealth()
    start_time = time.time()

    console.print("\n[bold blue]Waiting for services to be ready...[/bold blue]")

    while time.time() - start_time < HEALTH_CHECK_TIMEOUT:
        # Check MCP Server
        if not health.mcp_server_healthy:
            try:
                response = await http_client.get(f"{service_urls['mcp_server']}/health")
                if response.status_code == 200:
                    health.mcp_server_healthy = True
                    console.print("[green]  MCP Server is healthy[/green]")
            except Exception:
                pass

        # Check Agent
        if not health.agent_healthy:
            try:
                response = await http_client.get(f"{service_urls['agent']}/health")
                if response.status_code == 200:
                    health.agent_healthy = True
                    console.print("[green]  Agent is healthy[/green]")
            except Exception:
                pass

        # Check UI (optional - may not be running in all test modes)
        if not health.ui_healthy:
            try:
                response = await http_client.get(f"{service_urls['ui']}/api/v1/health")
                if response.status_code == 200:
                    health.ui_healthy = True
                    console.print("[green]  UI is healthy[/green]")
            except Exception:
                pass

        if health.all_healthy:
            console.print("[bold green]All core services are ready![/bold green]\n")
            return health

        await asyncio.sleep(2)

    # Report what's missing
    console.print("[bold red]Service health check failed:[/bold red]")
    if not health.mcp_server_healthy:
        console.print("[red]  - MCP Server not responding[/red]")
    if not health.agent_healthy:
        console.print("[red]  - Agent not responding[/red]")
    if not health.ui_healthy:
        console.print("[yellow]  - UI not responding (optional)[/yellow]")

    if not health.all_healthy:
        pytest.fail("Required services (Agent, MCP Server) are not healthy")

    return health


@pytest.fixture
async def mcp_client(http_client: httpx.AsyncClient, service_urls: dict) -> httpx.AsyncClient:
    """Get a client configured for MCP Server requests."""
    return http_client


@pytest.fixture
async def agent_client(http_client: httpx.AsyncClient, service_urls: dict) -> httpx.AsyncClient:
    """Get a client configured for Agent requests."""
    return http_client


@pytest.fixture
def mcp_url(service_urls: dict) -> str:
    """Get MCP Server URL."""
    return service_urls["mcp_server"]


@pytest.fixture
def agent_url(service_urls: dict) -> str:
    """Get Agent URL."""
    return service_urls["agent"]


@pytest.fixture
def ui_url(service_urls: dict) -> str:
    """Get UI URL."""
    return service_urls["ui"]
