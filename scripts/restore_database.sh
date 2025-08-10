#!/bin/bash

# SABC Database Restore Script
# This script restores a database backup with safety checks
# Usage: ./restore_database.sh <backup_file> [target_environment]
# Target environment: dev, staging, production (default: dev)

set -e  # Exit on any error

if [ $# -lt 1 ]; then
    echo "Usage: $0 <backup_file> [target_environment]"
    echo "Example: $0 /path/to/backup.sql.gz dev"
    exit 1
fi

BACKUP_FILE="$1"
TARGET_ENV=${2:-dev}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_DIR="$(dirname "$0")/../backups"
LOG_FILE="$LOG_DIR/restore_${TARGET_ENV}_${TIMESTAMP}.log"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to prompt for confirmation
confirm() {
    echo -n "$1 [y/N]: "
    read -r response
    case "$response" in
        [yY][eE][sS]|[yY])
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# Validate backup file
if [ ! -f "$BACKUP_FILE" ]; then
    log "ERROR: Backup file not found: $BACKUP_FILE"
    exit 1
fi

# Check if backup file is compressed
if [[ "$BACKUP_FILE" == *.gz ]]; then
    log "Backup file is compressed, will decompress during restore"
    CAT_CMD="zcat"
else
    CAT_CMD="cat"
fi

# Load target environment database credentials
case $TARGET_ENV in
    "production")
        if ! confirm "⚠️  WARNING: You are about to restore to PRODUCTION database. This is IRREVERSIBLE. Continue?"; then
            log "Restore to production cancelled by user"
            exit 0
        fi
        DB_NAME=${POSTGRES_DB:-sabc}
        DB_USER=${POSTGRES_USER:-postgres}
        DB_HOST=${DEPLOYMENT_HOST:-localhost}
        DB_PORT=${POSTGRES_PORT:-5432}
        ;;
    "staging")
        DB_NAME=${POSTGRES_DB:-sabc_staging}
        DB_USER=${POSTGRES_USER:-postgres}
        DB_HOST=${DEPLOYMENT_HOST:-localhost}
        DB_PORT=${POSTGRES_PORT:-5432}
        ;;
    "dev"|*)
        DB_NAME=${POSTGRES_DB:-sabc}
        DB_USER=${POSTGRES_USER:-env}
        DB_HOST=localhost
        DB_PORT=5432
        ;;
esac

log "Starting restore process for $TARGET_ENV environment"
log "Target database: $DB_NAME on $DB_HOST:$DB_PORT as user $DB_USER"
log "Backup file: $BACKUP_FILE"

# Verify backup file integrity
log "Verifying backup file integrity..."
if [[ "$BACKUP_FILE" == *.gz ]]; then
    if ! gunzip -t "$BACKUP_FILE" >/dev/null 2>&1; then
        log "ERROR: Backup file integrity check failed"
        exit 1
    fi
fi
log "Backup file integrity check passed"

# Check database connection
log "Testing database connection..."
if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; then
    log "ERROR: Cannot connect to database $DB_NAME on $DB_HOST:$DB_PORT"
    exit 1
fi
log "Database connection successful"

# Create safety backup before restore (except for production)
if [ "$TARGET_ENV" != "production" ]; then
    log "Creating safety backup before restore..."
    SAFETY_BACKUP="$LOG_DIR/pre_restore_safety_${TARGET_ENV}_${TIMESTAMP}.sql"
    if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        --no-password --format=plain --no-privileges --no-tablespaces > "$SAFETY_BACKUP" 2>>"$LOG_FILE"; then
        gzip "$SAFETY_BACKUP"
        log "Safety backup created: ${SAFETY_BACKUP}.gz"
    else
        log "WARNING: Could not create safety backup, continuing with restore..."
    fi
fi

# Final confirmation
if ! confirm "Ready to restore backup to $TARGET_ENV database '$DB_NAME'. Continue?"; then
    log "Restore cancelled by user"
    exit 0
fi

# Drop existing database and recreate (only for dev/staging)
if [ "$TARGET_ENV" != "production" ]; then
    log "Recreating database..."
    
    # Terminate existing connections to the database
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres \
        -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();" \
        2>>"$LOG_FILE" || true
    
    # Drop and recreate database
    dropdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" 2>>"$LOG_FILE" || true
    createdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" 2>>"$LOG_FILE"
    
    log "Database recreated"
fi

# Restore the backup
log "Restoring database from backup..."
if $CAT_CMD "$BACKUP_FILE" | psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --quiet --single-transaction 2>>"$LOG_FILE"; then
    
    log "Database restore completed successfully"
    
    # Run basic verification
    log "Running post-restore verification..."
    
    # Check if key tables exist
    TABLES=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>>"$LOG_FILE")
    
    if [ "$TABLES" -gt 0 ]; then
        log "Verification passed: Found $TABLES tables in database"
    else
        log "WARNING: Verification failed: No tables found in database"
        exit 1
    fi
    
    log "Restore process completed successfully"
    
else
    log "ERROR: Database restore failed"
    exit 1
fi