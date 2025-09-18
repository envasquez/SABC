# SABC Docker Deployment Guide

## Quick Start - Test Locally First

### 1. Test the production deployment locally:
```bash
./test-deployment-local.sh
```

This will:
- Build production containers
- Start PostgreSQL, Web App, and Nginx
- Initialize the database
- Run health checks
- Show you the logs

Access the app at:
- http://localhost (through Nginx)
- http://localhost:8000 (direct to app)

### 2. Run quick smoke tests:
```bash
./test-deployment-quick.sh
```

### 3. Stop local test:
```bash
docker compose -f docker-compose.prod.yml --env-file .env.local-test down -v
```

## Deploy to Production

### Step 1: Create Digital Ocean Droplet
- Go to Digital Ocean → Create Droplet
- Choose: Marketplace → Docker on Ubuntu 24.04
- Select: Basic plan ($6/month)
- Add your SSH key
- Create droplet

### Step 2: Deploy with one command
```bash
./deploy-docker.sh your-droplet-ip
```

### Step 3: Configure production settings
```bash
# SSH into your droplet
ssh root@your-droplet-ip

# Edit production settings
cd /opt/sabc
nano .env.production

# Update these values:
DB_PASSWORD=<strong-password>
SECRET_KEY=<generate-random-64-char-string>
DOMAIN=your-domain.com
```

### Step 4: Restart with new settings
```bash
docker compose -f docker-compose.prod.yml --env-file .env.production restart
```

## Daily Operations

### View logs:
```bash
docker compose -f docker-compose.prod.yml logs -f
```

### Update code:
```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

### Backup database:
```bash
docker compose -f docker-compose.prod.yml exec postgres \
  pg_dump -U sabc_user sabc > backup_$(date +%Y%m%d).sql
```

### Restore database:
```bash
cat backup.sql | docker compose -f docker-compose.prod.yml exec -T postgres \
  psql -U sabc_user sabc
```

### Enter containers:
```bash
# Web app shell
docker compose -f docker-compose.prod.yml exec web bash

# Database shell
docker compose -f docker-compose.prod.yml exec postgres psql -U sabc_user -d sabc
```

## SSL Setup (Production)

### Option 1: Let's Encrypt (Free)
```bash
# Install certbot on droplet
apt install certbot -y

# Get certificate
certbot certonly --standalone -d your-domain.com -d www.your-domain.com

# Certificates will be in:
# /etc/letsencrypt/live/your-domain.com/

# Update nginx.conf - uncomment HTTPS section and update paths
nano nginx.conf

# Restart nginx
docker compose -f docker-compose.prod.yml restart nginx
```

### Option 2: Cloudflare (Recommended)
- Add your domain to Cloudflare
- Enable "Full SSL" mode
- Cloudflare handles SSL automatically

## Troubleshooting

### Check container status:
```bash
docker compose -f docker-compose.prod.yml ps
```

### Check specific service logs:
```bash
docker compose -f docker-compose.prod.yml logs web
docker compose -f docker-compose.prod.yml logs postgres
docker compose -f docker-compose.prod.yml logs nginx
```

### Restart everything:
```bash
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d
```

### Reset database (WARNING: Deletes all data):
```bash
docker compose -f docker-compose.prod.yml down -v
docker compose -f docker-compose.prod.yml up -d
```

### Check disk space:
```bash
df -h
docker system df
```

### Clean up Docker:
```bash
docker system prune -a
```

## Environment Variables

### Required in .env.production:
```bash
# Database
DB_PASSWORD=strong_password_here

# Application
SECRET_KEY=generate_64_char_random_string
LOG_LEVEL=INFO
DEBUG=false

# Domain (for SSL)
DOMAIN=your-domain.com
```

### Generate secure values:
```bash
# Generate SECRET_KEY
python3 -c "import secrets; print(secrets.token_hex(32))"

# Generate DB_PASSWORD
openssl rand -base64 32
```

## Performance Monitoring

### Check resource usage:
```bash
docker stats
```

### Check application metrics:
```bash
# Response time
time curl -I http://localhost/health

# Load test (install apache2-utils first)
ab -n 100 -c 10 http://localhost/
```

## Backup Strategy

### Automated daily backups:
```bash
# Create backup script
cat > /opt/sabc/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/sabc/backups"
mkdir -p $BACKUP_DIR
cd /opt/sabc
docker compose -f docker-compose.prod.yml exec -T postgres \
  pg_dump -U sabc_user sabc | gzip > $BACKUP_DIR/sabc_$(date +%Y%m%d_%H%M%S).sql.gz
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete
EOF

chmod +x /opt/sabc/backup.sh

# Add to crontab
crontab -e
# Add: 0 2 * * * /opt/sabc/backup.sh
```

## Security Checklist

- [ ] Changed default passwords in .env.production
- [ ] Generated strong SECRET_KEY
- [ ] Configured firewall (ufw)
- [ ] Set up SSL certificate
- [ ] Regular security updates: `apt update && apt upgrade`
- [ ] Monitoring logs for suspicious activity
- [ ] Regular backups configured

## Support

For issues, check:
1. Application logs: `docker compose logs web`
2. Database logs: `docker compose logs postgres`
3. Nginx logs: `docker compose logs nginx`
4. GitHub Issues: https://github.com/envasquez/SABC/issues