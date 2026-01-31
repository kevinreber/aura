# Aura E2E Tests

End-to-end tests for the Aura platform that verify the complete flow:
**UI -> Agent -> MCP Server**

## Overview

These tests verify that all components of the Aura platform work together correctly:

1. **MCP Server** (port 8000) - Provides tools for weather, calendar, todos, etc.
2. **Agent** (port 8001) - AI agent that processes natural language and calls MCP tools
3. **UI** (port 5173) - React frontend that sends prompts to the Agent

## Test Types

### Smoke Tests (`-m smoke`)
- Quick, lightweight tests
- **No API keys required**
- Verify basic service health and connectivity
- Run in ~30 seconds

### E2E Tests (`-m e2e`)
- Comprehensive integration tests
- Test full request flows through all services
- Some tests work without API keys, others need them
- Run in ~2-5 minutes

## Running Tests Locally

### Quick Start (No API Keys)

```bash
# From project root
./e2e/run-e2e.sh
```

This runs smoke tests that verify:
- Services start and respond to health checks
- MCP Server lists available tools
- Agent can communicate with MCP Server
- Input validation works correctly

### Full Tests (With API Keys)

```bash
# Set up your .env file with API keys first
./e2e/run-e2e.sh --full
```

### Manual Docker Commands

```bash
# Build and start services
docker compose -f docker-compose.e2e.yml build
docker compose -f docker-compose.e2e.yml up -d redis server agent

# Run specific tests
docker compose -f docker-compose.e2e.yml run --rm e2e-tests pytest -v -m smoke
docker compose -f docker-compose.e2e.yml run --rm e2e-tests pytest -v -k "test_chat"

# Clean up
docker compose -f docker-compose.e2e.yml down -v
```

## GitHub Actions Workflow

The E2E tests run automatically via GitHub Actions:

### On Every PR/Push:
- **Smoke Tests**: Always run, no secrets needed
- **Build Validation**: Verify all Docker images build successfully

### On Push to Main (or Manual Trigger):
- **Full E2E Tests**: Run with API keys from GitHub Secrets

### Required GitHub Secrets for Full Tests

| Secret | Description | Required for |
|--------|-------------|--------------|
| `OPENAI_API_KEY` | OpenAI API key | Chat/AI features |
| `WEATHER_API_KEY` | OpenWeatherMap API key | Weather tool |
| `GOOGLE_MAPS_API_KEY` | Google Maps API key | Commute tools |
| `TODOIST_API_KEY` | Todoist API key | Todo tool |
| `ALPHA_VANTAGE_API_KEY` | Alpha Vantage API key | Stock data |

### Setting Up Secrets

1. Go to your GitHub repository
2. Navigate to **Settings** -> **Secrets and variables** -> **Actions**
3. Click **New repository secret**
4. Add each required secret

## Test Structure

```
e2e/
├── Dockerfile              # Test runner container
├── pyproject.toml          # Python dependencies
├── run-e2e.sh             # Local test runner script
├── README.md              # This file
└── tests/
    ├── conftest.py        # Fixtures and configuration
    ├── test_smoke.py      # Quick smoke tests
    └── test_e2e_flow.py   # Full E2E tests
```

## Writing New Tests

```python
import pytest
import httpx

@pytest.mark.e2e  # Mark as E2E test
class TestMyFeature:
    async def test_my_feature(
        self,
        http_client: httpx.AsyncClient,
        agent_url: str,
        wait_for_services  # Ensures services are healthy
    ):
        response = await http_client.post(
            f"{agent_url}/chat",
            json={"message": "Hello!"}
        )
        assert response.status_code in [200, 503]  # 503 if no API key
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `E2E_AGENT_URL` | `http://localhost:8001` | Agent service URL |
| `E2E_MCP_SERVER_URL` | `http://localhost:8000` | MCP Server URL |
| `E2E_UI_URL` | `http://localhost:5173` | UI URL |
| `E2E_HEALTH_CHECK_TIMEOUT` | `120` | Seconds to wait for services |
| `E2E_REQUEST_TIMEOUT` | `60` | Request timeout in seconds |

## Troubleshooting

### Services Won't Start
```bash
# Check logs
docker compose -f docker-compose.e2e.yml logs server
docker compose -f docker-compose.e2e.yml logs agent

# Rebuild from scratch
docker compose -f docker-compose.e2e.yml down -v
docker compose -f docker-compose.e2e.yml build --no-cache
```

### Tests Timeout
- Increase `E2E_HEALTH_CHECK_TIMEOUT` for slower machines
- Check if services are actually starting (view logs)

### API Key Issues
- Tests are designed to gracefully handle missing API keys
- Smoke tests work without any keys
- Full tests will skip AI-dependent assertions if keys are missing

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    E2E Test Runner                      │
│                  (pytest + httpx)                       │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP Requests
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│     UI      │  │   Agent     │  │ MCP Server  │
│  (5173)     │──│  (8001)     │──│   (8000)    │
└─────────────┘  └─────────────┘  └──────┬──────┘
                                         │
                                         ▼
                                  ┌─────────────┐
                                  │    Redis    │
                                  │   (6379)    │
                                  └─────────────┘
```
