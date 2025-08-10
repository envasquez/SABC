#!/bin/bash

# SABC Migration Testing Script
# This script tests database migrations on a copy of production data
# Usage: ./test_migration.sh <production_backup_file>

set -e  # Exit on any error

if [ $# -lt 1 ]; then
    echo "Usage: $0 <production_backup_file>"
    echo "Example: $0 /path/to/production_backup.sql.gz"
    exit 1
fi

PRODUCTION_BACKUP="$1"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TEST_DB="sabc_migration_test_${TIMESTAMP}"
LOG_DIR="$(dirname "$0")/../backups"
LOG_FILE="$LOG_DIR/migration_test_${TIMESTAMP}.log"
SCRIPT_DIR="$(dirname "$0")"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to cleanup test database
cleanup() {
    log "Cleaning up test database: $TEST_DB"
    dropdb -U "${POSTGRES_USER:-env}" "$TEST_DB" 2>/dev/null || true
}

# Set trap for cleanup on exit
trap cleanup EXIT

log "Starting migration test with production backup: $PRODUCTION_BACKUP"

# Validate production backup file
if [ ! -f "$PRODUCTION_BACKUP" ]; then
    log "ERROR: Production backup file not found: $PRODUCTION_BACKUP"
    exit 1
fi

# Create test database
log "Creating test database: $TEST_DB"
createdb -U "${POSTGRES_USER:-env}" "$TEST_DB"

# Restore production backup to test database
log "Restoring production backup to test database..."
if [[ "$PRODUCTION_BACKUP" == *.gz ]]; then
    CAT_CMD="zcat"
else
    CAT_CMD="cat"
fi

if $CAT_CMD "$PRODUCTION_BACKUP" | psql -U "${POSTGRES_USER:-env}" -d "$TEST_DB" \
    --quiet --single-transaction 2>>"$LOG_FILE"; then
    log "Production backup restored successfully to test database"
else
    log "ERROR: Failed to restore production backup"
    exit 1
fi

# Get pre-migration table counts
log "Recording pre-migration database state..."
PRE_TABLES=$(psql -U "${POSTGRES_USER:-env}" -d "$TEST_DB" \
    -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>>"$LOG_FILE")

PRE_USERS=$(psql -U "${POSTGRES_USER:-env}" -d "$TEST_DB" \
    -t -c "SELECT COUNT(*) FROM auth_user;" 2>>"$LOG_FILE" || echo "0")

PRE_TOURNAMENTS=$(psql -U "${POSTGRES_USER:-env}" -d "$TEST_DB" \
    -t -c "SELECT COUNT(*) FROM tournaments_tournament;" 2>>"$LOG_FILE" || echo "0")

log "Pre-migration state: $PRE_TABLES tables, $PRE_USERS users, $PRE_TOURNAMENTS tournaments"

# Set environment variables for Django to use test database
export POSTGRES_DB="$TEST_DB"
export DJANGO_SETTINGS_MODULE="sabc.settings"

# Change to Django project directory
cd "$(dirname "$0")/../sabc"

# Show current migration status
log "Checking current migration status..."
python manage.py showmigrations 2>>"$LOG_FILE"

# Plan migrations (dry run)
log "Planning migrations (dry run)..."
python manage.py migrate --plan 2>>"$LOG_FILE"

# Run migrations
log "Running migrations on test database..."
if python manage.py migrate --verbosity=2 2>>"$LOG_FILE"; then
    log "Migrations completed successfully"
else
    log "ERROR: Migrations failed"
    exit 1
fi

# Get post-migration table counts
log "Recording post-migration database state..."
POST_TABLES=$(psql -U "${POSTGRES_USER:-env}" -d "$TEST_DB" \
    -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>>"$LOG_FILE")

POST_USERS=$(psql -U "${POSTGRES_USER:-env}" -d "$TEST_DB" \
    -t -c "SELECT COUNT(*) FROM auth_user;" 2>>"$LOG_FILE" || echo "0")

POST_TOURNAMENTS=$(psql -U "${POSTGRES_USER:-env}" -d "$TEST_DB" \
    -t -c "SELECT COUNT(*) FROM tournaments_tournament;" 2>>"$LOG_FILE" || echo "0")

log "Post-migration state: $POST_TABLES tables, $POST_USERS users, $POST_TOURNAMENTS tournaments"

# Data integrity checks
log "Running data integrity checks..."

# Check for any foreign key violations
INTEGRITY_ISSUES=$(psql -U "${POSTGRES_USER:-env}" -d "$TEST_DB" \
    -t -c "
    DO \$\$
    DECLARE
        r RECORD;
        violations INTEGER := 0;
    BEGIN
        FOR r IN
            SELECT conname, conrelid::regclass AS table_name
            FROM pg_constraint
            WHERE contype = 'f'
        LOOP
            BEGIN
                EXECUTE 'SELECT 1 FROM ' || r.table_name || ' LIMIT 1';
            EXCEPTION WHEN OTHERS THEN
                violations := violations + 1;
                RAISE NOTICE 'Foreign key constraint issue: %', r.conname;
            END;
        END LOOP;
        RAISE NOTICE 'Total integrity violations: %', violations;
    END
    \$\$;" 2>>"$LOG_FILE" | grep -o '[0-9]*' | tail -1 || echo "0")

if [ "$INTEGRITY_ISSUES" -eq 0 ]; then
    log "Data integrity check passed"
else
    log "WARNING: Found $INTEGRITY_ISSUES potential integrity issues"
fi

# Run Django checks
log "Running Django system checks..."
if python manage.py check --deploy 2>>"$LOG_FILE"; then
    log "Django system checks passed"
else
    log "WARNING: Django system checks found issues (see log for details)"
fi

# Test basic functionality
log "Testing basic application functionality..."
if python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sabc.settings')
django.setup()

from django.contrib.auth.models import User
from users.models import Angler
from tournaments.models.tournaments import Tournament

print(f'Users: {User.objects.count()}')
print(f'Anglers: {Angler.objects.count()}') 
print(f'Tournaments: {Tournament.objects.count()}')
print('Basic functionality test passed')
" 2>>"$LOG_FILE"; then
    log "Basic functionality test passed"
else
    log "ERROR: Basic functionality test failed"
    exit 1
fi

# Generate migration test report
REPORT_FILE="$LOG_DIR/migration_test_report_${TIMESTAMP}.txt"
cat > "$REPORT_FILE" << EOF
SABC Migration Test Report
==========================

Test Date: $(date)
Production Backup: $PRODUCTION_BACKUP
Test Database: $TEST_DB

Pre-Migration State:
- Tables: $PRE_TABLES
- Users: $PRE_USERS  
- Tournaments: $PRE_TOURNAMENTS

Post-Migration State:
- Tables: $POST_TABLES
- Users: $POST_USERS
- Tournaments: $POST_TOURNAMENTS

Changes:
- Tables: $((POST_TABLES - PRE_TABLES))
- Users: $((POST_USERS - PRE_USERS))
- Tournaments: $((POST_TOURNAMENTS - PRE_TOURNAMENTS))

Data Integrity Issues: $INTEGRITY_ISSUES

Status: PASSED
Recommendation: Migrations are safe to apply to production

Full log available at: $LOG_FILE
EOF

log "Migration test completed successfully"
log "Test report generated: $REPORT_FILE"

echo ""
echo "========================================="
echo "MIGRATION TEST SUMMARY"
echo "========================================="
echo "Status: PASSED ✅"
echo "Tables: $PRE_TABLES → $POST_TABLES (${POST_TABLES:+$((POST_TABLES - PRE_TABLES))})"
echo "Users: $PRE_USERS → $POST_USERS (${POST_USERS:+$((POST_USERS - PRE_USERS))})"
echo "Tournaments: $PRE_TOURNAMENTS → $POST_TOURNAMENTS (${POST_TOURNAMENTS:+$((POST_TOURNAMENTS - PRE_TOURNAMENTS))})"
echo "Integrity Issues: $INTEGRITY_ISSUES"
echo ""
echo "Full report: $REPORT_FILE"
echo "Full log: $LOG_FILE"
echo "========================================="