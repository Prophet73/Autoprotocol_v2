#!/bin/bash
# =============================================================================
# WhisperX Production Backup Script
# =============================================================================
# Backs up PostgreSQL database and important volumes
#
# Usage:
#   ./scripts/prod-backup.sh                    # Backup to ./backups/
#   ./scripts/prod-backup.sh /path/to/backup    # Backup to specific path
# =============================================================================

set -e

COMPOSE_FILE="docker/docker-compose.prod.yml"
BACKUP_DIR="${1:-./backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   WhisperX Backup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Create backup directory
mkdir -p "$BACKUP_DIR"
BACKUP_PATH="$BACKUP_DIR/backup_$TIMESTAMP"
mkdir -p "$BACKUP_PATH"

echo -e "${BLUE}Backup location: $BACKUP_PATH${NC}"
echo ""

# Backup PostgreSQL
echo -e "${BLUE}[1/3] Backing up PostgreSQL...${NC}"
docker-compose -f "$COMPOSE_FILE" exec -T postgres pg_dump -U whisperx whisperx > "$BACKUP_PATH/database.sql"
gzip "$BACKUP_PATH/database.sql"
echo -e "${GREEN}Database backup: $BACKUP_PATH/database.sql.gz${NC}"

# Backup uploads volume
echo -e "${BLUE}[2/3] Backing up uploads...${NC}"
docker run --rm \
    -v whisperx_uploads:/data \
    -v "$(pwd)/$BACKUP_PATH":/backup \
    alpine tar czf /backup/uploads.tar.gz -C /data .
echo -e "${GREEN}Uploads backup: $BACKUP_PATH/uploads.tar.gz${NC}"

# Backup output volume
echo -e "${BLUE}[3/3] Backing up outputs...${NC}"
docker run --rm \
    -v whisperx_output:/data \
    -v "$(pwd)/$BACKUP_PATH":/backup \
    alpine tar czf /backup/output.tar.gz -C /data .
echo -e "${GREEN}Output backup: $BACKUP_PATH/output.tar.gz${NC}"

# Calculate sizes
echo ""
echo -e "${BLUE}Backup sizes:${NC}"
du -sh "$BACKUP_PATH"/*

# Create manifest
cat > "$BACKUP_PATH/manifest.json" << EOF
{
    "timestamp": "$TIMESTAMP",
    "date": "$(date -Iseconds)",
    "files": {
        "database": "database.sql.gz",
        "uploads": "uploads.tar.gz",
        "output": "output.tar.gz"
    }
}
EOF

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   Backup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Backup location: ${BLUE}$BACKUP_PATH${NC}"
echo ""
echo -e "To restore:"
echo -e "  1. Database: gunzip -c database.sql.gz | docker-compose exec -T postgres psql -U whisperx whisperx"
echo -e "  2. Uploads:  docker run --rm -v whisperx_uploads:/data -v \$(pwd):/backup alpine tar xzf /backup/uploads.tar.gz -C /data"
echo -e "  3. Output:   docker run --rm -v whisperx_output:/data -v \$(pwd):/backup alpine tar xzf /backup/output.tar.gz -C /data"
