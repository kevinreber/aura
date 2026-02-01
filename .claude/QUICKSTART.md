# Claude Code Quick Start for Aura

Get up and running with Claude Code in the Aura monorepo in 5 minutes.

## Initial Setup

```bash
# 1. Run the setup script
./.claude/setup.sh

# 2. Edit your environment file
nano .env  # or use your preferred editor

# 3. Start all services
make dev
```

## Verify Installation

In Claude Code, try these commands:

```
/health-check
```

You should see all services marked with ✅.

## Your First Feature

Let's add a simple feature end-to-end:

```
/add-tool
```

Then tell Claude: "I want to add a simple ping tool that just returns 'pong'"

Claude will guide you through:
1. Creating the server endpoint
2. Adding the agent tool
3. Creating the UI component
4. Testing everything

## Common Workflows

### Morning Routine

```
/health-check          # All services up?
/service-logs          # Any errors overnight?
```

### Before Starting Work

```
/health-check          # Services running?
```

If services are down:
```bash
make dev
```

### While Developing

Working on the server:
```
/service-logs
# Tell Claude: "show server logs"
```

Need to restart after changes:
```
/restart-service
# Tell Claude: "restart server"
```

### Before Committing

The pre-commit hook will automatically:
- Format your code
- Run linters
- Type check

Just commit normally:
```bash
git add .
git commit -m "Your message"
# Hook runs automatically
```

### Before Pushing

The pre-push hook will automatically:
- Run all test suites
- Type check UI

Just push normally:
```bash
git push
# Hook runs automatically
```

To run tests manually first:
```
/test-all
```

### Debugging Issues

Service not responding:
```
/health-check
/service-logs
/restart-service
```

Cache issues:
```
/debug-cache
```

API not working:
```
/api-test
```

## Skill Cheat Sheet

| Skill | When to Use |
|-------|-------------|
| `/health-check` | Start of day, after merge, service down |
| `/test-all` | Before committing, after feature |
| `/service-logs` | Debugging errors, checking behavior |
| `/restart-service` | Service unresponsive, config change |
| `/api-test` | API changes, integration testing |
| `/debug-cache` | Cache not working, stale data |
| `/add-tool` | Adding new feature |
| `/setup-env` | First time setup, new machine |

## Tips

1. **Ask Claude directly**: For simple tasks, just ask Claude. Skills are for complex workflows.

2. **Combine skills**: "First `/health-check`, then show me the server logs"

3. **Context awareness**: Skills understand your conversation context

4. **Skip hooks**: Use `--no-verify` if you really need to skip a hook (not recommended)

5. **Check docs**: See `.claude/README.md` for detailed skill documentation

## Troubleshooting

### Hooks not running

```bash
# Re-run setup
./.claude/setup.sh
```

### Services won't start

```bash
# Check Docker
docker ps

# Rebuild everything
make clean
make build
make dev
```

### Skills not working

Make sure you're using `/skill-name` format with the leading slash.

## Learning More

- **Skills**: `.claude/README.md` - Detailed skill documentation
- **Architecture**: `CLAUDE.md` - Monorepo structure and patterns
- **Server**: `packages/server/CLAUDE.md` - MCP server specifics
- **Agent**: `packages/agent/CLAUDE.md` - AI agent specifics
- **UI**: `packages/ui/CLAUDE.md` - Frontend specifics

## Example Session

Here's a typical development session with Claude Code:

```
You: /health-check
Claude: ✅ All services running! Server (8000), Agent (8001), UI (5173)

You: I want to add a new tool that gets sunrise/sunset times
Claude: Great! Let me guide you through adding this feature. First...

[Claude guides through implementation using /add-tool workflow]

You: /test-all
Claude: Running tests...
  ✅ Server tests: 45 passed
  ✅ Agent tests: 23 passed
  ✅ UI type check: passed

You: Let me commit this
[You run git commit, pre-commit hook runs automatically]

You: /api-test
Claude: Testing all endpoints...
  ✅ Server health: 200 (12ms)
  ✅ Weather tool: 200 (234ms)
  ✅ New sunrise tool: 200 (156ms)
  ...

You: Perfect! Looks good
```

## Next Steps

1. Try `/health-check` to verify your setup
2. Run `/add-tool` to practice adding a feature
3. Explore the other skills in `.claude/README.md`
4. Read `CLAUDE.md` for architectural understanding

Happy coding! 🚀
