#!/usr/bin/env bash
# Apply database migration for Phase 1 bug fixes

set -e

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    if [ -f ".env" ]; then
        source .env
    else
        echo "ERROR: DATABASE_URL not set and no .env file found"
        exit 1
    fi
fi

echo "🔧 Applying Phase 1 database migration..."
echo "Database: $DATABASE_URL"
echo ""

# Apply migration
psql "$DATABASE_URL" -f scripts/migration_add_vote_constraints.sql

echo ""
echo "✅ Migration completed successfully!"
echo ""
echo "Changes applied:"
echo "  • Added unique constraint on poll_votes (poll_id, angler_id)"
echo "  • Added unique constraint on team_results (tournament_id, angler1_id, angler2_id)"
echo ""
echo "These constraints prevent:"
echo "  • Duplicate voting via race conditions"
echo "  • Duplicate team result entries"
