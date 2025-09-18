# 🐳 Docker Deployment Guide

Simple Docker deployment for SABC Tournament Management System.

## Quick Start

### 1. Install Docker
```bash
# On Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# On CentOS/RHEL
sudo yum install docker docker-compose

# Start Docker
sudo systemctl start docker
sudo systemctl enable docker
```

### 2. Clone and Deploy
```bash
# Clone the repository
git clone https://github.com/envasquez/SABC.git
cd SABC

# Copy environment template
cp .env.example .env

# Edit your secrets (IMPORTANT!)
nano .env
```

### 3. Set Your Secrets in .env
```bash
# Generate a secure database password
DB_PASSWORD=your_super_secure_database_password_2024

# Generate a secret key (32+ characters)
SECRET_KEY=your_very_long_random_secret_key_here_at_least_32_characters_long_2024
```

### 4. Start Everything
```bash
# Build and start all services
docker compose -f docker-compose.prod.yml up -d

# Check logs
docker compose -f docker-compose.prod.yml logs -f
```

### 5. Access Your Site
- **Application**: http://your-server-ip:8000
- **Admin Login**: `admin@sabc.com` / `admin123`

## What Gets Deployed

- **PostgreSQL 17** - Database with persistent storage
- **SABC App** - FastAPI application
- **Nginx** - Reverse proxy and static file serving
- **Auto-initialization** - Database, lakes, holidays, admin user

## Management Commands

```bash
# View logs
docker compose -f docker-compose.prod.yml logs -f web

# Stop everything
docker compose -f docker-compose.prod.yml down

# Update from git
git pull
docker compose -f docker-compose.prod.yml up -d --build

# Backup database
docker compose -f docker-compose.prod.yml exec postgres pg_dump -U sabc_user sabc > backup.sql

# Restore database
docker compose -f docker-compose.prod.yml exec -i postgres psql -U sabc_user sabc < backup.sql
```

## Production Checklist

- [ ] Set strong `DB_PASSWORD` in .env
- [ ] Set secure `SECRET_KEY` in .env
- [ ] Configure firewall (allow ports 80, 443, 8000)
- [ ] Set up SSL certificates in `./ssl/` directory
- [ ] Configure domain in nginx.conf
- [ ] Set up backups
- [ ] Monitor logs

## SSL/HTTPS Setup

1. Get SSL certificates (Let's Encrypt recommended)
2. Place in `./ssl/` directory:
   - `./ssl/cert.pem`
   - `./ssl/key.pem`
3. Update nginx.conf for HTTPS
4. Restart: `docker compose -f docker-compose.prod.yml restart nginx`

## Troubleshooting

**Database connection issues:**
```bash
# Check database is running
docker compose -f docker-compose.prod.yml ps

# Check database logs
docker compose -f docker-compose.prod.yml logs postgres
```

**Application not starting:**
```bash
# Check app logs
docker compose -f docker-compose.prod.yml logs web

# Restart app
docker compose -f docker-compose.prod.yml restart web
```

**Can't access site:**
- Check firewall settings
- Verify port 8000 is open
- Check nginx logs: `docker compose -f docker-compose.prod.yml logs nginx`

## Security Notes

- Change default admin password after first login
- Keep .env file secure (never commit to git)
- Regularly update Docker images
- Monitor access logs
- Set up fail2ban for additional protection

---

That's it! Your SABC tournament management system should be running. 🎣