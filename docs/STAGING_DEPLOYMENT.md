# Staging Deployment Guide - Docker Compose on Digital Ocean Droplet

This guide covers setting up a staging environment that mirrors your production deployment using Docker Compose on a Digital Ocean Droplet.

## Current Production Setup

Your production deployment uses:
- **Platform**: Digital Ocean Droplet (VPS)
- **Deployment**: Docker Compose with 4 containers
  - `sabc-web` - FastAPI application
  - `sabc-postgres` - PostgreSQL 17 database
  - `sabc-nginx` - Nginx reverse proxy with SSL
  - `sabc-certbot` - Let's Encrypt SSL certificate management
- **Deployment Method**: SSH → git pull → [restart.sh](restart.sh)

## Staging Environment Options

### Option 1: Separate Droplet (Recommended)

Set up a completely separate staging droplet that mirrors production.

**Pros:**
- Complete isolation from production
- Identical deployment process
- Real-world testing environment
- Can test system updates

**Cons:**
- Additional cost (~$6-12/month for basic droplet)
- More infrastructure to manage

**Cost:** ~$6/month (Basic Droplet) + ~$0 (included bandwidth)

### Option 2: Same Droplet, Different Ports

Run staging containers alongside production on the same droplet.

**Pros:**
- No additional cost
- Same server environment

**Cons:**
- Resource sharing with production
- Less isolation
- Port conflicts to manage

**Cost:** $0 (uses existing droplet)

### Option 3: Local Docker Staging

Use Docker Compose locally to simulate production.

**Pros:**
- No additional cost
- Fast iteration
- Offline testing

**Cons:**
- Not internet-accessible for stakeholders
- Different environment from production

**Cost:** $0

## Recommended: Separate Staging Droplet

### Step 1: Create Staging Droplet

1. **Go to Digital Ocean Console** → Droplets → Create Droplet

2. **Choose Configuration:**
   - **Image**: Ubuntu 24.04 LTS
   - **Plan**: Basic - $6/month (1 GB RAM, 1 vCPU, 25 GB SSD)
   - **Datacenter**: Same region as production (for consistency)
   - **Authentication**: SSH Key (reuse your production key)
   - **Hostname**: `sabc-staging`

3. **Wait for Provisioning** (1-2 minutes)

4. **Note the IP Address** (e.g., 159.65.123.45)

### Step 2: Initial Server Setup

```bash
# SSH into staging droplet
ssh root@<staging-ip>

# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
apt install docker-compose-plugin -y

# Verify installation
docker --version
docker compose version

# Create deployment directory
mkdir -p /opt/sabc
cd /opt/sabc

# Create environment file
touch .env
chmod 600 .env
```

### Step 3: Configure Staging Environment

Create `/opt/sabc/.env` with staging-specific values:

```bash
# Database
DB_PASSWORD=<generate-new-password>

# Application Security
SECRET_KEY=<generate-new-64-char-key>
LOG_LEVEL=DEBUG
DEBUG=false

# SMTP (can reuse production or use staging account)
SMTP_USERNAME=<staging-smtp-username>
SMTP_PASSWORD=<staging-smtp-password>
FROM_EMAIL=staging@saustinbc.com

# Website URL
WEBSITE_URL=https://staging.saustinbc.com

# Sentry (optional - use separate project for staging)
SENTRY_DSN=<staging-sentry-dsn>
ENVIRONMENT=staging
```

**Generate secure secrets:**
```bash
# Generate DB password
openssl rand -base64 32

# Generate SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

### Step 4: Clone Repository

```bash
cd /opt/sabc

# Clone from GitHub
git clone https://github.com/your-org/SABC.git .

# Or clone from production droplet
git clone root@<production-ip>:/opt/sabc .

# Checkout staging branch
git checkout -b staging
git pull origin staging  # if staging branch exists remotely
```

### Step 5: Create Staging Docker Compose

You can use the same `docker-compose.prod.yml` but with staging environment variables from `.env`.

Optionally, create `docker-compose.staging.yml` with staging-specific tweaks:

```yaml
# docker-compose.staging.yml
services:
  web:
    build:
      context: .
      dockerfile: Dockerfile.prod
    container_name: sabc-staging-web
    restart: always
    environment:
      DATABASE_URL: postgresql://sabc_user:${DB_PASSWORD}@postgres:5432/sabc
      SECRET_KEY: ${SECRET_KEY}
      LOG_LEVEL: ${LOG_LEVEL:-DEBUG}
      DEBUG: ${DEBUG:-false}
      SMTP_USERNAME: ${SMTP_USERNAME}
      SMTP_PASSWORD: ${SMTP_PASSWORD}
      FROM_EMAIL: ${FROM_EMAIL}
      WEBSITE_URL: ${WEBSITE_URL}
      ENVIRONMENT: staging
      SENTRY_DSN: ${SENTRY_DSN:-}
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./static:/app/static:ro
    networks:
      - sabc-network

  postgres:
    image: postgres:17-alpine
    container_name: sabc-staging-postgres
    restart: always
    environment:
      POSTGRES_DB: sabc
      POSTGRES_USER: sabc_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U sabc_user -d sabc"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - sabc-network

  nginx:
    image: nginx:alpine
    container_name: sabc-staging-nginx
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx-https.conf:/etc/nginx/nginx.conf:ro
      - ./static:/usr/share/nginx/html/static:ro
      - ./ssl:/etc/nginx/ssl:ro
      - nginx_cache:/var/cache/nginx
      - certbot_webroot:/var/www/certbot:ro
    depends_on:
      - web
    networks:
      - sabc-network

  certbot:
    image: certbot/certbot
    container_name: sabc-staging-certbot
    volumes:
      - ./ssl:/etc/letsencrypt
      - certbot_webroot:/var/www/certbot
    command: echo "Certbot container for certificate renewal"

volumes:
  postgres_data:
  nginx_cache:
  certbot_webroot:

networks:
  sabc-network:
    driver: bridge
```

### Step 6: Configure DNS

Point a subdomain to your staging droplet:

1. **In your DNS provider** (e.g., Namecheap, Cloudflare):
   ```
   Type: A Record
   Name: staging
   Value: <staging-droplet-ip>
   TTL: 300
   ```

2. **Wait for DNS propagation** (5-30 minutes)
   ```bash
   # Test DNS resolution
   dig staging.saustinbc.com
   ```

### Step 7: Configure SSL Certificate

```bash
cd /opt/sabc

# Install Certbot (if not using container)
apt install certbot python3-certbot-nginx -y

# Get SSL certificate for staging subdomain
certbot certonly --standalone \
  --preferred-challenges http \
  -d staging.saustinbc.com \
  --email your-email@example.com \
  --agree-tos \
  --non-interactive

# Or use the certbot container
docker compose -f docker-compose.staging.yml run --rm certbot \
  certonly --webroot \
  -w /var/www/certbot \
  -d staging.saustinbc.com \
  --email your-email@example.com \
  --agree-tos \
  --non-interactive
```

### Step 8: Update Nginx Configuration

Update `nginx-https.conf` to use the staging domain:

```nginx
server {
    listen 80;
    server_name staging.saustinbc.com;

    # Redirect HTTP to HTTPS
    location / {
        return 301 https://$host$request_uri;
    }

    # Let's Encrypt verification
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
}

server {
    listen 443 ssl http2;
    server_name staging.saustinbc.com;

    ssl_certificate /etc/letsencrypt/live/staging.saustinbc.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/staging.saustinbc.com/privkey.pem;

    # ... rest of your nginx config
}
```

### Step 9: Initial Deployment

```bash
cd /opt/sabc

# Build and start containers
docker compose -f docker-compose.staging.yml up -d --build

# Check logs
docker compose -f docker-compose.staging.yml logs -f

# Verify containers are running
docker compose -f docker-compose.staging.yml ps
```

### Step 10: Seed Test Data

```bash
# Copy seed script to staging
scp scripts/seed_staging_data.py root@<staging-ip>:/opt/sabc/scripts/

# SSH into staging
ssh root@<staging-ip>

# Run seed script
cd /opt/sabc
docker compose -f docker-compose.staging.yml exec web \
  python scripts/seed_staging_data.py
```

## Staging Deployment Workflow

### Deploy New Changes to Staging

```bash
# On your local machine
git checkout staging
git merge master  # or merge feature branch
git push origin staging

# SSH into staging droplet
ssh root@<staging-ip>
cd /opt/sabc

# Pull latest code
git pull origin staging

# Restart containers
./restart.sh
# Or manually:
docker compose -f docker-compose.staging.yml down
docker compose -f docker-compose.staging.yml up -d --build
```

### Create `restart-staging.sh`

```bash
#!/usr/bin/bash
# restart-staging.sh - Staging deployment script

cd /opt/sabc

docker compose -f docker-compose.staging.yml down && \
  git pull origin staging && \
  docker compose -f docker-compose.staging.yml build --no-cache && \
  docker compose -f docker-compose.staging.yml up -d && \
  docker system prune -f && \
  sudo journalctl --vacuum-time=7d && \
  sudo apt clean

echo "✅ Staging deployment complete!"
echo "🌐 Visit: https://staging.saustinbc.com"
```

Make it executable:
```bash
chmod +x restart-staging.sh
```

## Testing on Staging

### Manual Testing Checklist

```bash
# SSH into staging
ssh root@<staging-ip>

# Check application logs
docker compose -f docker-compose.staging.yml logs web -f

# Check database
docker compose -f docker-compose.staging.yml exec postgres \
  psql -U sabc_user -d sabc -c "SELECT COUNT(*) FROM anglers;"

# Run migrations
docker compose -f docker-compose.staging.yml exec web \
  alembic current

# Test email sending (if configured)
docker compose -f docker-compose.staging.yml exec web \
  python -c "from core.email.service import send_test_email; send_test_email()"
```

### Access Staging Application

Visit: **https://staging.saustinbc.com**

Test credentials:
- **Admin**: admin@staging.sabc.test / TestPassword123!
- **Members**: member1-10@staging.sabc.test / TestPassword123!

## Promoting Staging to Production

Once staging validates successfully:

```bash
# Merge staging to master
git checkout master
git merge staging
git push origin master

# SSH into production
ssh root@<production-ip>
cd /opt/sabc

# Deploy to production
./restart.sh
```

## Maintenance

### Reset Staging Database

```bash
# SSH into staging
ssh root@<staging-ip>
cd /opt/sabc

# Run reset script
./scripts/reset_staging_db.sh

# Or manually:
docker compose -f docker-compose.staging.yml exec postgres \
  psql -U sabc_user -d sabc -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

docker compose -f docker-compose.staging.yml exec web \
  alembic upgrade head

docker compose -f docker-compose.staging.yml exec web \
  python scripts/seed_staging_data.py
```

### Backup Staging Database

```bash
# Create backup
docker compose -f docker-compose.staging.yml exec postgres \
  pg_dump -U sabc_user sabc > staging-backup-$(date +%Y%m%d).sql

# Restore from backup
docker compose -f docker-compose.staging.yml exec -T postgres \
  psql -U sabc_user sabc < staging-backup-20250109.sql
```

### Update Docker Images

```bash
# Pull latest base images
docker compose -f docker-compose.staging.yml pull

# Rebuild and restart
docker compose -f docker-compose.staging.yml up -d --build
```

## Cost Breakdown

| Component | Cost |
|-----------|------|
| Staging Droplet (1GB) | $6/month |
| Bandwidth (included) | $0/month |
| DNS (included with domain) | $0/month |
| SSL Certificate (Let's Encrypt) | $0/month |
| **Total** | **$6/month** |

## Security Considerations

1. **Different Credentials**: Use separate DB_PASSWORD, SECRET_KEY, SMTP credentials
2. **Firewall**: Configure UFW to allow only 80, 443, and SSH
   ```bash
   ufw allow 22/tcp
   ufw allow 80/tcp
   ufw allow 443/tcp
   ufw enable
   ```
3. **SSH Keys**: Use same SSH key as production (or separate if preferred)
4. **Test Data Only**: Never put real member data in staging
5. **Separate Sentry**: Use different Sentry project for staging alerts

## Troubleshooting

### Containers Won't Start

```bash
# Check logs
docker compose -f docker-compose.staging.yml logs

# Check individual service
docker compose -f docker-compose.staging.yml logs web
docker compose -f docker-compose.staging.yml logs postgres
```

### Database Connection Issues

```bash
# Test database connection
docker compose -f docker-compose.staging.yml exec postgres \
  psql -U sabc_user -d sabc

# Check DATABASE_URL
docker compose -f docker-compose.staging.yml exec web \
  printenv DATABASE_URL
```

### SSL Certificate Issues

```bash
# Test certificate
openssl s_client -connect staging.saustinbc.com:443 -servername staging.saustinbc.com

# Renew certificate
certbot renew
```

## CI/CD Integration

The existing [.github/workflows/deploy-staging.yml](.github/workflows/deploy-staging.yml) validates code quality before deployment. Actual deployment happens manually via SSH and `restart-staging.sh`.

For automatic deployment, you could add:

```yaml
# .github/workflows/deploy-staging.yml (additional step)
- name: Deploy to staging
  if: success()
  run: |
    ssh -o StrictHostKeyChecking=no root@${{ secrets.STAGING_IP }} \
      'cd /opt/sabc && ./restart-staging.sh'
  env:
    STAGING_IP: ${{ secrets.STAGING_IP }}
```

Requires setting up:
1. SSH key in GitHub Actions secrets
2. `STAGING_IP` secret with your staging droplet IP

---

**Last Updated**: 2025-10-09
**Environment**: Staging (Docker Compose on Droplet)
**Status**: Ready to deploy
