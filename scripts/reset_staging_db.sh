#!/bin/bash
# Reset Staging Database and Populate with Test Data
#
# This script completely resets the staging database and populates it
# with realistic test data for testing and demonstration purposes.
#
# WARNING: This DELETES ALL DATA in the staging database!
#
# Usage:
#   ./scripts/reset_staging_db.sh
#
# Prerequisites:
#   - STAGING_DATABASE_URL environment variable must be set
#   - PostgreSQL client (psql) must be installed
#   - Python with required dependencies must be available

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  SABC Staging Database Reset Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if STAGING_DATABASE_URL is set
if [ -z "$STAGING_DATABASE_URL" ]; then
    echo -e "${RED}❌ Error: STAGING_DATABASE_URL environment variable not set${NC}"
    echo ""
    echo "Please set the staging database URL:"
    echo "  export STAGING_DATABASE_URL='postgresql://user:pass@host:port/sabc_staging?sslmode=require'"
    echo ""
    echo "You can find this in Digital Ocean:"
    echo "  Dashboard → Databases → sabc-staging-db → Connection Details"
    exit 1
fi

# Confirm with user
echo -e "${YELLOW}⚠️  WARNING: This will DELETE ALL DATA in staging database!${NC}"
echo ""
echo "Database: $STAGING_DATABASE_URL"
echo ""
echo -e "${YELLOW}Press Ctrl+C to cancel, or Enter to continue...${NC}"
read

# Drop and recreate schema
echo ""
echo -e "${BLUE}🗑️  Dropping all tables...${NC}"
psql "$STAGING_DATABASE_URL" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" || {
    echo -e "${RED}❌ Failed to drop schema${NC}"
    exit 1
}
echo -e "${GREEN}✅ Schema dropped${NC}"

# Run Alembic migrations
echo ""
echo -e "${BLUE}📦 Running Alembic migrations...${NC}"
DATABASE_URL="$STAGING_DATABASE_URL" alembic upgrade head || {
    echo -e "${RED}❌ Migrations failed${NC}"
    exit 1
}
echo -e "${GREEN}✅ Migrations complete${NC}"

# Seed test data
echo ""
echo -e "${BLUE}🌱 Seeding test data...${NC}"
DATABASE_URL="$STAGING_DATABASE_URL" python scripts/seed_staging_data.py || {
    echo -e "${RED}❌ Seeding failed${NC}"
    exit 1
}
echo -e "${GREEN}✅ Test data seeded${NC}"

# Summary
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Staging Database Reset Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Test Credentials:${NC}"
echo "  Admin:    admin@staging.sabc.test / TestPassword123!"
echo "  Members:  member1-10@staging.sabc.test / TestPassword123!"
echo ""
echo -e "${BLUE}Staging URL:${NC}"
echo "  https://staging.sabc.example.com"
echo ""
echo -e "${GREEN}✨ Ready for testing!${NC}"
