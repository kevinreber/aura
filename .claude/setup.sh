#!/bin/bash
# Setup script for Claude Code features

set -e

echo "🚀 Setting up Claude Code features for Aura..."
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: Please run this script from the Aura monorepo root"
    exit 1
fi

# Setup git hooks
echo "${BLUE}📎 Setting up Git hooks...${NC}"

HOOKS_DIR=".claude/hooks"
GIT_HOOKS_DIR=".git/hooks"

# Make sure hooks are executable
chmod +x $HOOKS_DIR/*.sh

# Create symlinks for hooks
for hook in pre-commit pre-push post-merge; do
    SOURCE="../../$HOOKS_DIR/$hook.sh"
    TARGET="$GIT_HOOKS_DIR/$hook"

    if [ -L "$TARGET" ]; then
        echo "  ⚠️  Hook $hook already exists (symlink)"
        read -p "  Replace it? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm "$TARGET"
            ln -s "$SOURCE" "$TARGET"
            echo "  ✅ Replaced $hook hook"
        fi
    elif [ -f "$TARGET" ]; then
        echo "  ⚠️  Hook $hook already exists (file)"
        read -p "  Replace it? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm "$TARGET"
            ln -s "$SOURCE" "$TARGET"
            echo "  ✅ Replaced $hook hook"
        fi
    else
        ln -s "$SOURCE" "$TARGET"
        echo "  ✅ Created $hook hook"
    fi
done

echo ""
echo "${BLUE}📚 Installed Git Hooks:${NC}"
echo "  • pre-commit  - Runs linters/formatters, then checks for doc drift"
echo "  • pre-push    - Runs tests before push"
echo "  • post-merge  - Notifies if rebuild needed after merge"
echo ""
echo "${BLUE}🤖 Doc-drift hook:${NC}"
echo "  When pre-commit detects code touching MCP tools, agent endpoints,"
echo "  UI routes, or env vars without matching doc updates, it can invoke"
echo "  Claude headlessly to refresh affected READMEs and re-stage them."
echo ""
echo "  Tunable env vars:"
echo "    AURA_SKIP_DOC_CHECK=1            opt out entirely"
echo "    AURA_DOC_CHECK_MODE=warn         print drift report only (no AI call)"
echo "    AURA_DOC_CHECK_MODE=update       default — invoke Claude outside a session"
echo "    AURA_DOC_CHECK_MODE=block        refuse commit on drift"
echo ""

# Check for required tools
echo "${BLUE}🔍 Checking for required tools...${NC}"

MISSING_TOOLS=()

if ! command -v docker &> /dev/null; then
    MISSING_TOOLS+=("docker")
fi

if ! command -v uv &> /dev/null; then
    MISSING_TOOLS+=("uv (Python package manager)")
fi

if ! command -v npm &> /dev/null; then
    MISSING_TOOLS+=("npm")
fi

if [ ${#MISSING_TOOLS[@]} -eq 0 ]; then
    echo "  ✅ All required tools installed"
else
    echo "  ⚠️  Missing tools:"
    for tool in "${MISSING_TOOLS[@]}"; do
        echo "    - $tool"
    done
    echo ""
    echo "  Please install missing tools before continuing."
fi

echo ""

# List available skills
echo "${BLUE}✨ Available Claude Code Skills:${NC}"
echo "  • /test-all        - Run all test suites"
echo "  • /health-check    - Check service health"
echo "  • /service-logs    - View service logs"
echo "  • /restart-service - Restart a service"
echo "  • /setup-env       - Setup environment"
echo "  • /add-tool        - Add new feature guide"
echo "  • /debug-cache     - Debug Redis cache"
echo "  • /api-test        - Test all API endpoints"
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "${YELLOW}⚠️  No .env file found${NC}"
    read -p "Create .env from template? (Y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        cp .env.example .env
        echo "  ✅ Created .env file"
        echo "  📝 Please edit .env and add your API keys"
    fi
    echo ""
fi

# Summary
echo "${GREEN}✅ Setup complete!${NC}"
echo ""
echo "${BLUE}Next steps:${NC}"
echo "  1. Edit .env file with your API keys"
echo "  2. Run: make dev"
echo "  3. In Claude Code, try: /health-check"
echo ""
echo "${BLUE}Documentation:${NC}"
echo "  • Claude skills: .claude/README.md"
echo "  • Project guide: CLAUDE.md"
echo "  • Main README:   README.md"
echo ""
echo "Happy coding with Claude! 🚀"
