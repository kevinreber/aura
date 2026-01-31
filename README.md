# Aura

Unified monorepo for the Aura productivity platform.

## Quick Start

    cp .env.example .env
    # Edit .env with your API keys
    make dev

## Services

| Service | URL | Description |
|---------|-----|-------------|
| UI | http://localhost:5173 | React frontend |
| Agent | http://localhost:8001 | LangChain AI agent |
| Server | http://localhost:8000 | MCP Server API |

## Commands

    make dev    # Start all services
    make down   # Stop all services
    make logs   # View logs
    make build  # Rebuild images

## Packages

- packages/server - MCP Server (Python/Flask)
- packages/agent - AI Agent (Python/LangChain)
- packages/ui - Web UI (React/TypeScript)
