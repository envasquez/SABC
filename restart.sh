#!/usr/bin/bash
# Production deployment script with database migrations.
# Rollback procedure: see docs/RUNBOOK.md

set -euo pipefail

COMPOSE="docker compose -f docker-compose.prod.yml"
HEALTH_URL="${HEALTH_URL:-http://localhost/health}"

echo "🚀 Starting deployment..."

# 1. Pull the latest code FIRST. This is read-only and atomic — if it fails
#    (rebase conflict, network blip, GitHub outage), we abort before touching
#    the running site. The previous order (down → pull) meant a failed pull
#    left the site down with no easy recovery.
echo "📥 Pulling latest code..."
git pull

# 2. Back up the running database before any state-mutating step.
BACKUP_DIR="$HOME/backups"
BACKUP_FILE="$BACKUP_DIR/sabc_$(date +%Y%m%d_%H%M%S).sql.gz"
mkdir -p "$BACKUP_DIR"

echo "💾 Backing up database..."
if $COMPOSE exec -T postgres pg_dump -U sabc_user sabc | gzip > "$BACKUP_FILE"; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "✅ Backup saved: $BACKUP_FILE ($BACKUP_SIZE)"
else
    echo "❌ Backup failed! Aborting deployment."
    exit 1
fi

# Keep only last 10 backups
ls -t "$BACKUP_DIR"/sabc_*.sql.gz 2>/dev/null | tail -n +11 | xargs -r rm
echo "🗂️  Retained $(ls "$BACKUP_DIR"/sabc_*.sql.gz 2>/dev/null | wc -l) backups"

# 3. Tag the currently running image as :prev so a failed deploy can be rolled
#    back with `docker tag sabc-web:prev sabc-web:latest && $COMPOSE up -d`.
#    Safe on first deploy: the tag command no-ops if :latest doesn't exist.
echo "🏷️  Tagging current image for rollback..."
docker tag sabc-web:latest sabc-web:prev 2>/dev/null || echo "   (no current image to tag — first deploy)"

# 4. Build the new image while the old containers keep serving. Docker build
#    doesn't touch running containers, so the site stays up during this step.
echo "🔨 Building new image..."
$COMPOSE build --no-cache

# 5. Stop the old containers and start the new ones.
echo "⏹️  Stopping old containers..."
$COMPOSE down

echo "▶️  Starting new containers..."
$COMPOSE up -d

# 6. Wait for the web container to be ready before we run migrations through it.
echo "⏳ Waiting for web container to accept exec..."
sleep 10

# 7. Apply database migrations. The container command no longer runs alembic
#    on startup — this is the single, operator-controlled migration point.
echo "📦 Running database migrations..."
$COMPOSE exec -T web alembic upgrade head

echo "📊 Current migration version:"
$COMPOSE exec -T web alembic current

# 8. Verify the app actually serves. If this fails, the deploy reports failure
#    and the caller knows to roll back per docs/RUNBOOK.md.
echo "🩺 Health check..."
HEALTH_TRIES=10
for i in $(seq 1 "$HEALTH_TRIES"); do
    if curl -fsS "$HEALTH_URL" >/dev/null; then
        echo "✅ Health check passed on attempt $i"
        break
    fi
    if [ "$i" -eq "$HEALTH_TRIES" ]; then
        echo "❌ Health check failed after $HEALTH_TRIES attempts. See docs/RUNBOOK.md for rollback."
        exit 1
    fi
    sleep 2
done

# 9. Host hygiene. Use `docker image prune` (not `system prune`) with an
#    "until=24h" filter so the sabc-web:prev rollback tag survives — it points
#    at an image that is also tagged :prev, so it's not dangling, but we still
#    want to avoid blowing away recently-tagged images by accident.
echo "🧹 Cleaning up..."
docker image prune -f --filter "until=24h"
sudo journalctl --vacuum-time=7d
sudo apt clean

echo ""
echo "✅ Deployment complete!"
echo "🌐 Application: https://saustinbc.com"
echo "📊 Check logs: $COMPOSE logs -f web"
echo "↩️  Rollback steps: docs/RUNBOOK.md"