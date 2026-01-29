#!/bin/bash
# =============================================================================
# WhisperX Test/Staging Deployment (NO GPU)
# =============================================================================
# For testing on servers without GPU
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

COMPOSE_FILE="docker/docker compose.test.yml"
ENV_FILE="docker/.env.production"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   WhisperX TEST Deployment (No GPU)${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check env file
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}ERROR: $ENV_FILE not found!${NC}"
    exit 1
fi

# Check Docker
echo -e "${BLUE}[1/4] Checking Docker...${NC}"
if ! docker --version &> /dev/null; then
    echo -e "${RED}ERROR: Docker not installed${NC}"
    exit 1
fi
echo -e "${GREEN}Docker OK${NC}"

# Stop existing
echo -e "${BLUE}[2/4] Stopping existing containers...${NC}"
docker compose -f "$COMPOSE_FILE" down 2>/dev/null || true

# Build
echo -e "${BLUE}[3/4] Building images...${NC}"
docker compose -f "$COMPOSE_FILE" build

# Start
echo -e "${BLUE}[4/4] Starting services...${NC}"
docker compose -f "$COMPOSE_FILE" up -d

# Wait for health
echo -e "${BLUE}Waiting for services...${NC}"
sleep 10

for i in $(seq 1 30); do
    if curl -sf http://localhost:3001/health > /dev/null 2>&1; then
        echo ""
        echo -e "${GREEN}========================================${NC}"
        echo -e "${GREEN}   Deployment Complete!${NC}"
        echo -e "${GREEN}========================================${NC}"
        echo ""
        echo -e "URLs:"
        echo -e "  Frontend: ${BLUE}https://test1.dev.svrd.ru/${NC}"
        echo -e "  Local:    ${BLUE}http://localhost:3001${NC}"
        echo -e "  API:      ${BLUE}http://localhost:8000/docs${NC}"
        echo ""
        echo -e "Commands:"
        echo -e "  Logs:  docker compose -f $COMPOSE_FILE logs -f"
        echo -e "  Stop:  docker compose -f $COMPOSE_FILE down"
        echo ""
        echo -e "${YELLOW}NOTE: Transcription will be SLOW without GPU!${NC}"
        exit 0
    fi
    echo -n "."
    sleep 2
done

echo ""
echo -e "${RED}Health check failed. Check logs:${NC}"
docker compose -f "$COMPOSE_FILE" logs --tail=50
exit 1
