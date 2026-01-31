#!/bin/bash
# Setup script to install git hooks for the project

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
HOOKS_DIR="$PROJECT_ROOT/.git/hooks"

echo "Setting up git hooks..."

# Create hooks directory if it doesn't exist
mkdir -p "$HOOKS_DIR"

# Install pre-push hook
if [ -f "$SCRIPT_DIR/pre-push" ]; then
    cp "$SCRIPT_DIR/pre-push" "$HOOKS_DIR/pre-push"
    chmod +x "$HOOKS_DIR/pre-push"
    echo "Installed pre-push hook"
fi

echo ""
echo "Git hooks installed successfully!"
echo ""
echo "The following hooks are now active:"
echo "  - pre-push: Runs tests before allowing git push"
echo ""
echo "To skip hooks temporarily, use: git push --no-verify"
