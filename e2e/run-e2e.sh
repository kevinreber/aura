#!/bin/bash
#
# E2E Test Runner Script
#
# Usage:
#   ./e2e/run-e2e.sh           # Run smoke tests (no API keys needed)
#   ./e2e/run-e2e.sh --full    # Run full E2E tests (needs API keys)
#   ./e2e/run-e2e.sh --clean   # Clean up containers and volumes
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Parse arguments
RUN_FULL=false
CLEAN_ONLY=false
SHOW_LOGS=false

for arg in "$@"; do
    case $arg in
        --full)
            RUN_FULL=true
            shift
            ;;
        --clean)
            CLEAN_ONLY=true
            shift
            ;;
        --logs)
            SHOW_LOGS=true
            shift
            ;;
        --help|-h)
            echo "E2E Test Runner"
            echo ""
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --full    Run full E2E tests (requires API keys in .env)"
            echo "  --clean   Clean up containers and volumes only"
            echo "  --logs    Show service logs after tests"
            echo "  --help    Show this help message"
            exit 0
            ;;
    esac
done

# Clean up function
cleanup() {
    log_info "Cleaning up containers..."
    docker compose -f docker-compose.e2e.yml down -v 2>/dev/null || true
}

# Handle clean-only mode
if [ "$CLEAN_ONLY" = true ]; then
    cleanup
    log_success "Cleanup complete!"
    exit 0
fi

# Trap for cleanup on exit
trap cleanup EXIT

log_info "Starting E2E test environment..."

# Build containers
log_info "Building Docker images..."
docker compose -f docker-compose.e2e.yml build

# Start services
log_info "Starting services..."
docker compose -f docker-compose.e2e.yml up -d redis server agent

# Wait for services to be healthy
log_info "Waiting for services to be healthy..."
TIMEOUT=120
ELAPSED=0
while [ $ELAPSED -lt $TIMEOUT ]; do
    if docker compose -f docker-compose.e2e.yml ps | grep -q "healthy"; then
        SERVER_HEALTH=$(docker compose -f docker-compose.e2e.yml ps server --format json 2>/dev/null | grep -o '"Health":"[^"]*"' | head -1 || echo "")
        AGENT_HEALTH=$(docker compose -f docker-compose.e2e.yml ps agent --format json 2>/dev/null | grep -o '"Health":"[^"]*"' | head -1 || echo "")

        if [[ "$SERVER_HEALTH" == *"healthy"* ]] && [[ "$AGENT_HEALTH" == *"healthy"* ]]; then
            break
        fi
    fi
    sleep 5
    ELAPSED=$((ELAPSED + 5))
    echo -n "."
done
echo ""

if [ $ELAPSED -ge $TIMEOUT ]; then
    log_error "Services failed to become healthy within ${TIMEOUT}s"
    docker compose -f docker-compose.e2e.yml ps
    docker compose -f docker-compose.e2e.yml logs --tail=50
    exit 1
fi

log_success "Services are healthy!"
docker compose -f docker-compose.e2e.yml ps

# Run tests
if [ "$RUN_FULL" = true ]; then
    log_info "Running full E2E tests..."
    TEST_MARKER="e2e or smoke"
else
    log_info "Running smoke tests..."
    TEST_MARKER="smoke"
fi

# Run the tests
docker compose -f docker-compose.e2e.yml run --rm e2e-tests \
    pytest -v --tb=short -m "$TEST_MARKER"

TEST_EXIT_CODE=$?

# Show logs if requested or on failure
if [ "$SHOW_LOGS" = true ] || [ $TEST_EXIT_CODE -ne 0 ]; then
    log_info "Service logs:"
    echo ""
    echo "=== Server Logs ==="
    docker compose -f docker-compose.e2e.yml logs server --tail=50
    echo ""
    echo "=== Agent Logs ==="
    docker compose -f docker-compose.e2e.yml logs agent --tail=50
fi

if [ $TEST_EXIT_CODE -eq 0 ]; then
    log_success "All tests passed!"
else
    log_error "Some tests failed!"
fi

exit $TEST_EXIT_CODE
