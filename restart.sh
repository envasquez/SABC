#!/usr/bin/bash
# Production deployment script with database migrations

echo "🚀 Starting deployment..."

# Stop containers
echo "⏹️  Stopping containers..."
docker compose -f docker-compose.prod.yml down

# Pull latest code
echo "📥 Pulling latest code..."
git pull

# Rebuild containers
echo "🔨 Building containers..."
docker compose -f docker-compose.prod.yml build --no-cache

# Start containers
echo "▶️  Starting containers..."
docker compose -f docker-compose.prod.yml up -d

# Wait for database to be ready
echo "⏳ Waiting for database..."
sleep 10

# Run database migrations
echo "📦 Running database migrations..."
docker compose -f docker-compose.prod.yml exec -T web alembic upgrade head

# Check migration status
echo "📊 Current migration version:"
docker compose -f docker-compose.prod.yml exec -T web alembic current

# Cleanup
echo "🧹 Cleaning up..."
docker system prune -f
sudo journalctl --vacuum-time=7d
sudo apt clean

echo ""
echo "✅ Deployment complete!"
echo "🌐 Application: https://saustinbc.com"
echo "📊 Check logs: docker compose -f docker-compose.prod.yml logs -f web"
