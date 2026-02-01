# Claude Code Configuration

This directory contains custom skills, hooks, and configurations for Claude Code to help with the Aura monorepo development.

## Custom Skills

Skills are invoked using `/skill-name` in Claude Code conversations.

### Development & Testing

#### `/test-all`
Run test suites for all three packages (server, agent, UI) and provide a comprehensive summary.

**Usage**: Simply type `/test-all` to run all tests and get results.

**What it does**:
- Runs server pytest with coverage
- Runs agent pytest with coverage
- Runs UI type checking
- Provides detailed failure analysis and suggestions

---

#### `/health-check`
Check the health status of all running services.

**Usage**: `/health-check` to verify all services are up and running.

**What it checks**:
- Docker container status
- Server health endpoint (port 8000)
- Agent health endpoint (port 8001)
- UI availability (port 5173)
- Redis connectivity

**Output**: Visual dashboard with ✅/❌ for each service plus troubleshooting tips.

---

#### `/api-test`
Test API endpoints across all services with curl commands.

**Usage**: `/api-test` to run comprehensive API tests.

**What it tests**:
- All server MCP tool endpoints
- All agent API endpoints
- UI proxy endpoints
- Response schemas and timing
- Error handling

**Output**: Formatted table with status codes, response times, and pass/fail results.

---

### Service Management

#### `/service-logs`
View logs for specific services or all services.

**Usage**: `/service-logs` (Claude will ask which service) or tell Claude directly "show me agent logs"

**Services**: server, agent, ui, redis, or all

**Features**:
- Contextual log interpretation
- Error detection and diagnosis
- Helpful hints about what to look for

---

#### `/restart-service`
Restart a specific service or all services.

**Usage**: `/restart-service` (Claude will ask which service)

**What it does**:
- Restarts specified Docker service
- Waits for health checks
- Verifies service is responsive
- Shows recent logs
- Explains when to restart vs rebuild

---

### Development Workflows

#### `/setup-env`
Set up the development environment from scratch.

**Usage**: `/setup-env` for first-time setup or after cloning.

**What it does**:
- Creates .env file from template
- Lists all required API keys with instructions
- Checks Docker installation
- Builds containers
- Starts all services
- Verifies setup with health checks

---

#### `/add-tool`
Guide for adding a new tool/feature across the full stack.

**Usage**: `/add-tool` when adding a new feature.

**What it guides you through**:
1. Server: Schema, tool implementation, routes, tests
2. Agent: LangChain tool wrapper, API endpoints
3. UI: Components, API client, widgets
4. Testing: End-to-end verification
5. Documentation: README and CLAUDE.md updates

**Benefits**: Ensures you follow architectural patterns and don't miss any steps.

---

### Debugging

#### `/debug-cache`
Debug Redis cache issues and inspect cached data.

**Usage**: `/debug-cache` when experiencing caching issues.

**Capabilities**:
- Check Redis connection and memory
- Inspect cache contents and TTLs
- Diagnose common cache issues
- Test cache read/write operations
- Performance analysis and recommendations

**Common scenarios**:
- Stale data not updating
- Cache misses when hits expected
- Memory usage issues
- TTL adjustments

---

## Hooks

Hooks are shell scripts that automatically run at specific events. They're located in `.claude/hooks/`.

### Available Hooks

#### `pre-commit.sh`
Runs before each commit to ensure code quality.

**What it checks**:
- **Server**: Black formatting, Flake8 linting, MyPy type checking
- **Agent**: Black formatting, isort imports, MyPy type checking
- **UI**: TypeScript type checking

**Auto-fixes**: Formatting issues are automatically fixed and re-staged.

**Bypass**: If needed, use `git commit --no-verify` (not recommended).

---

#### `pre-push.sh`
Runs before pushing to ensure tests pass.

**What it runs**:
- Server test suite with coverage
- Agent test suite with coverage
- UI type checking

**Prevents**: Pushing broken code that would fail CI/CD.

**Bypass**: Use `git push --no-verify` (not recommended).

---

#### `post-merge.sh`
Runs after merging/pulling to detect if rebuild is needed.

**What it checks**:
- Python requirements files (server & agent)
- package.json changes (UI)
- Dockerfile modifications
- docker-compose.yml changes

**Output**: Notifies if `make build` is needed.

---

## Enabling Hooks

To enable these hooks in your local repository:

```bash
# Option 1: Symlink to git hooks
ln -sf ../../.claude/hooks/pre-commit.sh .git/hooks/pre-commit
ln -sf ../../.claude/hooks/pre-push.sh .git/hooks/pre-push
ln -sf ../../.claude/hooks/post-merge.sh .git/hooks/post-merge

# Option 2: Copy to git hooks
cp .claude/hooks/pre-commit.sh .git/hooks/pre-commit
cp .claude/hooks/pre-push.sh .git/hooks/pre-push
cp .claude/hooks/post-merge.sh .git/hooks/post-merge

# Make sure they're executable
chmod +x .git/hooks/pre-commit
chmod +x .git/hooks/pre-push
chmod +x .git/hooks/post-merge
```

**Note**: Git hooks are not tracked in the repository, so each developer needs to set them up locally.

---

## Quick Reference

### Most Common Commands

```
/health-check          # Is everything running?
/test-all             # Run all tests
/service-logs         # What's happening in the logs?
/restart-service      # Restart a service
/api-test            # Test all API endpoints
/debug-cache         # Cache not working?
```

### Workflow Examples

**Starting a new day**:
```
/health-check         # Make sure everything is up
/service-logs         # Check for any overnight issues
```

**Adding a feature**:
```
/add-tool            # Follow the guided workflow
/test-all            # Verify tests pass
/api-test            # Test the new endpoints
```

**Debugging issues**:
```
/service-logs        # See what's failing
/debug-cache         # If it's cache-related
/health-check        # Verify service status
/restart-service     # Try restarting
```

**Before pushing code**:
```
/test-all            # Run all tests
/api-test            # Verify API contracts
# Commit (pre-commit hook runs automatically)
# Push (pre-push hook runs automatically)
```

---

## Customizing Skills

Skills are defined in JSON format in `.claude/skills/`. To create a new skill:

```json
{
  "name": "my-skill",
  "description": "Brief description of what this skill does",
  "instructions": "Detailed instructions for Claude to follow..."
}
```

Then use `/my-skill` to invoke it.

---

## Tips

1. **Skills vs Commands**: Skills guide Claude through complex multi-step workflows. For simple one-off commands, just ask Claude directly.

2. **Hooks are Local**: Git hooks need to be set up on each developer's machine. Share this README with your team.

3. **Customize**: Feel free to modify skills and hooks to match your workflow.

4. **Combine Skills**: You can ask Claude to run multiple skills in sequence: "First do /health-check, then /service-logs for the server"

5. **Context Matters**: Skills have access to the conversation context, so you can say "add a weather caching feature" and then `/add-tool` will use that context.

---

## Contributing New Skills

When adding a new skill:

1. Create a JSON file in `.claude/skills/`
2. Give it a clear, descriptive name
3. Write detailed instructions that Claude can follow
4. Include examples and expected outputs
5. Test it thoroughly
6. Document it here in this README

---

## Support

For issues or suggestions about these Claude Code configurations:

1. Check the main [CLAUDE.md](../CLAUDE.md) for architectural guidance
2. Review package-specific CLAUDE.md files in each package
3. Open an issue in the repository

---

**Happy coding with Claude! 🚀**
