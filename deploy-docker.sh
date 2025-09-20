#!/bin/bash
# deploy-docker.sh - One-command Docker deployment

set -e

echo "🚀 SABC Docker Deployment Script"
echo "================================"

# Configuration
REMOTE_USER="root"
REMOTE_HOST="your-droplet-ip"
REMOTE_DIR="/opt/sabc"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if remote host is provided
if [ "$1" ]; then
    REMOTE_HOST="$1"
fi

echo -e "${YELLOW}📍 Deploying to: $REMOTE_USER@$REMOTE_HOST${NC}"
echo ""

# Create deployment package
echo "📦 Creating deployment package..."
tar -czf sabc-deploy.tar.gz \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.env' \
    --exclude='venv' \
    --exclude='.pytest_cache' \
    --exclude='*.db' \
    --exclude='node_modules' \
    --exclude='sabc-deploy.tar.gz' \
    .

# Upload to server
echo "📤 Uploading to server..."
scp sabc-deploy.tar.gz $REMOTE_USER@$REMOTE_HOST:/tmp/

# Deploy on server
echo "🔧 Deploying on server..."
ssh $REMOTE_USER@$REMOTE_HOST << 'ENDSSH'
    set -e

    # Create app directory
    mkdir -p /opt/sabc
    cd /opt/sabc

    # Extract files
    echo "📂 Extracting files..."
    tar -xzf /tmp/sabc-deploy.tar.gz
    rm /tmp/sabc-deploy.tar.gz

    # Create .env.production if not exists
    if [ ! -f .env.production ]; then
        echo "⚠️  Creating .env.production from example..."
        cp .env.production.example .env.production
        echo "⚠️  IMPORTANT: Edit .env.production with your values!"
    fi

    # Stop existing containers
    echo "🛑 Stopping existing containers..."
    docker compose -f docker compose.prod.yml --env-file .env.production down 2>/dev/null || true

    # Build and start containers
    echo "🏗️  Building containers..."
    docker compose -f docker compose.prod.yml --env-file .env.production build

    echo "🚀 Starting containers..."
    docker compose -f docker compose.prod.yml --env-file .env.production up -d

    # Wait for services to be ready
    echo "⏳ Waiting for services to start..."
    sleep 10

    # Initialize database
    echo "🗃️  Initializing database..."
    docker compose -f docker compose.prod.yml --env-file .env.production exec -T web python scripts/setup_db.py
    docker compose -f docker compose.prod.yml --env-file .env.production exec -T web python scripts/setup_admin.py --non-interactive || echo "Admin already exists"

    # Check health
    echo "🏥 Checking application health..."
    if curl -f http://localhost/health > /dev/null 2>&1; then
        echo "✅ Application is healthy!"
    else
        echo "⚠️  Health check failed, but containers are running"
    fi

    # Show container status
    echo ""
    echo "📊 Container Status:"
    docker compose -f docker compose.prod.yml --env-file .env.production ps

    echo ""
    echo "✅ Deployment complete!"
    echo "🌐 Access your site at: http://$(hostname -I | awk '{print $1}')"
    echo ""
    echo "📝 Useful commands:"
    echo "  View logs:    docker compose -f docker compose.prod.yml logs -f"
    echo "  Restart:      docker compose -f docker compose.prod.yml restart"
    echo "  Stop:         docker compose -f docker compose.prod.yml down"
    echo "  Backup DB:    docker compose -f docker compose.prod.yml exec postgres pg_dump -U sabc_user sabc > backup.sql"
ENDSSH

# Cleanup
rm sabc-deploy.tar.gz

echo ""
echo -e "${GREEN}🎉 Deployment successful!${NC}"
echo -e "${YELLOW}Next steps:${NC}"
echo "1. SSH into server: ssh $REMOTE_USER@$REMOTE_HOST"
echo "2. Edit /opt/sabc/.env.production with your values"
echo "3. Restart: cd /opt/sabc && docker compose -f docker compose.prod.yml --env-file .env.production restart"