#!/bin/bash
# Post-merge hook: Rebuild containers if dependencies changed

set -e

echo "🔄 Checking if rebuild needed after merge..."

# Check if any dependency files changed
CHANGED_FILES=$(git diff-tree -r --name-only --no-commit-id ORIG_HEAD HEAD)

NEEDS_REBUILD=false

# Check server dependencies
if echo "$CHANGED_FILES" | grep -q "^packages/server/requirements"; then
    echo "  📦 Server dependencies changed"
    NEEDS_REBUILD=true
fi

# Check agent dependencies
if echo "$CHANGED_FILES" | grep -q "^packages/agent/pyproject.toml\|^packages/agent/requirements"; then
    echo "  📦 Agent dependencies changed"
    NEEDS_REBUILD=true
fi

# Check UI dependencies
if echo "$CHANGED_FILES" | grep -q "^packages/ui/package"; then
    echo "  📦 UI dependencies changed"
    NEEDS_REBUILD=true
fi

# Check Dockerfiles
if echo "$CHANGED_FILES" | grep -q "Dockerfile\|docker-compose.yml"; then
    echo "  🐳 Docker configuration changed"
    NEEDS_REBUILD=true
fi

if [ "$NEEDS_REBUILD" = true ]; then
    echo "🔨 Dependencies or Docker config changed. Rebuilding containers..."
    echo "   Run: make build && make down && make dev"
else
    echo "✅ No rebuild needed"
fi
