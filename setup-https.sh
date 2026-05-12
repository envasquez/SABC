#!/bin/bash

# HTTPS Setup Script for SABC
# Run this on your production server

set -euo pipefail

echo "🔐 Setting up HTTPS for South Austin Bass Club"
echo "================================================"

# Check if running as root or with sudo
if [[ $EUID -eq 0 ]]; then
   echo "❌ Don't run this script as root. Run as your regular user with sudo access."
   exit 1
fi

# Require SECRET_KEY (or pull from .env.production if present) before any
# docker-compose operation so we never start prod containers with a placeholder.
if [ -z "${SECRET_KEY:-}" ] && [ -f .env.production ]; then
    # shellcheck disable=SC1091
    set -a && . ./.env.production && set +a
fi
if [ -z "${SECRET_KEY:-}" ]; then
    echo "❌ SECRET_KEY is not set. Export it or put it in .env.production before running."
    exit 1
fi

# Check if domain resolves to this server
echo "📡 Checking if saustinbc.com points to this server..."
DOMAIN_IP=$(dig +short saustinbc.com)
SERVER_IP=$(curl -s ifconfig.me)

if [ "$DOMAIN_IP" != "$SERVER_IP" ]; then
    echo "⚠️  Warning: saustinbc.com ($DOMAIN_IP) doesn't point to this server ($SERVER_IP)"
    echo "   Make sure your DNS is configured correctly before proceeding."
    read -r -p "Continue anyway? (y/N): " -n 1 REPLY
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Install certbot if not already installed
if ! command -v certbot &> /dev/null; then
    echo "📦 Installing certbot..."
    sudo apt update
    sudo apt install -y snapd
    sudo snap install --classic certbot
    sudo ln -sf /snap/bin/certbot /usr/bin/certbot
fi

# Stop current containers
echo "🛑 Stopping current containers..."
docker compose -f docker-compose.prod.yml down

# Create SSL directory
echo "📁 Creating SSL directory..."
mkdir -p ssl

# Generate certificates
echo "🔑 Generating SSL certificates..."
echo "   You'll need to enter your email and agree to terms..."
sudo certbot certonly --standalone \
    -d saustinbc.com \
    -d www.saustinbc.com \
    --non-interactive \
    --agree-tos \
    --email admin@saustinbc.com

# Copy certificates
echo "📋 Copying certificates..."
sudo cp /etc/letsencrypt/live/saustinbc.com/fullchain.pem ssl/
sudo cp /etc/letsencrypt/live/saustinbc.com/privkey.pem ssl/
sudo chown "$USER:$USER" ssl/*.pem

# Start containers with HTTPS
echo "🚀 Starting containers with HTTPS..."
docker compose -f docker-compose.prod.yml up -d

# Wait for startup
echo "⏳ Waiting for services to start..."
sleep 15

# Test HTTPS
echo "🧪 Testing HTTPS..."
if curl -k -s https://saustinbc.com/ | head -1 | grep -q "<!DOCTYPE html>"; then
    echo "✅ HTTPS is working!"
    echo "🌐 Your site is now available at:"
    echo "   https://saustinbc.com"
    echo "   https://www.saustinbc.com"
    echo ""
    echo "📋 Next steps:"
    echo "   1. Test the site in your browser"
    echo "   2. Set up automatic certificate renewal (see below)"
else
    echo "❌ HTTPS test failed. Check the logs:"
    echo "   docker logs sabc-nginx"
fi

echo ""
echo "🔄 To set up automatic certificate renewal, add this cron job:"
echo "   sudo crontab -e"
echo "   Add this line:"
echo "   0 12 * * * /usr/bin/certbot renew --quiet --post-hook \"docker restart sabc-nginx\""
echo ""
echo "🎉 HTTPS setup complete!"
