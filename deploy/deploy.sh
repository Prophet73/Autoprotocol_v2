#!/bin/bash
#
# Main deployment script for SeverinAutoprotocol
#
# Usage:
#   ./deploy/deploy.sh [--rebuild] [--seed]
#
# Options:
#   --rebuild   Force rebuild Docker images (no cache)
#   --seed      Run seed scripts after deployment
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$PROJECT_ROOT/docker"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Parse arguments
REBUILD=false
RUN_SEED=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --rebuild)
            REBUILD=true
            shift
            ;;
        --seed)
            RUN_SEED=true
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo ""
echo "=============================================="
echo "  SeverinAutoprotocol Deployment"
echo "=============================================="
echo ""

# Check we're in the right directory
if [[ ! -d "$DOCKER_DIR" ]]; then
    log_error "Docker directory not found: $DOCKER_DIR"
    exit 1
fi

cd "$DOCKER_DIR"
log_info "Working directory: $(pwd)"

# Stop existing containers
log_info "Stopping existing containers..."
docker-compose down || true

# Prune anonymous volumes (safe - doesn't touch named volumes like postgres_data)
log_info "Pruning anonymous volumes..."
docker volume prune -f || true

# Build
if [[ "$REBUILD" == "true" ]]; then
    log_info "Rebuilding images (no cache)..."
    docker-compose build --no-cache
else
    log_info "Building images..."
    docker-compose build
fi

# Start containers
log_info "Starting containers..."
docker-compose up -d

# Wait for services to be ready
log_info "Waiting for services to start..."
sleep 10

# Check health
log_info "Checking service health..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    log_info "API is healthy!"
else
    log_warn "API health check failed (may still be starting)"
fi

# Show status
echo ""
log_info "Container status:"
docker-compose ps

# Run seed scripts if requested
if [[ "$RUN_SEED" == "true" ]]; then
    echo ""
    log_info "Running seed scripts..."
    "$SCRIPT_DIR/seed_all.sh"
fi

echo ""
echo "=============================================="
echo "  Deployment Complete!"
echo "=============================================="
echo ""
echo "Services:"
echo "  - API:    http://localhost:8000"
echo "  - Docs:   http://localhost:8000/docs"
echo "  - Flower: http://localhost:5555 (if monitoring enabled)"
echo ""
echo "Logs:"
echo "  docker-compose logs -f worker"
echo "  docker-compose logs -f api"
echo ""
