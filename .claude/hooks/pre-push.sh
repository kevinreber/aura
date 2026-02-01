#!/bin/bash
# Pre-push hook: Run test suites before pushing

set -e

echo "🧪 Running test suites before push..."

# Server tests
echo "📦 Testing server package..."
cd packages/server
if ! uv run pytest --cov=mcp_server -q; then
    echo "❌ Server tests failed!"
    exit 1
fi
cd ../..

# Agent tests
echo "📦 Testing agent package..."
cd packages/agent
if ! uv run pytest --cov=daily_ai_agent -q; then
    echo "❌ Agent tests failed!"
    exit 1
fi
cd ../..

# UI type checking (faster than full tests)
echo "📦 Type checking UI package..."
cd packages/ui
if ! npm run typecheck; then
    echo "❌ UI type check failed!"
    exit 1
fi
cd ../..

echo "✅ All tests passed! Proceeding with push..."
