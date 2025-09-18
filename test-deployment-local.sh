#!/bin/bash
# test-deployment-local.sh - Test production deployment locally

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧪 SABC Local Production Test${NC}"
echo "=============================="
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}🧹 Cleaning up...${NC}"
    docker compose -f docker compose.prod.yml --env-file .env.local-test down -v 2>/dev/null || true
    echo -e "${GREEN}✅ Cleanup complete${NC}"
}

# Set trap to cleanup on script exit
trap cleanup EXIT

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Stop any existing containers
echo -e "${YELLOW}🛑 Stopping any existing containers...${NC}"
docker compose -f docker compose.prod.yml --env-file .env.local-test down 2>/dev/null || true
docker compose down 2>/dev/null || true  # Also stop dev containers

echo ""
echo -e "${YELLOW}🏗️  Building production containers...${NC}"
docker compose -f docker compose.prod.yml --env-file .env.local-test build

echo ""
echo -e "${YELLOW}🚀 Starting production stack...${NC}"
docker compose -f docker compose.prod.yml --env-file .env.local-test up -d

echo ""
echo -e "${YELLOW}⏳ Waiting for services to start (15 seconds)...${NC}"
sleep 15

echo ""
echo -e "${YELLOW}🗃️  Initializing database...${NC}"
docker compose -f docker compose.prod.yml --env-file .env.local-test exec -T web python scripts/init_postgres.py || echo "Database already initialized"
docker compose -f docker compose.prod.yml --env-file .env.local-test exec -T web python scripts/bootstrap_admin_postgres.py || echo "Admin already exists"

echo ""
echo -e "${YELLOW}🏥 Running health checks...${NC}"
echo ""

# Check PostgreSQL
echo -n "  PostgreSQL: "
if docker compose -f docker compose.prod.yml --env-file .env.local-test exec -T postgres pg_isready -U sabc_user > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Healthy${NC}"
else
    echo -e "${RED}❌ Not responding${NC}"
fi

# Check Web App
echo -n "  Web App:    "
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Healthy${NC}"
else
    echo -e "${RED}❌ Not responding${NC}"
fi

# Check Nginx
echo -n "  Nginx:      "
if curl -f http://localhost/ > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Healthy${NC}"
else
    echo -e "${RED}❌ Not responding${NC}"
fi

echo ""
echo -e "${YELLOW}📊 Container Status:${NC}"
docker compose -f docker compose.prod.yml --env-file .env.local-test ps

echo ""
echo -e "${GREEN}🎉 Local production test environment is running!${NC}"
echo ""
echo -e "${BLUE}📍 Access Points:${NC}"
echo "  • Web App (direct):  http://localhost:8000"
echo "  • Web App (nginx):   http://localhost"
echo "  • PostgreSQL:        localhost:5432"
echo "  • Database:          sabc / User: sabc_user"
echo ""
echo -e "${BLUE}🔧 Useful Commands:${NC}"
echo "  • View logs:         docker compose -f docker compose.prod.yml --env-file .env.local-test logs -f"
echo "  • View web logs:     docker compose -f docker compose.prod.yml --env-file .env.local-test logs -f web"
echo "  • View DB logs:      docker compose -f docker compose.prod.yml --env-file .env.local-test logs -f postgres"
echo "  • Enter web shell:   docker compose -f docker compose.prod.yml --env-file .env.local-test exec web bash"
echo "  • Enter DB shell:    docker compose -f docker compose.prod.yml --env-file .env.local-test exec postgres psql -U sabc_user -d sabc"
echo "  • Stop everything:   docker compose -f docker compose.prod.yml --env-file .env.local-test down"
echo ""
echo -e "${YELLOW}⚠️  Press Ctrl+C to stop and cleanup${NC}"
echo ""

# Keep script running and show logs
echo -e "${BLUE}📜 Following logs (Ctrl+C to stop)...${NC}"
echo ""
docker compose -f docker compose.prod.yml --env-file .env.local-test logs -f