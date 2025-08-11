# GitHub Actions Deployment Setup Guide

This guide walks through setting up the complete CI/CD pipeline for SABC with GitHub Actions.

## 🔧 Repository Configuration

### 1. GitHub Secrets Setup

Navigate to your repository → Settings → Secrets and Variables → Actions

#### Required Secrets for Deployment:

```bash
# Server Connection
DEPLOY_HOST         # Your Digital Ocean droplet IP or domain
DEPLOY_USER         # SSH username (e.g., 'sabc' or 'ubuntu')
DEPLOY_SSH_KEY      # Private SSH key content (see SSH setup below)

# Optional but Recommended
CODECOV_TOKEN       # For coverage reporting (get from codecov.io)
```

#### Optional Notification Secrets:
```bash
SLACK_WEBHOOK       # For deployment notifications
DISCORD_WEBHOOK     # Alternative notification channel
```

### 2. GitHub Environments Setup

Create these environments in Repository → Settings → Environments:

#### Production Environment
- **Name**: `production`
- **Protection Rules**:
  - ✅ Required reviewers: Add repository maintainers
  - ✅ Restrict to protected branches: `master`
  - ✅ Wait timer: 0 minutes (or add delay for verification)
- **Environment Secrets**: Add production-specific values if different from repository secrets

#### Staging Environment
- **Name**: `staging` 
- **Protection Rules**: None (for automatic deployment)
- **Environment Secrets**: Staging server credentials if using separate server

## 🔑 SSH Key Setup

### Generate Deployment Key

```bash
# Generate a new SSH key pair for deployments
ssh-keygen -t ed25519 -C "github-actions-sabc-deploy" -f ~/.ssh/sabc_deploy_key

# Copy public key to your server
ssh-copy-id -i ~/.ssh/sabc_deploy_key.pub your-user@your-server.com

# Test the connection
ssh -i ~/.ssh/sabc_deploy_key your-user@your-server.com "echo 'Connection successful'"
```

### Add Private Key to GitHub Secrets

```bash
# Copy the private key content
cat ~/.ssh/sabc_deploy_key

# Copy the entire output (including -----BEGIN and -----END lines)
# Add it as the DEPLOY_SSH_KEY secret in GitHub
```

## 🖥️ Server Setup

### 1. Service Configuration

Create a systemd service file for your application:

```bash
# /etc/systemd/system/sabc-web.service
[Unit]
Description=SABC Django Application
After=network.target

[Service]
User=sabc
Group=sabc
WorkingDirectory=/home/sabc/SABC_II/SABC/sabc
Environment=DJANGO_SETTINGS_MODULE=sabc.settings
Environment=SECRET_KEY=your-production-secret-key
Environment=ALLOWED_HOSTS=your-domain.com,www.your-domain.com
Environment=DEBUG=False
Environment=POSTGRES_DB=sabc
Environment=POSTGRES_USER=postgres
Environment=POSTGRES_PASSWORD=your-db-password
ExecStart=/home/sabc/.nix-profile/bin/nix develop -c python manage.py runserver 0.0.0.0:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

### 2. Enable and Start Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable sabc-web
sudo systemctl start sabc-web
sudo systemctl status sabc-web
```

### 3. Web Server Configuration (Nginx)

```nginx
# /etc/nginx/sites-available/sabc
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;
    
    # SSL configuration
    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;
    
    # Static files
    location /static/ {
        alias /home/sabc/SABC_II/SABC/sabc/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # Media files
    location /media/ {
        alias /home/sabc/SABC_II/SABC/sabc/media/;
        expires 7d;
    }
    
    # Health check endpoint (bypass Django for faster response)
    location /health/ {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
    
    # Application
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 4. Enable Nginx Site

```bash
sudo ln -s /etc/nginx/sites-available/sabc /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 📊 Monitoring Setup

### 1. Health Check Endpoint

Ensure your Django application has a health check endpoint:

```python
# sabc/urls.py
from django.urls import path, include
from core.views import health_check

urlpatterns = [
    path('health/', health_check, name='health'),
    # ... other URLs
]
```

### 2. Log Monitoring

Set up log rotation for application logs:

```bash
# /etc/logrotate.d/sabc
/home/sabc/logs/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 sabc sabc
    postrotate
        systemctl reload sabc-web
    endscript
}
```

## 🧪 Testing the Pipeline

### 1. Test SSH Connection

```bash
# From your local machine
ssh -i ~/.ssh/sabc_deploy_key your-user@your-server.com "whoami && cd ~/SABC_II/SABC && git status"
```

### 2. Test Manual Deployment

```bash
# Use the included deployment script
./scripts/deploy.sh test
./scripts/deploy.sh deploy --dry-run
```

### 3. Test GitHub Actions

1. Create a test branch
2. Make a small change
3. Push the branch
4. Create a PR to `develop` 
5. Verify all CI checks pass
6. Merge to `develop` to test staging deployment
7. Create PR from `develop` to `master` to test production deployment

## 🚨 Troubleshooting

### Common Issues

#### SSH Connection Issues
```bash
# Test SSH connectivity
ssh -i ~/.ssh/sabc_deploy_key -v your-user@your-server.com

# Check SSH agent
ssh-add ~/.ssh/sabc_deploy_key
ssh-add -l
```

#### Service Start Issues
```bash
# Check service logs
sudo journalctl -u sabc-web -f

# Check application logs
tail -f /home/sabc/logs/application.log
```

#### Permission Issues
```bash
# Fix file permissions
sudo chown -R sabc:sabc /home/sabc/SABC_II/
sudo chmod -R 755 /home/sabc/SABC_II/
```

### GitHub Actions Debug

Enable debug logging by adding these repository variables:
```
ACTIONS_STEP_DEBUG = true
ACTIONS_RUNNER_DEBUG = true
```

## 📋 Deployment Checklist

Before going live with automated deployments:

- [ ] SSH key authentication working
- [ ] Manual deployment script works
- [ ] Database backups are automated
- [ ] Service management (systemctl) configured
- [ ] Web server (nginx) configured with SSL
- [ ] Health check endpoint responding
- [ ] Log rotation configured
- [ ] Monitoring and alerting set up
- [ ] Rollback procedure tested
- [ ] GitHub environments configured
- [ ] All required secrets added
- [ ] Test deployment to staging successful

## 🔄 Maintenance

### Weekly Tasks (Automated)
- Dependency vulnerability scanning
- Performance regression testing
- Database backup verification
- Log rotation and cleanup

### Monthly Tasks (Manual)
- Review deployment logs
- Update dependencies
- SSL certificate renewal check
- Server security updates
- Performance optimization review

---

For additional help or questions, create an issue in the repository with the `ci-cd` label.