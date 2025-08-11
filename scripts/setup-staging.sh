#!/bin/bash

#
# SABC Staging Environment Setup Script
# 
# This script sets up a staging environment that mirrors production
# Run this on your staging server after initial OS setup
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   error "This script should not be run as root"
   exit 1
fi

log "Starting SABC Staging Environment Setup"

# Update system
log "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install essential packages
log "Installing essential packages..."
sudo apt install -y \
    curl \
    wget \
    git \
    nginx \
    postgresql \
    postgresql-contrib \
    redis-server \
    certbot \
    python3-certbot-nginx \
    htop \
    unzip \
    build-essential

# Install Nix (mirrors production environment)
log "Installing Nix package manager..."
if ! command -v nix &> /dev/null; then
    curl -L https://nixos.org/nix/install | sh -s -- --daemon
    source ~/.bashrc
    info "Nix installed. Please restart your shell session and re-run this script."
    exit 0
else
    log "Nix already installed"
fi

# Enable Nix flakes (required for SABC project)
log "Enabling Nix flakes..."
mkdir -p ~/.config/nix
echo "experimental-features = nix-command flakes" > ~/.config/nix/nix.conf

# Create application user
log "Creating application user..."
if ! id "sabc-staging" &>/dev/null; then
    sudo useradd -m -s /bin/bash sabc-staging
    sudo usermod -aG sudo sabc-staging
    log "Created user: sabc-staging"
else
    log "User sabc-staging already exists"
fi

# Set up application directory
log "Setting up application directory..."
sudo -u sabc-staging mkdir -p /home/sabc-staging/app
sudo -u sabc-staging git clone https://github.com/your-username/SABC_II.git /home/sabc-staging/app/SABC_II || true

# PostgreSQL setup for staging
log "Setting up PostgreSQL for staging..."
sudo -u postgres psql << EOF
-- Create staging database and user
CREATE DATABASE sabc_staging;
CREATE USER sabc_staging_user WITH ENCRYPTED PASSWORD 'staging_password_change_me';
GRANT ALL PRIVILEGES ON DATABASE sabc_staging TO sabc_staging_user;
ALTER USER sabc_staging_user CREATEDB;
\q
EOF

# Redis configuration for staging
log "Configuring Redis for staging..."
sudo sed -i 's/# maxmemory <bytes>/maxmemory 256mb/' /etc/redis/redis.conf
sudo sed -i 's/# maxmemory-policy noeviction/maxmemory-policy allkeys-lru/' /etc/redis/redis.conf
sudo systemctl restart redis-server
sudo systemctl enable redis-server

# Create staging systemd service
log "Creating systemd service for staging..."
sudo tee /etc/systemd/system/sabc-staging.service > /dev/null << EOF
[Unit]
Description=SABC Staging Django Application
After=network.target postgresql.service redis-server.service

[Service]
Type=exec
User=sabc-staging
Group=sabc-staging
WorkingDirectory=/home/sabc-staging/app/SABC_II/SABC/sabc
Environment=DJANGO_SETTINGS_MODULE=sabc.settings
Environment=SECRET_KEY=staging-secret-key-change-me-in-production
Environment=DEBUG=True
Environment=ALLOWED_HOSTS=staging.yourdomain.com,localhost,127.0.0.1
Environment=POSTGRES_DB=sabc_staging
Environment=POSTGRES_USER=sabc_staging_user
Environment=POSTGRES_PASSWORD=staging_password_change_me
Environment=POSTGRES_HOST=localhost
Environment=POSTGRES_PORT=5432
Environment=REDIS_URL=redis://localhost:6379/1
ExecStart=/home/sabc-staging/.nix-profile/bin/nix develop -c python manage.py runserver 0.0.0.0:8001
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# Nginx configuration for staging
log "Setting up Nginx for staging..."
sudo tee /etc/nginx/sites-available/sabc-staging > /dev/null << 'EOF'
server {
    listen 80;
    server_name staging.yourdomain.com;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    
    # Staging indicator header
    add_header X-Environment "staging" always;
    
    # Static files
    location /static/ {
        alias /home/sabc-staging/app/SABC_II/SABC/sabc/staticfiles/;
        expires 7d;
        add_header Cache-Control "public";
    }
    
    # Media files
    location /media/ {
        alias /home/sabc-staging/app/SABC_II/SABC/sabc/media/;
        expires 1d;
    }
    
    # Health check
    location /health/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        access_log off;
    }
    
    # Application
    location / {
        # Add staging warning banner
        proxy_set_header X-Staging-Environment "true";
        
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# Enable the site
sudo ln -sf /etc/nginx/sites-available/sabc-staging /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx

# Set up SSL certificate for staging
log "Setting up SSL certificate for staging..."
info "Run this manually after DNS is configured:"
info "sudo certbot --nginx -d staging.yourdomain.com"

# Create staging data directory
log "Creating staging data directories..."
sudo -u sabc-staging mkdir -p /home/sabc-staging/backups
sudo -u sabc-staging mkdir -p /home/sabc-staging/logs
sudo -u sabc-staging mkdir -p /home/sabc-staging/media

# Set up log rotation for staging
sudo tee /etc/logrotate.d/sabc-staging > /dev/null << EOF
/home/sabc-staging/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 sabc-staging sabc-staging
    postrotate
        systemctl reload sabc-staging
    endscript
}
EOF

# Create staging deployment script
log "Creating staging deployment script..."
sudo -u sabc-staging tee /home/sabc-staging/deploy-staging.sh > /dev/null << 'EOF'
#!/bin/bash

set -euo pipefail

echo "🚀 Deploying to staging environment..."

# Navigate to application directory
cd ~/app/SABC_II/SABC

# Stop the application
echo "⏹️ Stopping staging application..."
sudo systemctl stop sabc-staging

# Pull latest changes from develop branch
echo "📥 Pulling latest changes..."
git fetch --all
git reset --hard origin/develop

# Install dependencies
echo "📦 Installing dependencies..."
nix develop -c bash -c "
    cd sabc &&
    pip install -r requirements.txt 2>/dev/null || echo 'No requirements.txt found'
"

# Run database migrations
echo "🗄️ Running database migrations..."
nix develop -c bash -c "
    cd sabc &&
    python manage.py migrate --noinput
"

# Load staging test data
echo "🎣 Loading staging test data..."
nix develop -c bash -c "
    cd sabc &&
    python manage.py load_fake_data --clear || echo 'Test data loading failed'
"

# Collect static files
echo "📁 Collecting static files..."
nix develop -c bash -c "
    cd sabc &&
    python manage.py collectstatic --noinput
"

# Start application
echo "🔄 Starting staging application..."
sudo systemctl start sabc-staging

# Verify deployment
echo "✅ Verifying staging deployment..."
sleep 5
if curl -f http://localhost:8001/health/ > /dev/null 2>&1; then
    echo "✅ Staging deployment successful!"
    echo "🔗 Access at: http://staging.yourdomain.com"
else
    echo "❌ Staging health check failed"
    exit 1
fi
EOF

chmod +x /home/sabc-staging/deploy-staging.sh

# Create staging monitoring script
log "Creating staging monitoring script..."
sudo -u sabc-staging tee /home/sabc-staging/monitor-staging.sh > /dev/null << 'EOF'
#!/bin/bash

echo "=== SABC Staging Environment Status ==="
echo "Date: $(date)"
echo ""

echo "=== Service Status ==="
sudo systemctl status sabc-staging --no-pager --lines=5

echo -e "\n=== Database Status ==="
sudo -u postgres psql -d sabc_staging -c "SELECT COUNT(*) as total_users FROM auth_user;"
sudo -u postgres psql -d sabc_staging -c "SELECT COUNT(*) as total_tournaments FROM tournaments_tournament;"

echo -e "\n=== Redis Status ==="
redis-cli -n 1 info keyspace

echo -e "\n=== Disk Usage ==="
df -h /home/sabc-staging/

echo -e "\n=== Memory Usage ==="
free -h

echo -e "\n=== Health Check ==="
curl -s http://localhost:8001/health/ && echo " ✅ Application healthy" || echo " ❌ Application unhealthy"

echo -e "\n=== Recent Logs ==="
tail -5 /var/log/syslog | grep sabc-staging || echo "No recent logs"
EOF

chmod +x /home/sabc-staging/monitor-staging.sh

log "✅ Staging environment setup complete!"
log ""
log "Next steps:"
log "1. Configure DNS: staging.yourdomain.com -> $(curl -s ifconfig.me)"
log "2. Run SSL setup: sudo certbot --nginx -d staging.yourdomain.com"
log "3. Initial deployment: sudo -u sabc-staging /home/sabc-staging/deploy-staging.sh"
log "4. Monitor status: sudo -u sabc-staging /home/sabc-staging/monitor-staging.sh"
log ""
log "🔗 Staging will be available at: https://staging.yourdomain.com"
log "📊 Admin access: https://staging.yourdomain.com/admin/"
log "🎣 Test with fake data automatically loaded"