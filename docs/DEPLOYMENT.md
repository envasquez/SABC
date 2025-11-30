# Deployment Guide - SABC Tournament Management

## Overview

This guide covers deploying the SABC Tournament Management System to production environments. The recommended deployment method uses Docker Compose on a Digital Ocean Droplet.

---

## Table of Contents

1. [Deployment Options](#deployment-options)
2. [Prerequisites](#prerequisites)
3. [Production Deployment (Docker)](#production-deployment-docker)
4. [Environment Variables](#environment-variables)
5. [SSL/TLS Setup](#ssltls-setup)
6. [Database Management](#database-management)
7. [Monitoring Setup](#monitoring-setup)
8. [Backup and Recovery](#backup-and-recovery)
9. [Troubleshooting](#troubleshooting)

---

## Deployment Options

| Option | Cost | Complexity | Best For |
|--------|------|------------|----------|
| Docker on Droplet | ~$12/mo | Medium | Production (recommended) |
| Staging Droplet | ~$6/mo | Medium | Testing before production |
| App Platform | ~$18-30/mo | Low | Managed hosting preference |

---

## Prerequisites

### Server Requirements

- **OS**: Ubuntu 22.04 LTS or newer
- **RAM**: 2GB minimum (4GB recommended)
- **Storage**: 25GB SSD minimum
- **CPU**: 1 vCPU minimum (2 recommended)

### Software Requirements

- Docker 24.0+
- Docker Compose 2.20+
- Git
- Nginx (included in Docker setup)

### Domain and DNS

- A registered domain name
- DNS A record pointing to server IP
- Access to DNS settings for SSL verification

---

## Production Deployment (Docker)

### Step 1: Server Setup

```bash
# Connect to your server
ssh root@your-server-ip

# Update system packages
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
apt install docker-compose-plugin -y

# Verify installation
docker --version
docker compose version
```

### Step 2: Clone Repository

```bash
# Create application directory
mkdir -p /opt/sabc
cd /opt/sabc

# Clone the repository
git clone https://github.com/envasquez/SABC.git .

# Or if using SSH key
git clone git@github.com:envasquez/SABC.git .
```

### Step 3: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit environment variables
nano .env
```

**Required environment variables** (see [Environment Variables](#environment-variables) section):

```bash
# Database
DATABASE_URL=postgresql://sabc:your-secure-password@db:5432/sabc
DB_PASSWORD=your-secure-password

# Security
SECRET_KEY=your-64-character-random-string

# Email
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=noreply@yourdomain.com

# Application
WEBSITE_URL=https://yourdomain.com
ENVIRONMENT=production
```

### Step 4: SSL Certificate Setup

```bash
# Create certificate directories
mkdir -p certbot/conf certbot/www

# Get initial certificate (replace with your domain)
docker compose -f docker-compose.prod.yml run --rm certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  -d yourdomain.com \
  -d www.yourdomain.com \
  --email your-email@example.com \
  --agree-tos \
  --no-eff-email
```

### Step 5: Start Services

```bash
# Build and start all services
docker compose -f docker-compose.prod.yml up -d --build

# Check service status
docker compose -f docker-compose.prod.yml ps

# View logs
docker compose -f docker-compose.prod.yml logs -f
```

### Step 6: Initialize Database

```bash
# Run database setup
docker compose -f docker-compose.prod.yml exec web python scripts/setup_db.py

# Create admin user
docker compose -f docker-compose.prod.yml exec web python scripts/setup_admin.py
```

### Step 7: Verify Deployment

```bash
# Check health endpoint
curl -s https://yourdomain.com/health

# Expected response:
# {"status": "healthy", "database": "connected", "timestamp": "..."}
```

---

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:5432/db` |
| `DB_PASSWORD` | Database password | Secure random string |
| `SECRET_KEY` | Session encryption key | 64+ character random string |

### Email Configuration

| Variable | Description | Example |
|----------|-------------|---------|
| `SMTP_HOST` | SMTP server hostname | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP server port | `587` |
| `SMTP_USERNAME` | SMTP authentication username | `your-email@gmail.com` |
| `SMTP_PASSWORD` | SMTP authentication password | App-specific password |
| `FROM_EMAIL` | Sender email address | `noreply@yourdomain.com` |

### Application Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `WEBSITE_URL` | Public URL of the application | - |
| `ENVIRONMENT` | Environment name | `production` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `DEBUG` | Debug mode | `false` |

### Monitoring (Optional)

| Variable | Description | Example |
|----------|-------------|---------|
| `SENTRY_DSN` | Sentry project DSN | `https://xxx@sentry.io/yyy` |
| `RELEASE_VERSION` | Application version | `v1.2.3` |

### Generating Secure Secrets

```bash
# Generate SECRET_KEY (64 characters)
python -c "import secrets; print(secrets.token_urlsafe(48))"

# Generate DB_PASSWORD (32 characters)
python -c "import secrets; print(secrets.token_urlsafe(24))"
```

---

## SSL/TLS Setup

### Using Certbot (Let's Encrypt)

The Docker Compose setup includes Certbot for automatic SSL certificate management.

#### Initial Certificate

```bash
# Stop nginx temporarily
docker compose -f docker-compose.prod.yml stop nginx

# Obtain certificate
docker compose -f docker-compose.prod.yml run --rm certbot certonly \
  --standalone \
  -d yourdomain.com \
  --email admin@yourdomain.com \
  --agree-tos

# Start nginx
docker compose -f docker-compose.prod.yml start nginx
```

#### Certificate Renewal

Certificates auto-renew via cron job. Manual renewal:

```bash
# Test renewal
docker compose -f docker-compose.prod.yml run --rm certbot renew --dry-run

# Force renewal
docker compose -f docker-compose.prod.yml run --rm certbot renew --force-renewal

# Reload nginx after renewal
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

#### Automatic Renewal Cron

Add to `/etc/crontab`:

```cron
0 3 * * * root cd /opt/sabc && docker compose -f docker-compose.prod.yml run --rm certbot renew --quiet && docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

---

## Database Management

### Running Migrations

```bash
# Check current migration status
docker compose -f docker-compose.prod.yml exec web alembic current

# Apply pending migrations
docker compose -f docker-compose.prod.yml exec web alembic upgrade head

# Rollback one migration
docker compose -f docker-compose.prod.yml exec web alembic downgrade -1
```

### Database Backup

```bash
# Create backup
docker compose -f docker-compose.prod.yml exec db \
  pg_dump -U sabc sabc > backup_$(date +%Y%m%d_%H%M%S).sql

# Compress backup
gzip backup_*.sql
```

### Database Restore

```bash
# Stop application (keep database running)
docker compose -f docker-compose.prod.yml stop web

# Restore from backup
gunzip backup_20240315_120000.sql.gz
docker compose -f docker-compose.prod.yml exec -T db \
  psql -U sabc sabc < backup_20240315_120000.sql

# Restart application
docker compose -f docker-compose.prod.yml start web
```

### Automated Backups

Create `/opt/sabc/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR=/opt/sabc/backups
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Dump database
docker compose -f /opt/sabc/docker-compose.prod.yml exec -T db \
  pg_dump -U sabc sabc | gzip > $BACKUP_DIR/sabc_$DATE.sql.gz

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete

# Optional: Upload to remote storage
# aws s3 cp $BACKUP_DIR/sabc_$DATE.sql.gz s3://your-bucket/backups/
```

Add to crontab:
```cron
0 2 * * * /opt/sabc/backup.sh
```

---

## Monitoring Setup

### Sentry Error Tracking

1. Create account at [sentry.io](https://sentry.io)
2. Create new project (Python/FastAPI)
3. Copy DSN to environment:
   ```bash
   SENTRY_DSN=https://xxx@sentry.io/yyy
   ```
4. Restart application

### Prometheus Metrics

The application exposes metrics at `/metrics`. To collect:

1. Install Prometheus on monitoring server
2. Add scrape config:
   ```yaml
   scrape_configs:
     - job_name: 'sabc'
       static_configs:
         - targets: ['your-server-ip:8000']
       metrics_path: '/metrics'
   ```

**Security**: Restrict `/metrics` endpoint via firewall:
```bash
# Only allow monitoring server
ufw allow from monitoring-server-ip to any port 8000
```

### Health Checks

The `/health` endpoint returns application status:

```bash
# Basic health check
curl -s https://yourdomain.com/health | jq .

# Use in monitoring (e.g., UptimeRobot, Pingdom)
# URL: https://yourdomain.com/health
# Expected: 200 OK
```

---

## Updating the Application

### Standard Update Process

```bash
# Navigate to application directory
cd /opt/sabc

# Pull latest code
git pull origin master

# Rebuild and restart
docker compose -f docker-compose.prod.yml up -d --build

# Run any pending migrations
docker compose -f docker-compose.prod.yml exec web alembic upgrade head

# Verify health
curl -s https://yourdomain.com/health
```

### Using the Restart Script

The repository includes a convenience script:

```bash
./restart.sh
```

This script:
1. Pulls latest code
2. Rebuilds containers
3. Restarts services
4. Runs migrations
5. Verifies health

### Rollback Procedure

```bash
# View recent commits
git log --oneline -10

# Rollback to specific commit
git checkout <commit-hash>

# Rebuild and restart
docker compose -f docker-compose.prod.yml up -d --build

# Rollback database if needed
docker compose -f docker-compose.prod.yml exec web alembic downgrade -1
```

---

## Firewall Configuration

### UFW Setup

```bash
# Enable UFW
ufw enable

# Allow SSH
ufw allow 22

# Allow HTTP (for Let's Encrypt)
ufw allow 80

# Allow HTTPS
ufw allow 443

# Deny everything else
ufw default deny incoming
ufw default allow outgoing

# Check status
ufw status
```

### Docker and UFW

Docker manages its own iptables rules. For additional security:

```bash
# Edit Docker daemon config
nano /etc/docker/daemon.json

# Add:
{
  "iptables": true,
  "ip-forward": true
}

# Restart Docker
systemctl restart docker
```

---

## Troubleshooting

### Common Issues

#### Container Won't Start

```bash
# Check logs
docker compose -f docker-compose.prod.yml logs web

# Check if port is in use
lsof -i :8000

# Check Docker status
systemctl status docker
```

#### Database Connection Failed

```bash
# Check database container
docker compose -f docker-compose.prod.yml logs db

# Test connection
docker compose -f docker-compose.prod.yml exec db \
  psql -U sabc -c "SELECT 1"

# Check DATABASE_URL format
# Should be: postgresql://user:pass@db:5432/sabc
```

#### SSL Certificate Issues

```bash
# Check certificate status
docker compose -f docker-compose.prod.yml run --rm certbot certificates

# Check nginx config
docker compose -f docker-compose.prod.yml exec nginx nginx -t

# View nginx logs
docker compose -f docker-compose.prod.yml logs nginx
```

#### Out of Memory

```bash
# Check memory usage
docker stats

# Increase swap (if needed)
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

### Log Files

```bash
# Application logs
docker compose -f docker-compose.prod.yml logs web

# Database logs
docker compose -f docker-compose.prod.yml logs db

# Nginx logs
docker compose -f docker-compose.prod.yml logs nginx

# Follow logs in real-time
docker compose -f docker-compose.prod.yml logs -f --tail=100
```

### Debug Mode

**Warning**: Never enable in production for extended periods.

```bash
# Temporarily enable debug mode
export DEBUG=true
docker compose -f docker-compose.prod.yml up -d

# Disable after debugging
export DEBUG=false
docker compose -f docker-compose.prod.yml up -d
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] Domain DNS configured (A record pointing to server)
- [ ] Server provisioned and accessible via SSH
- [ ] Docker and Docker Compose installed
- [ ] Repository cloned to `/opt/sabc`
- [ ] Environment variables configured in `.env`
- [ ] Strong passwords generated for DATABASE and SECRET_KEY

### Deployment

- [ ] Docker containers built successfully
- [ ] Database container healthy
- [ ] SSL certificate obtained
- [ ] Database migrations applied
- [ ] Admin user created
- [ ] Health endpoint responding

### Post-Deployment

- [ ] Firewall configured (ports 22, 80, 443 only)
- [ ] Sentry monitoring configured
- [ ] Automated backups scheduled
- [ ] SSL renewal cron job added
- [ ] Uptime monitoring configured
- [ ] Documentation updated with server details

---

## Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [DATABASE_MIGRATIONS.md](DATABASE_MIGRATIONS.md) - Migration guide
- [MONITORING.md](MONITORING.md) - Monitoring setup
- [SECURITY.md](../SECURITY.md) - Security policies

---

**Last Updated**: 2024-11-30
