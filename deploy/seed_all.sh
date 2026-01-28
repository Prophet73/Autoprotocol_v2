#!/bin/bash
#
# Run all seed scripts for production database
#
# Usage:
#   ./deploy/seed_all.sh [--dry-run]
#
# This script runs inside the Docker container to seed the database.
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Parse arguments
DRY_RUN=""
if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN="--dry-run"
    log_warn "DRY RUN MODE - No changes will be made"
fi

echo ""
echo "=============================================="
echo "  Database Seeding"
echo "=============================================="
echo ""

cd "$PROJECT_ROOT"

# Check if running in Docker or locally
if [[ -f /.dockerenv ]]; then
    log_info "Running inside Docker container"
    PYTHON="python"
else
    log_info "Running locally"
    # Try to find Python in venv or system
    if [[ -f "$PROJECT_ROOT/venv310/bin/python" ]]; then
        PYTHON="$PROJECT_ROOT/venv310/bin/python"
    elif [[ -f "$PROJECT_ROOT/venv310/Scripts/python.exe" ]]; then
        PYTHON="$PROJECT_ROOT/venv310/Scripts/python.exe"
    else
        PYTHON="python"
    fi
fi

log_info "Using Python: $PYTHON"

# 1. Seed SVRD tenant and users (if not exists)
log_info "Step 1: Seeding SVRD tenant and users..."
$PYTHON scripts/seed_svrd_data.py $DRY_RUN || log_warn "seed_svrd_data.py failed (may already exist)"

# 2. Seed projects from Excel
if [[ -f "$PROJECT_ROOT/deploy/data/projects.xls" ]] || [[ -f "$PROJECT_ROOT/список проектов.xls" ]]; then
    log_info "Step 2: Seeding projects from Excel..."
    $PYTHON deploy/scripts/seed_projects.py $DRY_RUN
else
    log_warn "Step 2: Skipped - No projects Excel file found"
    log_warn "       Expected: deploy/data/projects.xls"
fi

echo ""
echo "=============================================="
echo "  Seeding Complete!"
echo "=============================================="
echo ""
