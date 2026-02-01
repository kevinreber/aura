# Claude Code Features for Aura

Complete overview of all Claude Code customizations for the Aura monorepo.

## 📁 What Was Created

```
.claude/
├── README.md              # Complete documentation
├── QUICKSTART.md          # Quick start guide
├── FEATURES.md            # This file - feature overview
├── config.json            # Project configuration
├── settings.json          # Claude Code settings
├── settings.local.json    # Permission settings (auto-generated)
├── setup.sh              # One-command setup script
├── skills/               # Custom Claude Code skills (8 total)
│   ├── test-all.json
│   ├── health-check.json
│   ├── service-logs.json
│   ├── setup-env.json
│   ├── restart-service.json
│   ├── add-tool.json
│   ├── debug-cache.json
│   └── api-test.json
└── hooks/                # Git hooks for automation (3 total)
    ├── pre-commit.sh
    ├── pre-push.sh
    └── post-merge.sh
```

## 🎯 8 Custom Skills

### 1. `/test-all` - Comprehensive Testing
**When to use**: Before commits, after implementing features

**What it does**:
- Runs server pytest with coverage
- Runs agent pytest with coverage
- Runs UI type checking
- Provides detailed pass/fail summary
- Suggests fixes for failures

**Example**:
```
You: /test-all
Claude: Running all test suites...
  ✅ Server: 45 tests passed (92% coverage)
  ✅ Agent: 23 tests passed (88% coverage)
  ✅ UI: Type check passed
```

---

### 2. `/health-check` - Service Status Dashboard
**When to use**: Start of day, after merges, troubleshooting

**What it does**:
- Checks Docker container status
- Tests server endpoint (port 8000)
- Tests agent endpoint (port 8001)
- Tests UI availability (port 5173)
- Pings Redis
- Shows visual ✅/❌ dashboard

**Example**:
```
You: /health-check
Claude: Service Status:
  ✅ Server  (http://localhost:8000) - Healthy
  ✅ Agent   (http://localhost:8001) - Healthy
  ✅ UI      (http://localhost:5173) - Running
  ✅ Redis   - Responding
```

---

### 3. `/service-logs` - Smart Log Viewer
**When to use**: Debugging errors, monitoring behavior

**What it does**:
- Asks which service to view
- Tails logs with context
- Highlights errors and warnings
- Provides troubleshooting suggestions
- Explains what to look for in each service

**Example**:
```
You: /service-logs
Claude: Which service? (server/agent/ui/redis/all)
You: server
Claude: [Shows last 100 lines of server logs]
  Found 2 errors:
  - Line 45: Cache connection failed
  Suggestion: Check REDIS_URL in .env
```

---

### 4. `/setup-env` - Environment Setup Guide
**When to use**: First time setup, new machine, onboarding

**What it does**:
- Creates .env from template
- Lists all required API keys
- Provides instructions for getting each key
- Checks Docker installation
- Builds and starts containers
- Verifies everything works

**Example**:
```
You: /setup-env
Claude: Setting up Aura environment...

  Required API keys:
  1. OPENAI_API_KEY
     Get it from: https://platform.openai.com
     Required for: AI chat features

  2. WEATHER_API_KEY
     Get it from: https://openweathermap.org
     Required for: Weather forecasts
  ...
```

---

### 5. `/restart-service` - Smart Service Restart
**When to use**: Service unresponsive, config changes

**What it does**:
- Asks which service to restart
- Performs clean restart
- Waits for health checks
- Verifies service responds
- Shows recent logs
- Explains restart vs rebuild

**Example**:
```
You: /restart-service
Claude: Which service? (server/agent/ui/redis/all)
You: server
Claude: Restarting server...
  ✅ Service restarted
  ✅ Health check passed
  Recent logs: [shows last 20 lines]
```

---

### 6. `/add-tool` - Feature Implementation Guide
**When to use**: Adding new features across the stack

**What it does**:
- Guides through full-stack implementation
- Follows architecture: UI → Agent → Server → External API
- Provides code templates
- Ensures patterns are followed
- Helps with testing
- Updates documentation

**Steps**:
1. **Understand**: Asks about requirements
2. **Server**: Schema → Tool → Route → Tests
3. **Agent**: LangChain tool → API endpoint → Tests
4. **UI**: Interface → API client → Component → Widget
5. **Testing**: End-to-end verification
6. **Documentation**: README updates

**Example**:
```
You: /add-tool
Claude: What should this tool do?
You: Get sunrise/sunset times for a location
Claude: Great! Let's implement this step by step...

  Step 1: Server Implementation
  First, create the Pydantic schema...
  [Provides complete implementation guide]
```

---

### 7. `/debug-cache` - Redis Cache Debugger
**When to use**: Stale data, cache misses, performance issues

**What it does**:
- Checks Redis connection
- Inspects cache keys and values
- Shows TTL for cached items
- Analyzes cache hit rates
- Identifies issues
- Suggests TTL adjustments
- Can clear cache if needed

**Example**:
```
You: /debug-cache
Claude: Redis Status:
  ✅ Connected - Memory: 2.4MB / 64MB

  Cache Analysis:
  - weather:* (15 keys, avg TTL: 28min)
  - route:* (8 keys, avg TTL: 14min)
  - geocode:* (42 keys, avg TTL: 6.8 days)

  Cache Hit Rate: 76% (good)
  Recommendation: All TTLs are optimal
```

---

### 8. `/api-test` - Comprehensive API Testing
**When to use**: API changes, integration testing, validation

**What it does**:
- Tests all server endpoints
- Tests all agent endpoints
- Tests UI proxy endpoints
- Checks response schemas
- Measures response times
- Tests error handling
- Formats results as table

**Example**:
```
You: /api-test
Claude: Testing API endpoints...

Server (MCP):
  Endpoint              | Status | Time   | Result
  /health              | 200    | 12ms   | ✅
  /tools/weather       | 200    | 234ms  | ✅
  /tools/calendar      | 200    | 156ms  | ✅

Agent:
  Endpoint              | Status | Time   | Result
  /health              | 200    | 8ms    | ✅
  /chat                | 200    | 1.2s   | ✅
  /tools/weather       | 200    | 245ms  | ✅

All endpoints passed! ✅
```

---

## 🪝 3 Git Hooks

### 1. pre-commit - Code Quality
**Runs**: Before each commit
**Can bypass**: `git commit --no-verify`

**What it checks**:
- **Server**: Black formatting, Flake8 linting, MyPy type checking
- **Agent**: Black formatting, isort imports, MyPy type checking
- **UI**: TypeScript type checking

**Auto-fixes**: Yes - formatting issues are automatically fixed and re-staged

---

### 2. pre-push - Test Suite
**Runs**: Before each push
**Can bypass**: `git push --no-verify`

**What it runs**:
- Server pytest with coverage
- Agent pytest with coverage
- UI type checking

**Prevents**: Pushing broken code

---

### 3. post-merge - Rebuild Detection
**Runs**: After git merge/pull
**Auto-action**: No (just notifies)

**What it checks**:
- Python requirements.txt changes
- pyproject.toml changes
- package.json changes
- Dockerfile changes
- docker-compose.yml changes

**Output**: Notifies if `make build` is needed

---

## 🚀 Setup Instructions

### One-Command Setup

```bash
./.claude/setup.sh
```

This will:
1. Install git hooks (with confirmation)
2. Check for required tools
3. Create .env file (optional)
4. Show available skills
5. Provide next steps

### Manual Setup

```bash
# 1. Setup hooks
ln -sf ../../.claude/hooks/pre-commit.sh .git/hooks/pre-commit
ln -sf ../../.claude/hooks/pre-push.sh .git/hooks/pre-push
ln -sf ../../.claude/hooks/post-merge.sh .git/hooks/post-merge
chmod +x .git/hooks/*

# 2. Create environment
cp .env.example .env
# Edit .env with your API keys

# 3. Start services
make dev
```

---

## 📖 Usage Examples

### Daily Workflow

**Morning routine**:
```
/health-check          # Verify everything is up
/service-logs          # Check for any issues
```

**Starting a feature**:
```
/add-tool             # Get implementation guide
# [Implement the feature]
/test-all             # Verify tests pass
/api-test             # Verify API works
```

**Debugging**:
```
/service-logs         # What's happening?
/debug-cache          # Cache issues?
/health-check         # Service status?
/restart-service      # Try restarting
```

**Before committing**:
```
/test-all             # Run tests manually
git commit            # pre-commit hook runs automatically
git push              # pre-push hook runs automatically
```

### Combining Skills

You can ask Claude to run multiple skills:

```
"First do /health-check, then show me the server logs"
"Run /test-all and then /api-test"
"Do /debug-cache and help me fix the TTL issues"
```

### Context-Aware Usage

Skills understand conversation context:

```
You: I'm getting 500 errors on the weather endpoint
Claude: Let me help debug that...
You: /service-logs
Claude: [Shows server logs and filters for weather-related errors]
```

---

## 🎓 Learning Path

### For New Users

1. **Start here**: `.claude/QUICKSTART.md`
2. **Try skills**: `/health-check`, `/service-logs`, `/test-all`
3. **Read**: `.claude/README.md` for detailed docs
4. **Understand architecture**: `CLAUDE.md`

### For Active Development

1. **Use `/add-tool`** when adding features
2. **Use `/test-all`** before commits
3. **Use `/health-check`** when something breaks
4. **Use `/debug-cache`** for caching issues

### For Advanced Users

1. Create custom skills in `.claude/skills/`
2. Modify hooks in `.claude/hooks/`
3. Share your improvements with the team

---

## 🔧 Customization

### Adding New Skills

1. Create `.claude/skills/my-skill.json`
2. Define name, description, instructions
3. Use `/my-skill` to invoke

### Modifying Hooks

Edit scripts in `.claude/hooks/`:
- `pre-commit.sh` - Add more linters
- `pre-push.sh` - Add more tests
- `post-merge.sh` - Add more checks

### Adjusting Permissions

Edit `.claude/settings.local.json` to allow/deny specific commands.

---

## 📊 Skill Usage Statistics

Recommended usage frequency:

| Skill | Frequency |
|-------|-----------|
| `/health-check` | Daily, after merges |
| `/service-logs` | When debugging |
| `/test-all` | Before each commit |
| `/api-test` | After API changes |
| `/debug-cache` | When cache issues |
| `/restart-service` | As needed |
| `/add-tool` | Per new feature |
| `/setup-env` | Once per machine |

---

## 🆘 Troubleshooting

### Skills Not Working

- Ensure you're using `/skill-name` format
- Check `.claude/skills/` directory exists
- Verify JSON syntax in skill files

### Hooks Not Running

- Run `./.claude/setup.sh` again
- Check symlinks: `ls -la .git/hooks/`
- Ensure scripts are executable: `chmod +x .claude/hooks/*.sh`

### Services Won't Start

```
/health-check         # Diagnose the issue
/service-logs         # Check error logs
make down && make build && make dev  # Full rebuild
```

---

## 📚 Documentation Index

| Document | Purpose |
|----------|---------|
| `.claude/README.md` | Complete skill & hook documentation |
| `.claude/QUICKSTART.md` | Quick start guide |
| `.claude/FEATURES.md` | This file - feature overview |
| `CLAUDE.md` | Architectural guide |
| `packages/*/CLAUDE.md` | Package-specific guides |

---

## 🎯 Quick Reference

**Most useful commands**:
```
/health-check    # Is everything working?
/test-all       # Did I break anything?
/service-logs   # What's happening?
/add-tool       # How do I add a feature?
```

**Most useful hooks**:
- pre-commit: Keeps code quality high
- pre-push: Prevents pushing broken code
- post-merge: Reminds to rebuild

**Setup**:
```bash
./.claude/setup.sh
```

---

Happy coding with Claude! 🚀
