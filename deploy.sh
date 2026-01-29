#!/bin/bash
# =============================================================================
# WhisperX Production Deployment Script
# =============================================================================
# Usage:
#   ./deploy.sh              # Full deployment
#   ./deploy.sh --rebuild    # Rebuild without cache
#   ./deploy.sh --logs       # Show logs after deploy
#   ./deploy.sh --seed       # Run seed scripts after deploy
#   ./deploy.sh --monitoring # Include Flower monitoring
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker/docker-compose.prod.yml"
ENV_FILE="docker/.env.production"
HEALTH_URL="http://localhost:3001/health"
API_HEALTH_URL="http://localhost:8000/health"

# Parse arguments
REBUILD=false
SHOW_LOGS=false
RUN_SEED=false
MONITORING=false

for arg in "$@"; do
    case $arg in
        --rebuild)
            REBUILD=true
            shift
            ;;
        --logs)
            SHOW_LOGS=true
            shift
            ;;
        --seed)
            RUN_SEED=true
            shift
            ;;
        --monitoring)
            MONITORING=true
            shift
            ;;
        --help)
            echo "Usage: ./deploy.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --rebuild     Rebuild images without cache"
            echo "  --logs        Show logs after deployment"
            echo "  --seed        Run database seed scripts"
            echo "  --monitoring  Enable Flower monitoring"
            echo "  --help        Show this help"
            exit 0
            ;;
    esac
done

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   WhisperX Production Deployment${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if .env.production exists
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}ERROR: $ENV_FILE not found!${NC}"
    echo -e "${YELLOW}Copy docker/.env.production.example to docker/.env.production and configure it.${NC}"
    exit 1
fi

# Check required env vars
echo -e "${BLUE}[1/6] Checking configuration...${NC}"
source "$ENV_FILE"

if [ -z "$HUGGINGFACE_TOKEN" ] || [ "$HUGGINGFACE_TOKEN" = "hf_your_token_here" ]; then
    echo -e "${RED}ERROR: HUGGINGFACE_TOKEN not configured in $ENV_FILE${NC}"
    exit 1
fi

if [ -z "$GEMINI_API_KEY" ] || [ "$GEMINI_API_KEY" = "your_gemini_api_key_here" ]; then
    echo -e "${RED}ERROR: GEMINI_API_KEY not configured in $ENV_FILE${NC}"
    exit 1
fi

if [ "$SECRET_KEY" = "CHANGE_ME_generate_with_python_secrets" ]; then
    echo -e "${RED}ERROR: SECRET_KEY not changed in $ENV_FILE${NC}"
    echo -e "${YELLOW}Generate with: python -c \"import secrets; print(secrets.token_urlsafe(32))\"${NC}"
    exit 1
fi

echo -e "${GREEN}Configuration OK${NC}"

# Check Docker
echo -e "${BLUE}[2/6] Checking Docker...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}ERROR: Docker not found${NC}"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo -e "${RED}ERROR: Docker daemon not running${NC}"
    exit 1
fi

# Check NVIDIA Docker
if ! docker run --rm --gpus all nvidia/cuda:12.1-base nvidia-smi &> /dev/null; then
    echo -e "${YELLOW}WARNING: NVIDIA Docker runtime not available or no GPU found${NC}"
    echo -e "${YELLOW}Transcription will fail without GPU!${NC}"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo -e "${GREEN}NVIDIA Docker OK${NC}"
fi

# Stop existing containers
echo -e "${BLUE}[3/6] Stopping existing containers...${NC}"
docker-compose -f "$COMPOSE_FILE" down 2>/dev/null || true

# Clean anonymous volumes (but NOT named volumes with data!)
echo -e "${BLUE}[4/6] Cleaning anonymous volumes...${NC}"
docker volume prune -f 2>/dev/null || true

# Build images
echo -e "${BLUE}[5/6] Building images...${NC}"
BUILD_ARGS=""
if [ "$REBUILD" = true ]; then
    BUILD_ARGS="--no-cache"
    echo -e "${YELLOW}Rebuilding without cache (this may take a while)...${NC}"
fi

PROFILE_ARGS=""
if [ "$MONITORING" = true ]; then
    PROFILE_ARGS="--profile monitoring"
fi

docker-compose -f "$COMPOSE_FILE" build $BUILD_ARGS

# Start services
echo -e "${BLUE}[6/6] Starting services...${NC}"
docker-compose -f "$COMPOSE_FILE" $PROFILE_ARGS up -d

# Wait for services to be healthy
echo -e "${BLUE}Waiting for services to be healthy...${NC}"
echo -n "Checking "

MAX_RETRIES=60
RETRY_INTERVAL=5

for i in $(seq 1 $MAX_RETRIES); do
    echo -n "."

    # Check frontend health
    if curl -sf "$HEALTH_URL" > /dev/null 2>&1; then
        echo ""
        echo -e "${GREEN}Frontend is healthy!${NC}"
        break
    fi

    if [ $i -eq $MAX_RETRIES ]; then
        echo ""
        echo -e "${RED}Timeout waiting for services to be healthy${NC}"
        echo -e "${YELLOW}Check logs with: docker-compose -f $COMPOSE_FILE logs${NC}"
        exit 1
    fi

    sleep $RETRY_INTERVAL
done

# Run seed if requested
if [ "$RUN_SEED" = true ]; then
    echo -e "${BLUE}Running seed scripts...${NC}"
    if [ -f "deploy/seed_all.sh" ]; then
        bash deploy/seed_all.sh
    else
        echo -e "${YELLOW}Seed script not found, skipping...${NC}"
    fi
fi

# Show status
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Services:"
docker-compose -f "$COMPOSE_FILE" ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
echo ""
echo -e "URLs:"
echo -e "  Frontend: ${BLUE}https://test1.dev.svrd.ru/${NC}"
echo -e "  Local:    ${BLUE}http://localhost:3001${NC}"
if [ "$MONITORING" = true ]; then
    echo -e "  Flower:   ${BLUE}http://localhost:5555${NC}"
fi
echo ""
echo -e "Commands:"
echo -e "  Logs:     docker-compose -f $COMPOSE_FILE logs -f"
echo -e "  Stop:     docker-compose -f $COMPOSE_FILE down"
echo -e "  Restart:  docker-compose -f $COMPOSE_FILE restart"
echo ""

# Show logs if requested
if [ "$SHOW_LOGS" = true ]; then
    echo -e "${BLUE}Showing logs (Ctrl+C to exit)...${NC}"
    docker-compose -f "$COMPOSE_FILE" logs -f
fi
