#!/bin/bash

# SABC Database Backup Script
# This script creates timestamped backups of the PostgreSQL database
# Usage: ./backup_database.sh [environment]
# Environment: dev, staging, production (default: dev)

set -e  # Exit on any error

# Configuration
ENVIRONMENT=${1:-dev}
BACKUP_DIR="$(dirname "$0")/../backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$BACKUP_DIR/backup_${ENVIRONMENT}_${TIMESTAMP}.log"

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to cleanup old backups (keep last 7 days)
cleanup_old_backups() {
    log "Cleaning up backups older than 7 days..."
    find "$BACKUP_DIR" -name "sabc_backup_${ENVIRONMENT}_*.sql" -mtime +7 -delete 2>/dev/null || true
    find "$BACKUP_DIR" -name "backup_${ENVIRONMENT}_*.log" -mtime +7 -delete 2>/dev/null || true
}

# Load environment-specific database credentials
case $ENVIRONMENT in
    "production")
        # Production environment variables (should be set in deployment)
        DB_NAME=${POSTGRES_DB:-sabc}
        DB_USER=${POSTGRES_USER:-postgres}
        DB_HOST=${DEPLOYMENT_HOST:-localhost}
        DB_PORT=${POSTGRES_PORT:-5432}
        BACKUP_FILE="$BACKUP_DIR/sabc_backup_production_${TIMESTAMP}.sql"
        ;;
    "staging")
        # Staging environment variables
        DB_NAME=${POSTGRES_DB:-sabc_staging}
        DB_USER=${POSTGRES_USER:-postgres}
        DB_HOST=${DEPLOYMENT_HOST:-localhost}
        DB_PORT=${POSTGRES_PORT:-5432}
        BACKUP_FILE="$BACKUP_DIR/sabc_backup_staging_${TIMESTAMP}.sql"
        ;;
    "dev"|*)
        # Development environment variables
        DB_NAME=${POSTGRES_DB:-sabc}
        DB_USER=${POSTGRES_USER:-env}
        DB_HOST=localhost
        DB_PORT=5432
        BACKUP_FILE="$BACKUP_DIR/sabc_backup_dev_${TIMESTAMP}.sql"
        ;;
esac

log "Starting backup for $ENVIRONMENT environment"
log "Database: $DB_NAME on $DB_HOST:$DB_PORT as user $DB_USER"
log "Backup file: $BACKUP_FILE"

# Check if database is accessible
log "Testing database connection..."
if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; then
    log "ERROR: Cannot connect to database $DB_NAME on $DB_HOST:$DB_PORT"
    exit 1
fi

log "Database connection successful"

# Create the backup
log "Creating database backup..."
if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --verbose \
    --no-password \
    --format=plain \
    --no-privileges \
    --no-tablespaces \
    --quote-all-identifiers \
    > "$BACKUP_FILE" 2>>"$LOG_FILE"; then
    
    # Compress the backup
    log "Compressing backup..."
    gzip "$BACKUP_FILE"
    BACKUP_FILE="${BACKUP_FILE}.gz"
    
    # Get file size
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log "Backup created successfully: $BACKUP_FILE ($BACKUP_SIZE)"
    
    # Verify backup integrity
    log "Verifying backup integrity..."
    if gunzip -t "$BACKUP_FILE" >/dev/null 2>&1; then
        log "Backup integrity check passed"
    else
        log "ERROR: Backup integrity check failed"
        exit 1
    fi
    
    # Cleanup old backups
    cleanup_old_backups
    
    log "Backup process completed successfully"
    
    # Return backup file path for scripts
    echo "$BACKUP_FILE"
    
else
    log "ERROR: Backup failed"
    exit 1
fi