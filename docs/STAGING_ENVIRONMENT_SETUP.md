# SABC Staging Environment Setup Guide

## Overview

This guide provides comprehensive steps to create a staging environment that mirrors production for the SABC tournament management system.

## Prerequisites

- DigitalOcean account (or similar VPS provider)
- Domain name with DNS management access
- GitHub repository with proper secrets configured
- SSH key pair for server access

## Step 1: Create Digital Ocean Droplet

### 1.1 Droplet Specifications
```bash
# Recommended specs for staging:
- OS: Ubuntu 22.04 LTS
- Size: Basic Plan, Regular Intel CPU
- CPU: 2 vCPUs
- Memory: 4 GB
- SSD: 80 GB
- Region: Choose closest to your users
- Monitoring: Enable
- Backups: Enable (optional but recommended)
```

### 1.2 Initial Server Setup
```bash
# Connect to your new droplet
ssh root@your-staging-server-ip

# Update system
apt update && apt upgrade -y

# Create non-root user
adduser deploy
usermod -aG sudo deploy

# Set up SSH key for deploy user
mkdir -p /home/deploy/.ssh
cp ~/.ssh/authorized_keys /home/deploy/.ssh/
chown -R deploy:deploy /home/deploy/.ssh
chmod 700 /home/deploy/.ssh
chmod 600 /home/deploy/.ssh/authorized_keys

# Test SSH access with deploy user
exit
ssh deploy@your-staging-server-ip
```

## Step 2: Configure DNS

### 2.1 Add DNS Records
Add the following DNS records to your domain:
```
A Record:
  Name: staging
  Value: your-staging-server-ip
  TTL: 300 (5 minutes)

CNAME Record (optional):
  Name: staging-www
  Value: staging.yourdomain.com
  TTL: 300
```

### 2.2 Verify DNS Propagation
```bash
# Check DNS resolution
nslookup staging.yourdomain.com
dig staging.yourdomain.com
```

## Step 3: Run Staging Setup Script

### 3.1 Download and Execute Setup Script
```bash
# Connect to staging server as deploy user
ssh deploy@staging.yourdomain.com

# Download setup script
wget https://raw.githubusercontent.com/your-username/SABC_II/master/scripts/setup-staging.sh

# Make executable and run
chmod +x setup-staging.sh
./setup-staging.sh
```

### 3.2 Post-Setup Configuration
```bash
# Update git clone URL in the script
sudo -u sabc-staging git remote set-url origin https://github.com/your-username/SABC_II.git

# Update domain name in Nginx config
sudo sed -i 's/staging.yourdomain.com/staging.your-actual-domain.com/g' /etc/nginx/sites-available/sabc-staging

# Restart Nginx
sudo nginx -t
sudo systemctl restart nginx
```

## Step 4: Configure SSL Certificate

### 4.1 Install SSL Certificate
```bash
# Install certbot certificate
sudo certbot --nginx -d staging.your-actual-domain.com

# Verify auto-renewal
sudo certbot renew --dry-run
```

### 4.2 Update Nginx Configuration for HTTPS
The certbot will automatically update the Nginx configuration, but verify the final config:
```bash
sudo cat /etc/nginx/sites-available/sabc-staging
```

## Step 5: Configure GitHub Secrets

### 5.1 Required GitHub Secrets
Add these secrets to your GitHub repository (`Settings > Secrets and variables > Actions`):

```yaml
STAGING_HOST: staging.your-actual-domain.com
STAGING_USER: sabc-staging
STAGING_SSH_KEY: |
  -----BEGIN OPENSSH PRIVATE KEY-----
  [Your private SSH key content]
  -----END OPENSSH PRIVATE KEY-----
```

### 5.2 Generate SSH Key for GitHub Actions
```bash
# On your local machine
ssh-keygen -t ed25519 -C "github-actions@staging" -f ~/.ssh/sabc_staging_key

# Copy public key to staging server
ssh-copy-id -i ~/.ssh/sabc_staging_key.pub sabc-staging@staging.your-actual-domain.com

# Add private key to GitHub secrets (content of ~/.ssh/sabc_staging_key)
cat ~/.ssh/sabc_staging_key
```

## Step 6: Configure Environment Variables

### 6.1 Update Staging Service Environment
```bash
# Edit systemd service file
sudo nano /etc/systemd/system/sabc-staging.service

# Update these environment variables:
Environment=SECRET_KEY=your-secure-staging-secret-key
Environment=ALLOWED_HOSTS=staging.your-actual-domain.com,localhost,127.0.0.1
Environment=POSTGRES_PASSWORD=your-secure-staging-db-password

# Reload systemd and restart service
sudo systemctl daemon-reload
sudo systemctl restart sabc-staging
```

### 6.2 Update Database Password
```bash
# Update PostgreSQL password
sudo -u postgres psql
postgres=# ALTER USER sabc_staging_user PASSWORD 'your-secure-staging-db-password';
postgres=# \q
```

## Step 7: Initial Deployment

### 7.1 Manual First Deployment
```bash
# Run initial deployment as sabc-staging user
sudo -u sabc-staging /home/sabc-staging/deploy-staging.sh
```

### 7.2 Verify Deployment
```bash
# Check service status
sudo systemctl status sabc-staging

# Check application health
curl https://staging.your-actual-domain.com/health/

# Monitor logs
sudo journalctl -u sabc-staging -f
```

## Step 8: Test Automated Deployment

### 8.1 Trigger GitHub Actions Deployment
```bash
# Push to develop branch or create PR with 'deploy-staging' label
git checkout develop
git push origin develop
```

### 8.2 Monitor Deployment
- Check GitHub Actions tab in your repository
- Monitor staging server logs during deployment
- Verify application functionality after deployment

## Step 9: Monitoring and Maintenance

### 9.1 Set Up Monitoring Script
```bash
# Run monitoring script
sudo -u sabc-staging /home/sabc-staging/monitor-staging.sh

# Add to crontab for regular monitoring
sudo -u sabc-staging crontab -e
# Add line: */15 * * * * /home/sabc-staging/monitor-staging.sh >> /home/sabc-staging/logs/monitor.log 2>&1
```

### 9.2 Log Management
```bash
# View application logs
sudo journalctl -u sabc-staging --since "1 hour ago"

# View Nginx access logs
sudo tail -f /var/log/nginx/access.log

# View Nginx error logs
sudo tail -f /var/log/nginx/error.log
```

## Step 10: Backup and Recovery

### 10.1 Database Backup
```bash
# Create database backup script
sudo -u sabc-staging tee /home/sabc-staging/backup-db.sh > /dev/null << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/sabc-staging/backups/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"
BACKUP_FILE="$BACKUP_DIR/sabc_staging_$(date +%Y%m%d_%H%M%S).sql"
pg_dump -h localhost -U sabc_staging_user sabc_staging > "$BACKUP_FILE"
gzip "$BACKUP_FILE"
echo "Backup created: ${BACKUP_FILE}.gz"
# Keep only last 7 days of backups
find /home/sabc-staging/backups -type f -name "*.sql.gz" -mtime +7 -delete
EOF

chmod +x /home/sabc-staging/backup-db.sh

# Add to daily cron
sudo -u sabc-staging crontab -e
# Add line: 0 2 * * * /home/sabc-staging/backup-db.sh >> /home/sabc-staging/logs/backup.log 2>&1
```

### 10.2 Application Backup
```bash
# Create application backup script
sudo -u sabc-staging tee /home/sabc-staging/backup-app.sh > /dev/null << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/sabc-staging/backups/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"
cd /home/sabc-staging/app/SABC_II/SABC
tar -czf "$BACKUP_DIR/sabc_app_$(date +%Y%m%d_%H%M%S).tar.gz" \
    --exclude='.git' \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='staticfiles' \
    .
echo "Application backup created: $BACKUP_DIR/sabc_app_$(date +%Y%m%d_%H%M%S).tar.gz"
EOF

chmod +x /home/sabc-staging/backup-app.sh
```

## Step 11: Security Hardening

### 11.1 Firewall Configuration
```bash
# Configure UFW firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw enable
sudo ufw status
```

### 11.2 Fail2Ban Setup
```bash
# Install and configure fail2ban
sudo apt install fail2ban
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### 11.3 Security Updates
```bash
# Enable automatic security updates
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

## Step 12: Testing and Validation

### 12.1 Functional Testing Checklist
- [ ] Application loads at https://staging.your-actual-domain.com
- [ ] Health check endpoint responds correctly
- [ ] User registration and login works
- [ ] Tournament creation and management functions
- [ ] Database operations work correctly
- [ ] Static files serve properly
- [ ] SSL certificate is valid and secure

### 12.2 Performance Testing
```bash
# Basic performance test with curl
time curl -o /dev/null -s -w "%{http_code} %{time_total}\n" https://staging.your-actual-domain.com/

# Load test with Apache Bench (if installed)
ab -n 100 -c 10 https://staging.your-actual-domain.com/
```

### 12.3 Security Testing
```bash
# SSL test
sslscan staging.your-actual-domain.com

# Basic security headers check
curl -I https://staging.your-actual-domain.com
```

## Troubleshooting

### Common Issues and Solutions

1. **Application won't start**
   ```bash
   sudo journalctl -u sabc-staging -n 50
   sudo -u sabc-staging nix develop -c python /home/sabc-staging/app/SABC_II/SABC/sabc/manage.py check
   ```

2. **Database connection issues**
   ```bash
   sudo -u postgres psql -l
   sudo -u sabc-staging psql -h localhost -U sabc_staging_user -d sabc_staging
   ```

3. **Nginx configuration issues**
   ```bash
   sudo nginx -t
   sudo systemctl status nginx
   ```

4. **SSL certificate issues**
   ```bash
   sudo certbot certificates
   sudo certbot renew --dry-run
   ```

## Maintenance Schedule

### Daily
- Monitor application health and logs
- Check disk usage and system resources

### Weekly
- Review backup integrity
- Update system packages
- Monitor SSL certificate expiry

### Monthly
- Security audit
- Performance review
- Backup retention cleanup

## Next Steps

After completing this staging environment setup:
1. Configure staging data refresh procedures
2. Set up end-to-end testing automation
3. Implement staging-to-production promotion process
4. Document rollback procedures
5. Begin Phase 4: Advanced Features & Scalability

## Support

For issues with this setup:
1. Check application logs: `sudo journalctl -u sabc-staging -f`
2. Run monitoring script: `sudo -u sabc-staging /home/sabc-staging/monitor-staging.sh`
3. Verify GitHub Actions deployment logs
4. Review this documentation for troubleshooting steps