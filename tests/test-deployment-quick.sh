#!/bin/bash
# test-deployment-quick.sh - Quick smoke test for production deployment

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🧪 Quick Deployment Test"
echo "======================="

# Start containers
echo "Starting containers..."
docker compose -f docker-compose.prod.yml --env-file .env.local-test up -d

# Wait for startup
echo "Waiting for services (15 seconds)..."
sleep 15

# Run tests
echo ""
echo "Running smoke tests:"
echo "-------------------"

FAILED=0

# Test 1: Database connection
echo -n "1. Database connection: "
if docker compose -f docker-compose.prod.yml --env-file .env.local-test exec -T postgres pg_isready -U sabc_user > /dev/null 2>&1; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC}"
    FAILED=$((FAILED + 1))
fi

# Test 2: Web app health
echo -n "2. Web app health:      "
if curl -sf http://localhost:8000/health > /dev/null; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC}"
    FAILED=$((FAILED + 1))
fi

# Test 3: Nginx proxy
echo -n "3. Nginx proxy:         "
if curl -sf http://localhost/ > /dev/null; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC}"
    FAILED=$((FAILED + 1))
fi

# Test 4: Static files
echo -n "4. Static files:        "
if curl -sf http://localhost/static/style.css > /dev/null; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC}"
    FAILED=$((FAILED + 1))
fi

# Test 5: Database tables
echo -n "5. Database tables:     "
TABLE_COUNT=$(docker compose -f docker-compose.prod.yml --env-file .env.local-test exec -T postgres psql -U sabc_user -d sabc -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'" 2>/dev/null | tr -d ' ')
if [ "$TABLE_COUNT" -gt "0" ]; then
    echo -e "${GREEN}PASS${NC} ($TABLE_COUNT tables)"
else
    echo -e "${RED}FAIL${NC}"
    FAILED=$((FAILED + 1))
fi

echo ""
echo "-------------------"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    echo ""
    echo "Production deployment is working correctly."
else
    echo -e "${RED}❌ $FAILED test(s) failed${NC}"
    echo ""
    echo "Check logs with:"
    echo "docker compose -f docker-compose.prod.yml --env-file .env.local-test logs"
fi

echo ""
echo "Cleanup with:"
echo "docker compose -f docker-compose.prod.yml --env-file .env.local-test down -v"