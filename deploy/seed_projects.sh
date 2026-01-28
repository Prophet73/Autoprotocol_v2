#!/bin/bash
#
# Seed projects from Excel file
#
# Usage:
#   ./deploy/seed_projects.sh [--dry-run] [--file path/to/file.xls]
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Find Python
if [[ -f /.dockerenv ]]; then
    PYTHON="python"
elif [[ -f "$PROJECT_ROOT/venv310/bin/python" ]]; then
    PYTHON="$PROJECT_ROOT/venv310/bin/python"
elif [[ -f "$PROJECT_ROOT/venv310/Scripts/python.exe" ]]; then
    PYTHON="$PROJECT_ROOT/venv310/Scripts/python.exe"
else
    PYTHON="python"
fi

exec $PYTHON deploy/scripts/seed_projects.py "$@"
