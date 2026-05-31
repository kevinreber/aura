#!/bin/bash
# Pre-commit hook: Run linters and formatters on changed files

set -e

echo "🔍 Running pre-commit checks..."

# Get list of changed Python files in server package
SERVER_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep "^packages/server/.*\.py$" || true)
if [ -n "$SERVER_FILES" ]; then
    echo "📦 Checking server package..."
    cd packages/server

    # Format with black
    echo "  🎨 Running black..."
    uv run black $SERVER_FILES || exit 1

    # Lint with flake8
    echo "  🔍 Running flake8..."
    uv run flake8 $SERVER_FILES || exit 1

    # Type check with mypy
    echo "  🔬 Running mypy..."
    uv run mypy $SERVER_FILES || exit 1

    cd ../..

    # Re-stage formatted files
    git add $SERVER_FILES
fi

# Get list of changed Python files in agent package
AGENT_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep "^packages/agent/.*\.py$" || true)
if [ -n "$AGENT_FILES" ]; then
    echo "📦 Checking agent package..."
    cd packages/agent

    # Format with black
    echo "  🎨 Running black..."
    uv run black $AGENT_FILES || exit 1

    # Lint with isort
    echo "  📚 Running isort..."
    uv run isort $AGENT_FILES || exit 1

    # Type check with mypy
    echo "  🔬 Running mypy..."
    uv run mypy $AGENT_FILES || exit 1

    cd ../..

    # Re-stage formatted files
    git add $AGENT_FILES
fi

# Get list of changed TypeScript files in UI package
UI_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep "^packages/ui/.*\.\(ts\|tsx\)$" || true)
if [ -n "$UI_FILES" ]; then
    echo "📦 Checking UI package..."
    cd packages/ui

    # Type check
    echo "  🔬 Running type check..."
    npm run typecheck || exit 1

    cd ../..
fi

echo "✅ Pre-commit checks passed!"

# ─── Doc-drift check ───────────────────────────────────────────────────
# Detects when staged code touches user-facing surfaces (MCP tools,
# agent endpoints, UI routes, env vars) without updating the matching
# README/CLAUDE.md. Defaults to AI-driven refresh outside a Claude
# session; warn-only inside one. Tunable via env vars — see the
# script's header.
HOOK_DIR="$(dirname "$0")"
DRIFT_SCRIPT="$HOOK_DIR/check-docs-drift.sh"

# Resolve symlinks so this works whether the hook is invoked via
# .git/hooks/pre-commit (symlink) or directly.
if [ -L "$0" ]; then
    REAL_HOOK="$(readlink "$0")"
    case "$REAL_HOOK" in
        /*) DRIFT_SCRIPT="$(dirname "$REAL_HOOK")/check-docs-drift.sh" ;;
        *)  DRIFT_SCRIPT="$(dirname "$0")/$REAL_HOOK"
            DRIFT_SCRIPT="$(dirname "$DRIFT_SCRIPT")/check-docs-drift.sh" ;;
    esac
fi

if [ -x "$DRIFT_SCRIPT" ]; then
    "$DRIFT_SCRIPT"
fi
