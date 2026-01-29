#!/bin/bash
# =============================================================================
# Make user a superadmin
# =============================================================================
# Usage: ./scripts/make-superadmin.sh [email]
# If no email provided, defaults to n.khromenok@svrd.ru
# =============================================================================

set -e

EMAIL="${1:-n.khromenok@svrd.ru}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}   Make User Superadmin${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""
echo -e "Email: ${GREEN}$EMAIL${NC}"
echo ""

# Detect which compose file is in use
if docker ps --format '{{.Names}}' | grep -q whisperx-api; then
    # Find compose file
    if [ -f "docker/docker-compose.test.yml" ]; then
        COMPOSE_FILE="docker/docker-compose.test.yml"
    elif [ -f "docker/docker-compose.prod.yml" ]; then
        COMPOSE_FILE="docker/docker-compose.prod.yml"
    else
        COMPOSE_FILE="docker/docker-compose.yml"
    fi
else
    echo -e "${RED}ERROR: whisperx-api container not running${NC}"
    exit 1
fi

echo -e "Using compose file: ${COMPOSE_FILE}"
echo ""

# Run SQL to make user superadmin
docker compose -f "$COMPOSE_FILE" exec -T postgres psql -U whisperx -d whisperx <<EOF
UPDATE users 
SET is_superuser = true, 
    role = 'admin' 
WHERE email = '$EMAIL';
EOF

# Verify
echo ""
echo -e "${GREEN}Checking result...${NC}"
docker compose -f "$COMPOSE_FILE" exec -T postgres psql -U whisperx -d whisperx -c \
    "SELECT id, email, full_name, role, is_superuser FROM users WHERE email = '$EMAIL';"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   Done!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "User ${GREEN}$EMAIL${NC} is now a superadmin."
echo -e "Please ${YELLOW}logout and login again${NC} to apply changes."
