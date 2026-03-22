#!/bin/bash
set -euo pipefail

# Aura - Deploy/Update Script
# Run from the project root on the Droplet

COMPOSE_FILE="docker-compose.prod.yml"

echo "==> Pulling latest changes..."
git pull origin main 2>/dev/null || echo "Skipping git pull (not a git repo or no remote)"

echo "==> Building production images..."
docker compose -f "$COMPOSE_FILE" build

echo "==> Starting services..."
docker compose -f "$COMPOSE_FILE" up -d

echo "==> Waiting for services to be healthy..."
sleep 5

echo "==> Service status:"
docker compose -f "$COMPOSE_FILE" ps

echo ""
echo "==> Health checks:"
for service in server agent ui; do
    status=$(docker compose -f "$COMPOSE_FILE" ps --format json "$service" 2>/dev/null | grep -o '"Health":"[^"]*"' | head -1 || echo "unknown")
    echo "  $service: $status"
done

echo ""
echo "==> Deploy complete!"
