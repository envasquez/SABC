#!/usr/bin/bash
# Production deployment script with database migrations.
# Rollback procedure: see docs/RUNBOOK.md
#
# Downtime profile: nginx and postgres stay up the entire deploy. The only
# service gap is the web container being swapped at step 6 — typically 5–15s
# of 502s while the new uvicorn binds :8000, instead of the previous 30–60s
# full-stack restart.

set -euo pipefail

COMPOSE="docker compose -f docker-compose.prod.yml"
HEALTH_URL="${HEALTH_URL:-http://localhost/health}"

NGINX_CONTAINER="${NGINX_CONTAINER:-sabc-nginx}"
MIN_FREE_MB="${MIN_FREE_MB:-1024}"

# Host hygiene, as an EXIT trap so it runs even when the deploy aborts. It used
# to be the last step, which meant a deploy that failed the health check left
# every intermediate build layer on disk — several aborted deploys in a row are
# how this droplet reached 94% full. Uses `docker image prune` (not `system
# prune`) with an "until=24h" filter, and no -a, so the sabc-web:prev rollback
# tag and the image we just built both survive.
cleanup_host() {
    echo "🧹 Cleaning up..."
    docker image prune -f --filter "until=24h" >/dev/null 2>&1 || true
    docker builder prune -f --filter "until=168h" >/dev/null 2>&1 || true
    sudo journalctl --vacuum-time=7d >/dev/null 2>&1 || true
    sudo apt clean >/dev/null 2>&1 || true
    echo "   Free space now: $(df -h / | awk 'NR==2 {print $4}')"
}
trap cleanup_host EXIT

echo "🚀 Starting deployment..."

# 0. Refuse to start a deploy that will fill the disk. A build needs room for
#    a full new image layer set; running out mid-build leaves a wedged docker
#    state that is far more annoying than an early abort.
FREE_MB=$(df -Pm / | awk 'NR==2 {print $4}')
echo "💽 Free disk: ${FREE_MB}MB"
if [ "$FREE_MB" -lt "$MIN_FREE_MB" ]; then
    echo "⚠️  Below ${MIN_FREE_MB}MB free — reclaiming space before building..."
    cleanup_host
    FREE_MB=$(df -Pm / | awk 'NR==2 {print $4}')
    if [ "$FREE_MB" -lt "$MIN_FREE_MB" ]; then
        echo "❌ Still only ${FREE_MB}MB free after cleanup. Aborting before the build." >&2
        echo "   Investigate with: docker system df && du -xh --max-depth=1 / 2>/dev/null | sort -h | tail" >&2
        exit 1
    fi
fi

# 1. Pull the latest code FIRST. This is read-only and atomic — if it fails
#    (rebase conflict, network blip, GitHub outage), we abort before touching
#    the running site.
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
#    back with `docker tag sabc-web:prev sabc-web:latest && $COMPOSE up -d --no-deps web`.
#    Safe on first deploy: the tag command no-ops if :latest doesn't exist.
echo "🏷️  Tagging current image for rollback..."
docker tag sabc-web:latest sabc-web:prev 2>/dev/null || echo "   (no current image to tag — first deploy)"

# 4. Build the new image while the old container keeps serving. Docker build
#    doesn't touch running containers, so the site stays up during this step.
#    No --no-cache: keeping the layer cache means rebuilds skip the python
#    install layer (60–120s saved) and only re-do COPY-and-after layers. If
#    a future change needs a clean build, override with: RESTART_NO_CACHE=1.
echo "🔨 Building new image..."
if [ "${RESTART_NO_CACHE:-0}" = "1" ]; then
    $COMPOSE build --no-cache web
else
    $COMPOSE build web
fi

# 5. Run migrations BEFORE swapping the web container, via a one-shot
#    container spun from the freshly built image. The OLD web container is
#    still serving traffic during this step — briefly against the NEW schema.
#    This requires migrations to be additive (expand-contract): column adds
#    and new tables are safe; destructive changes (column drops, renames,
#    NOT NULL adds without backfill) must be split across two deploys —
#    deploy #1 stops using the column, deploy #2 drops it.
#
#    If migration fails, the old web keeps serving and we abort BEFORE any
#    swap, so a broken migration never produces user-visible downtime.
#    --no-deps: postgres is already up (we just backed it up); don't restart it.
echo "📦 Running database migrations..."
$COMPOSE run --rm --no-deps -T web alembic upgrade head

echo "📊 Current migration version:"
$COMPOSE run --rm --no-deps -T web alembic current

# 6. Atomic swap of the WEB container only. --no-deps means nginx, postgres,
#    and certbot are untouched: TLS sessions survive, postgres connections
#    from the host survive, certbot's renewal schedule isn't perturbed.
#    Compose sends SIGTERM to the old web and waits up to stop_grace_period
#    (default 10s) for uvicorn to finish in-flight requests before SIGKILL.
echo "♻️  Recreating web container (nginx + postgres stay up)..."
$COMPOSE up -d --no-deps web

# 7. Wait for the new web to be healthy via direct container exec. Replaces
#    the previous blind `sleep 10` — exits as soon as the app is actually
#    ready, capped at HEALTH_TRIES seconds.
echo "⏳ Waiting for new web to pass internal health check..."
HEALTH_TRIES=30
for i in $(seq 1 "$HEALTH_TRIES"); do
    if $COMPOSE exec -T web curl -fsS http://localhost:8000/health >/dev/null 2>&1; then
        echo "✅ Web container healthy on attempt $i"
        break
    fi
    if [ "$i" -eq "$HEALTH_TRIES" ]; then
        echo "❌ Web container failed health check after $HEALTH_TRIES attempts. See docs/RUNBOOK.md for rollback."
        exit 1
    fi
    sleep 1
done

# 7.5 Make sure nginx is actually running. This deploy only recreates `web`
#     (--no-deps), so a stopped nginx is invisible to every check above: the
#     app is perfectly healthy and the site is still completely unreachable.
#     re-cert.sh stopping nginx and failing before restarting it is exactly
#     how that happens. nginx being down is never intentional, so fix it.
echo "🔎 Verifying nginx is up..."
NGINX_STATE=$(docker inspect -f '{{.State.Status}}' "$NGINX_CONTAINER" 2>/dev/null || echo "missing")
if [ "$NGINX_STATE" != "running" ]; then
    echo "⚠️  nginx is '${NGINX_STATE}' — the site is unreachable regardless of app health."
    echo "   Starting it..."
    $COMPOSE up -d --no-deps nginx
    sleep 2
    NGINX_STATE=$(docker inspect -f '{{.State.Status}}' "$NGINX_CONTAINER" 2>/dev/null || echo "missing")
    if [ "$NGINX_STATE" != "running" ]; then
        echo "❌ nginx still '${NGINX_STATE}'. Its logs:" >&2
        docker logs --tail=30 "$NGINX_CONTAINER" 2>&1 | sed 's/^/   /' >&2
        exit 1
    fi
    echo "✅ nginx recovered."
else
    echo "✅ nginx running."
fi

# 8. Verify the public path through nginx still works end-to-end.
echo "🩺 External health check..."
EXT_HEALTH_TRIES=10
for i in $(seq 1 "$EXT_HEALTH_TRIES"); do
    if curl -fsS "$HEALTH_URL" >/dev/null; then
        echo "✅ External health check passed on attempt $i"
        break
    fi
    if [ "$i" -eq "$EXT_HEALTH_TRIES" ]; then
        echo "❌ External health check failed after $EXT_HEALTH_TRIES attempts." >&2
        echo "" >&2
        echo "   The app itself passed its internal check, so this is the edge, not the app." >&2
        echo "   Container states:" >&2
        $COMPOSE ps -a 2>&1 | sed 's/^/   /' >&2
        echo "   Last 20 lines of nginx:" >&2
        docker logs --tail=20 "$NGINX_CONTAINER" 2>&1 | sed 's/^/   /' >&2
        echo "" >&2
        echo "   'Connection refused' => nothing listening on :80 (nginx down)." >&2
        echo "   'Connection reset'   => port published but container behind it is dead." >&2
        echo "   '502 Bad Gateway'    => nginx up, cannot reach web:8000." >&2
        echo "   See docs/RUNBOOK.md for rollback." >&2
        exit 1
    fi
    sleep 2
done

# 9. Host hygiene runs from the EXIT trap defined at the top, so it happens
#    on failed deploys too — that is where the disk actually leaks.

echo ""
echo "✅ Deployment complete!"
echo "🌐 Application: https://saustinbc.com"
echo "📊 Check logs: $COMPOSE logs -f web"
echo "↩️  Rollback steps: docs/RUNBOOK.md"
