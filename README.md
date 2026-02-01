# Aura

Unified monorepo for the Aura productivity platform.

## Quick Start

    cp .env.example .env
    # Edit .env with your API keys
    make dev

## 🤖 Claude Code Integration

This project includes custom Claude Code skills and hooks for enhanced development:

```bash
# Setup Claude Code features
./.claude/setup.sh
```

**Available Skills**: `/health-check`, `/test-all`, `/service-logs`, `/add-tool`, and more
**Documentation**: See [.claude/README.md](.claude/README.md) and [.claude/QUICKSTART.md](.claude/QUICKSTART.md)

## Services

| Service | URL | Description |
|---------|-----|-------------|
| UI | http://localhost:5173 | React frontend |
| Agent | http://localhost:8001 | LangChain AI agent |
| Server | http://localhost:8000 | MCP Server API |

## Production URLs (Render)

| Service | URL |
|---------|-----|
| Agent | https://aura-agent-yz8u.onrender.com |
| MCP Server | https://aura-server-sxxd.onrender.com |

## Commands

    make dev    # Start all services
    make down   # Stop all services
    make logs   # View logs
    make build  # Rebuild images

## Packages

- packages/server - MCP Server (Python/Flask)
- packages/agent - AI Agent (Python/LangChain)
- packages/ui - Web UI (React/TypeScript)

## Documentation

- **CLAUDE.md** - Architecture guide for AI assistants
- **.claude/README.md** - Custom Claude Code skills and hooks
- **.claude/QUICKSTART.md** - Quick start guide for Claude Code
- **packages/*/README.md** - Package-specific documentation
