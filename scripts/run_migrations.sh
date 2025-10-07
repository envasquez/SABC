#!/usr/bin/env bash
# Run all pending database migrations
# This script is designed to run in the production container

set -e

echo "🔄 Running database migrations..."

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "❌ ERROR: DATABASE_URL environment variable not set"
    exit 1
fi

echo "📦 Database: ${DATABASE_URL%%@*}@***"
echo ""

# Run all migration files in order
for migration in scripts/migration_*.sql; do
    if [ -f "$migration" ]; then
        echo "📝 Applying: $(basename $migration)"
        psql "$DATABASE_URL" -f "$migration"
        echo "✅ Applied: $(basename $migration)"
        echo ""
    fi
done

echo "✨ All migrations completed successfully!"
