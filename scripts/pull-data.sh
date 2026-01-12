#!/bin/bash
# Pull database and media from production server to local
# Usage: ./scripts/pull-data.sh

set -e

# Configuration - update these
SERVER_HOST="${SERVER_HOST:-207.246.125.49}"
SERVER_USER="${SERVER_USER:-root}"
SERVER_PATH="/opt/diveops"
LOCAL_BACKUP_DIR="./backups"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}=== Pulling data from production ===${NC}"

# Create backup directory
mkdir -p "$LOCAL_BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 0. Backup local database FIRST (safety before overwriting)
echo -e "${GREEN}[0/5] Backing up LOCAL database before overwriting...${NC}"
docker compose exec -T db pg_dump -U diveops diveops 2>/dev/null | gzip > "$LOCAL_BACKUP_DIR/local_before_pull_$TIMESTAMP.sql.gz" || {
    echo -e "${YELLOW}  No local database running, skipping local backup${NC}"
}
echo "  Saved: $LOCAL_BACKUP_DIR/local_before_pull_$TIMESTAMP.sql.gz"

# 1. Dump database on server
echo -e "${GREEN}[1/5] Dumping database on server...${NC}"
ssh "$SERVER_USER@$SERVER_HOST" "cd $SERVER_PATH && docker compose exec -T db pg_dump -U \$POSTGRES_USER \$POSTGRES_DB" > "$LOCAL_BACKUP_DIR/db_$TIMESTAMP.sql"

echo -e "${GREEN}[2/5] Database dumped to $LOCAL_BACKUP_DIR/db_$TIMESTAMP.sql${NC}"

# 2. Sync media files
echo -e "${GREEN}[3/5] Syncing media files (rsync)...${NC}"
mkdir -p ./media
rsync -avz --progress "$SERVER_USER@$SERVER_HOST:$SERVER_PATH/media/" ./media/

# 3. Restore database locally
echo -e "${GREEN}[4/5] Restoring database locally...${NC}"
docker compose exec -T db psql -U diveops -d diveops < "$LOCAL_BACKUP_DIR/db_$TIMESTAMP.sql" 2>/dev/null || {
    echo -e "${YELLOW}Note: Some errors during restore are normal (existing objects)${NC}"
}

echo -e "${GREEN}[5/5] Complete!${NC}"
echo ""
echo -e "${GREEN}=== Done! ===${NC}"
echo ""
echo "Backups saved:"
echo "  Local (before pull): $LOCAL_BACKUP_DIR/local_before_pull_$TIMESTAMP.sql.gz"
echo "  Production dump:     $LOCAL_BACKUP_DIR/db_$TIMESTAMP.sql"
echo ""
echo "Media files synced to: ./media/"
echo ""
echo -e "${YELLOW}Restart your local containers to see changes:${NC}"
echo "  docker compose down && docker compose up -d"
echo ""
echo "To restore your local database to before the pull:"
echo "  gunzip -c $LOCAL_BACKUP_DIR/local_before_pull_$TIMESTAMP.sql.gz | docker compose exec -T db psql -U diveops diveops"
