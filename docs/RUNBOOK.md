# Operations Runbook

When something is on fire at 11 PM during a tournament weekend, you read this file.

## Roll back a failed deploy

`restart.sh` makes a gzip'd `pg_dump` of the prod database into `~/backups/sabc_YYYYMMDD_HHMMSS.sql.gz` **before** doing anything destructive. That backup is what you restore from.

### When to roll back

Roll back if any of the following is true after `restart.sh` finishes (or aborts):

- The health-check loop at the end of `restart.sh` exited non-zero
- `docker compose -f docker-compose.prod.yml logs web` shows the app crashing on startup
- `https://saustinbc.com/health` returns 5xx or doesn't respond
- A migration partially applied and the schema is half-broken
- Anything user-visible is wrong and you can't immediately diagnose

### Steps

```bash
# 1. Find the most recent backup (created by this deploy)
ls -t ~/backups/sabc_*.sql.gz | head -1
# Note the filename, e.g. ~/backups/sabc_20260513_211530.sql.gz

# 2. Find the last known-good git revision (the one this deploy replaced).
#    `git reflog` shows what HEAD was before `git pull`.
git reflog | head -5
# Example: HEAD@{1}: pull: Fast-forward
# Note the commit hash on the line BEFORE the pull, e.g. c294153

# 3. Stop the broken containers (don't `down` — we want postgres running for the restore)
docker compose -f docker-compose.prod.yml stop web

# 4. Restore the database
gunzip -c ~/backups/sabc_YYYYMMDD_HHMMSS.sql.gz | \
    docker compose -f docker-compose.prod.yml exec -T postgres psql -U sabc_user sabc

# 5. Roll the code back to the previous revision
git reset --hard <PREVIOUS_COMMIT_HASH>

# 6. Rebuild and start
docker compose -f docker-compose.prod.yml build --no-cache web
docker compose -f docker-compose.prod.yml up -d

# 7. Verify
curl -fsS https://saustinbc.com/health
docker compose -f docker-compose.prod.yml logs --tail=50 web
```

### If the backup restore fails

The backup is a `pg_dump` in custom format compressed with gzip. If `psql` chokes:

```bash
# Inspect the backup is valid
gunzip -t ~/backups/sabc_YYYYMMDD_HHMMSS.sql.gz && echo "gzip OK"
gunzip -c ~/backups/sabc_YYYYMMDD_HHMMSS.sql.gz | head -50

# If the database is in a weird state, drop and recreate it before restoring:
docker compose -f docker-compose.prod.yml exec -T postgres psql -U sabc_user -d postgres \
    -c "DROP DATABASE IF EXISTS sabc; CREATE DATABASE sabc OWNER sabc_user;"
gunzip -c ~/backups/sabc_YYYYMMDD_HHMMSS.sql.gz | \
    docker compose -f docker-compose.prod.yml exec -T postgres psql -U sabc_user sabc
```

## Common incidents

### "too many connections for role" errors

Postgres is at its `max_connections` ceiling.

```bash
# How many active connections, by source?
docker compose -f docker-compose.prod.yml exec -T postgres \
    psql -U sabc_user sabc -c "SELECT count(*), client_addr FROM pg_stat_activity GROUP BY client_addr;"

# Kill idle connections older than 5 minutes
docker compose -f docker-compose.prod.yml exec -T postgres \
    psql -U sabc_user sabc -c \
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity \
     WHERE state = 'idle' AND state_change < now() - interval '5 minutes';"
```

Persistent? Lower `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` in `.env.production` and restart. Defaults are 5+10 per worker; with 4 workers that's 60 max. The compose file already sets `max_connections=200`, so unless you've bumped `WORKERS` you should never hit this.

### Site won't start after deploy: secret missing

The app now hard-fails if `SECRET_KEY` is missing in any non-dev/non-test environment, and prod compose hard-fails if `DB_PASSWORD` or `SECRET_KEY` are missing.

```bash
# Check what's set
grep -E '^(SECRET_KEY|DB_PASSWORD|ENVIRONMENT)=' .env.production
# Should show all three with non-empty values.
```

Fix `.env.production` and re-run `restart.sh`.

### Migrations applied but app still serves the old version

The browser may be caching. Hard-refresh (Cmd-Shift-R). The CSS cache-bust param in `templates/base.html` (`?v=N`) should normally handle this — verify it was bumped if CSS changed.

If the app itself appears stale: `docker compose -f docker-compose.prod.yml restart web`.

### Database container stuck in restart loop

```bash
docker compose -f docker-compose.prod.yml logs --tail=100 postgres
```

Common causes: corrupt data volume (rare), permission errors on `/var/lib/postgresql/data`, or out-of-disk. Check `df -h` first.

## Reference

- Backups: `~/backups/sabc_*.sql.gz` (last 10 retained automatically by `restart.sh`)
- Logs: `docker compose -f docker-compose.prod.yml logs -f web`
- Health: `curl https://saustinbc.com/health`
- Compose file: `docker-compose.prod.yml`
- Env file: `.env.production` (not in git — keep a copy somewhere safe)
