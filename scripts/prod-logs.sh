#!/bin/bash
# =============================================================================
# WhisperX Production Logs Viewer
# =============================================================================
# Quick access to service logs
#
# Usage:
#   ./scripts/prod-logs.sh              # All services
#   ./scripts/prod-logs.sh api          # API only
#   ./scripts/prod-logs.sh worker-gpu   # GPU worker only
#   ./scripts/prod-logs.sh -f           # Follow all logs
# =============================================================================

COMPOSE_FILE="docker/docker-compose.prod.yml"

# Default to all services
SERVICE=""
FOLLOW=""
TAIL="100"

for arg in "$@"; do
    case $arg in
        -f|--follow)
            FOLLOW="-f"
            ;;
        -n|--lines)
            shift
            TAIL="$1"
            ;;
        api|frontend|worker-gpu|worker-llm|redis|postgres|flower)
            SERVICE="$arg"
            ;;
        --help)
            echo "Usage: ./scripts/prod-logs.sh [SERVICE] [OPTIONS]"
            echo ""
            echo "Services:"
            echo "  api         API server logs"
            echo "  frontend    Frontend (nginx) logs"
            echo "  worker-gpu  GPU worker logs (transcription)"
            echo "  worker-llm  LLM worker logs (Gemini)"
            echo "  redis       Redis logs"
            echo "  postgres    PostgreSQL logs"
            echo "  flower      Flower monitoring logs"
            echo ""
            echo "Options:"
            echo "  -f, --follow    Follow log output"
            echo "  -n, --lines N   Number of lines to show (default: 100)"
            echo ""
            exit 0
            ;;
    esac
done

docker-compose -f "$COMPOSE_FILE" logs --tail="$TAIL" $FOLLOW $SERVICE
