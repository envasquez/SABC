#!/usr/bin/bash
# Production deployment script with database migrations

set -e  # Exit on any error

echo "🚀 Starting deployment..."

# Backup database before anything else
BACKUP_DIR="$HOME/backups"
BACKUP_FILE="$BACKUP_DIR/sabc_$(date +%Y%m%d_%H%M%S).sql.gz"
mkdir -p "$BACKUP_DIR"

echo "💾 Backing up database..."
if docker compose -f docker-compose.prod.yml exec -T postgres pg_dump -U sabc_user sabc | gzip > "$BACKUP_FILE"; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "✅ Backup saved: $BACKUP_FILE ($BACKUP_SIZE)"
else
    echo "❌ Backup failed! Aborting deployment."
    exit 1
fi

# Keep only last 10 backups
ls -t "$BACKUP_DIR"/sabc_*.sql.gz 2>/dev/null | tail -n +11 | xargs -r rm
echo "🗂️  Retained $(ls "$BACKUP_DIR"/sabc_*.sql.gz 2>/dev/null | wc -l) backups"

# Stop containers
echo "⏹️  Stopping containers..."
docker compose -f docker-compose.prod.yml down

# Pull latest code
echo "📥 Pulling latest code..."
git pull

# Rebuild containers
echo "🔨 Building containers..."
docker compose -f docker-compose.prod.yml build --no-cache

# Start containers
echo "▶️  Starting containers..."
docker compose -f docker-compose.prod.yml up -d

# Wait for database to be ready
echo "⏳ Waiting for database..."
sleep 10

# Run database migrations
echo "📦 Running database migrations..."
docker compose -f docker-compose.prod.yml exec -T web alembic upgrade head

# Check migration status
echo "📊 Current migration version:"
docker compose -f docker-compose.prod.yml exec -T web alembic current

# Cleanup
echo "🧹 Cleaning up..."
docker system prune -f
sudo journalctl --vacuum-time=7d
sudo apt clean

echo ""
echo "✅ Deployment complete!"
echo "🌐 Application: https://saustinbc.com"
echo "📊 Check logs: docker compose -f docker-compose.prod.yml logs -f web"

# To restore a backup ...
# gunzip -c ~/backups/sabc_XXXXXXXX_XXXXXX.sql.gz | docker compose -f docker-compose.prod.yml exec -T postgres psql -U sabc_user sabc