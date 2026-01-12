#!/bin/bash
# Backup production database and media (no restore, just backup)
# Usage: ./scripts/backup-prod.sh

set -e

# Configuration
SERVER_HOST="${SERVER_HOST:-207.246.125.49}"
SERVER_USER="${SERVER_USER:-root}"
SERVER_PATH="/opt/diveops"
LOCAL_BACKUP_DIR="./backups"

# Colors
GREEN='\033[0;32m'
NC='\033[0m'

mkdir -p "$LOCAL_BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo -e "${GREEN}=== Backing up production ===${NC}"

# Database
echo -e "${GREEN}[1/2] Backing up database...${NC}"
ssh "$SERVER_USER@$SERVER_HOST" "cd $SERVER_PATH && docker compose exec -T db pg_dump -U \$POSTGRES_USER \$POSTGRES_DB" | gzip > "$LOCAL_BACKUP_DIR/db_$TIMESTAMP.sql.gz"
echo "  Saved: $LOCAL_BACKUP_DIR/db_$TIMESTAMP.sql.gz"

# Media (optional - can be large)
read -p "Backup media files too? [y/N]: " backup_media
if [ "$backup_media" = "y" ] || [ "$backup_media" = "Y" ]; then
    echo -e "${GREEN}[2/2] Backing up media files...${NC}"
    rsync -avz --progress "$SERVER_USER@$SERVER_HOST:$SERVER_PATH/media/" "$LOCAL_BACKUP_DIR/media_$TIMESTAMP/"
    echo "  Saved: $LOCAL_BACKUP_DIR/media_$TIMESTAMP/"
else
    echo -e "${GREEN}[2/2] Skipping media backup${NC}"
fi

echo -e "${GREEN}=== Backup complete ===${NC}"
echo ""
echo "Files saved to: $LOCAL_BACKUP_DIR/"
ls -lh "$LOCAL_BACKUP_DIR/" | tail -5
