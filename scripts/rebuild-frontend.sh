#!/bin/bash
# =============================================================================
# Quick Frontend Rebuild
# =============================================================================
# Rebuilds only the frontend container (faster than full redeploy)
# =============================================================================

COMPOSE_FILE="docker/docker-compose.prod.yml"

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Rebuilding frontend...${NC}"

# Build frontend only
docker-compose -f "$COMPOSE_FILE" build --no-cache frontend

# Restart frontend
docker-compose -f "$COMPOSE_FILE" up -d --force-recreate frontend

# Wait for health
echo -n "Waiting for frontend..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:3001/health > /dev/null 2>&1; then
        echo ""
        echo -e "${GREEN}Frontend rebuilt and running!${NC}"
        exit 0
    fi
    echo -n "."
    sleep 2
done

echo ""
echo -e "${RED}Frontend health check failed${NC}"
docker-compose -f "$COMPOSE_FILE" logs --tail=20 frontend
exit 1
