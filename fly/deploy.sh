#!/usr/bin/env bash
set -euo pipefail

# Deploy Aura services to Fly.io
# Usage:
#   ./fly/deploy.sh              # Deploy all services
#   ./fly/deploy.sh server       # Deploy server only
#   ./fly/deploy.sh agent        # Deploy agent only
#   ./fly/deploy.sh ui           # Deploy UI only

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

deploy_service() {
    local service=$1
    local config="$SCRIPT_DIR/${service}.toml"
    local dockerfile="docker/${service}.Dockerfile"

    if [ ! -f "$config" ]; then
        echo "Error: Config not found: $config"
        exit 1
    fi

    echo "==> Deploying $service..."
    cd "$ROOT_DIR"

    if [ "$service" = "ui" ]; then
        # VITE_ vars must be set at build time (Vite inlines them)
        local agent_url="${VITE_AI_AGENT_API_URL:-https://aura-agent.fly.dev}"
        fly deploy \
            --config "$config" \
            --dockerfile "$dockerfile" \
            --build-target production \
            --build-arg "VITE_AI_AGENT_API_URL=$agent_url"
    else
        fly deploy \
            --config "$config" \
            --dockerfile "$dockerfile" \
            --build-target production
    fi

    echo "==> $service deployed successfully"
}

# First-time setup helper
setup_service() {
    local service=$1
    local app_name="aura-${service}"

    echo "==> Creating app: $app_name"
    fly apps create "$app_name" --org personal 2>/dev/null || echo "    App $app_name already exists"
}

if [ "${1:-}" = "setup" ]; then
    echo "Setting up Fly.io apps..."
    setup_service server
    setup_service agent
    setup_service ui
    echo ""
    echo "Apps created. Now set your secrets:"
    echo ""
    echo "  # Server secrets (use your Upstash Redis URL)"
    echo "  fly secrets set -a aura-server \\"
    echo "    REDIS_URL=<your-upstash-redis-url> \\"
    echo "    WEATHER_API_KEY=<key> \\"
    echo "    GOOGLE_MAPS_API_KEY=<key> \\"
    echo "    TODOIST_API_KEY=<key> \\"
    echo "    ALPHA_VANTAGE_API_KEY=<key> \\"
    echo "    HOME_ADDRESS=<address> \\"
    echo "    WORK_ADDRESS=<address>"
    echo ""
    echo "  # Agent secrets"
    echo "  fly secrets set -a aura-agent \\"
    echo "    MCP_SERVER_URL=https://aura-server.fly.dev \\"
    echo "    OPENAI_API_KEY=<key> \\"
    echo "    ALLOWED_ORIGINS=https://aura-ui.fly.dev"
    echo ""
    echo "  # UI: VITE_ vars are build-time only (set via --build-arg in deploy)."
    echo "  # To customize the agent URL for UI builds, export before deploying:"
    echo "  #   export VITE_AI_AGENT_API_URL=https://aura-agent.fly.dev"
    echo "  #   ./fly/deploy.sh ui"
    echo ""
    echo "Then deploy with: ./fly/deploy.sh"
    exit 0
fi

TARGET="${1:-all}"

case "$TARGET" in
    server) deploy_service server ;;
    agent)  deploy_service agent ;;
    ui)     deploy_service ui ;;
    all)
        deploy_service server
        deploy_service agent
        echo ""
        echo "Server + Agent deployed."
        echo "UI is on Vercel — skip UI deploy unless you want to move it to Fly."
        echo "To deploy UI too: ./fly/deploy.sh ui"
        ;;
    *)
        echo "Usage: $0 [setup|server|agent|ui|all]"
        exit 1
        ;;
esac
