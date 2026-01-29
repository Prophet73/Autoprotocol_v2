#!/bin/bash
# =============================================================================
# WhisperX Production Status Check
# =============================================================================
# Quick overview of all services and their health
# =============================================================================

COMPOSE_FILE="docker/docker-compose.prod.yml"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   WhisperX Production Status${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Container status
echo -e "${BLUE}Container Status:${NC}"
docker-compose -f "$COMPOSE_FILE" ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || \
    docker-compose -f "$COMPOSE_FILE" ps

echo ""

# Health checks
echo -e "${BLUE}Health Checks:${NC}"

check_health() {
    local name=$1
    local url=$2
    if curl -sf "$url" > /dev/null 2>&1; then
        echo -e "  $name: ${GREEN}Healthy${NC}"
    else
        echo -e "  $name: ${RED}Unhealthy${NC}"
    fi
}

check_health "Frontend" "http://localhost:3001/health"
check_health "API" "http://localhost:3001/api/health"

echo ""

# Resource usage
echo -e "${BLUE}Resource Usage:${NC}"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" 2>/dev/null | head -10

echo ""

# GPU status
echo -e "${BLUE}GPU Status:${NC}"
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.total --format=csv,noheader 2>/dev/null || echo "  GPU info unavailable"
else
    echo "  nvidia-smi not found"
fi

echo ""

# Recent logs (last 5 lines per service)
echo -e "${BLUE}Recent Errors (if any):${NC}"
docker-compose -f "$COMPOSE_FILE" logs --tail=50 2>/dev/null | grep -i "error\|exception\|failed" | tail -10 || echo "  No recent errors"

echo ""
echo -e "${BLUE}========================================${NC}"
