#!/bin/bash
# Push database and media from local to production server
# Usage: ./scripts/push-data.sh
#
# WARNING: This OVERWRITES production data!

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

echo -e "${RED}=== WARNING: This will OVERWRITE production data! ===${NC}"
echo ""
read -p "Are you sure? Type 'yes' to continue: " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 1
fi

mkdir -p "$LOCAL_BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 1. Backup production first (safety)
echo -e "${GREEN}[1/5] Backing up production database first...${NC}"
ssh "$SERVER_USER@$SERVER_HOST" "cd $SERVER_PATH && docker compose exec -T db pg_dump -U \$POSTGRES_USER \$POSTGRES_DB" > "$LOCAL_BACKUP_DIR/prod_backup_$TIMESTAMP.sql"
echo "  Saved to: $LOCAL_BACKUP_DIR/prod_backup_$TIMESTAMP.sql"

# 2. Dump local database
echo -e "${GREEN}[2/5] Dumping local database...${NC}"
docker compose exec -T db pg_dump -U diveops diveops > "$LOCAL_BACKUP_DIR/local_$TIMESTAMP.sql"

# 3. Push database to server
echo -e "${GREEN}[3/5] Pushing database to server...${NC}"
ssh "$SERVER_USER@$SERVER_HOST" "cd $SERVER_PATH && docker compose exec -T db psql -U \$POSTGRES_USER -d \$POSTGRES_DB -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'"
cat "$LOCAL_BACKUP_DIR/local_$TIMESTAMP.sql" | ssh "$SERVER_USER@$SERVER_HOST" "cd $SERVER_PATH && docker compose exec -T db psql -U \$POSTGRES_USER \$POSTGRES_DB"

# 4. Sync media files to server
echo -e "${GREEN}[4/5] Syncing media files to server...${NC}"
rsync -avz --progress ./media/ "$SERVER_USER@$SERVER_HOST:$SERVER_PATH/media/"

# 5. Restart server containers
echo -e "${GREEN}[5/5] Restarting server containers...${NC}"
ssh "$SERVER_USER@$SERVER_HOST" "cd $SERVER_PATH && docker compose restart web"

echo -e "${GREEN}=== Done! ===${NC}"
echo ""
echo "Production backup saved to: $LOCAL_BACKUP_DIR/prod_backup_$TIMESTAMP.sql"
echo "If something went wrong, restore with:"
echo "  cat $LOCAL_BACKUP_DIR/prod_backup_$TIMESTAMP.sql | ssh $SERVER_USER@$SERVER_HOST 'cd $SERVER_PATH && docker compose exec -T db psql -U \$POSTGRES_USER \$POSTGRES_DB'"
