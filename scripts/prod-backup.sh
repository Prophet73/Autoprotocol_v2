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

# Save Alembic migration version
ALEMBIC_VERSION=$(docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U whisperx -d whisperx -tAc "SELECT version_num FROM alembic_version LIMIT 1" 2>/dev/null || echo "none")
echo -e "${BLUE}Alembic version: ${ALEMBIC_VERSION}${NC}"

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

# Verify backup integrity
echo ""
echo -e "${BLUE}[4/4] Verifying backup integrity...${NC}"
VERIFY_FAILED=false
for gz_file in "$BACKUP_PATH"/*.gz; do
    if gzip -t "$gz_file" 2>/dev/null; then
        echo -e "  ${GREEN}OK:${NC} $(basename "$gz_file")"
    else
        echo -e "  ${RED}FAILED:${NC} $(basename "$gz_file")"
        VERIFY_FAILED=true
    fi
done
if [ "$VERIFY_FAILED" = true ]; then
    echo -e "${RED}WARNING: Some backup files failed integrity check!${NC}"
fi

# Rotate old backups (keep last 10)
KEEP_BACKUPS=${KEEP_BACKUPS:-10}
BACKUP_COUNT=$(ls -1d "$BACKUP_DIR"/backup_* 2>/dev/null | wc -l)
if [ "$BACKUP_COUNT" -gt "$KEEP_BACKUPS" ]; then
    REMOVE_COUNT=$((BACKUP_COUNT - KEEP_BACKUPS))
    echo ""
    echo -e "${BLUE}Rotating backups: removing $REMOVE_COUNT old backup(s) (keeping $KEEP_BACKUPS)${NC}"
    ls -1d "$BACKUP_DIR"/backup_* | head -n "$REMOVE_COUNT" | while read old_backup; do
        rm -rf "$old_backup"
        echo -e "  Removed: $(basename "$old_backup")"
    done
fi

# Calculate sizes
echo ""
echo -e "${BLUE}Backup sizes:${NC}"
du -sh "$BACKUP_PATH"/*

# Create manifest
cat > "$BACKUP_PATH/manifest.json" << EOF
{
    "timestamp": "$TIMESTAMP",
    "date": "$(date -Iseconds)",
    "alembic_version": "$ALEMBIC_VERSION",
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
