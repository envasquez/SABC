# 🚀 SABC Digital Ocean Deployment Guide

## Complete Step-by-Step Deployment for Digital Ocean Droplet

### Prerequisites
- Digital Ocean account
- Domain name (optional, but recommended)
- GitHub repository with your SABC code
- 30 minutes for initial setup

---

## 📋 PART 1: Create Digital Ocean Droplet

### Step 1: Create Droplet
1. Log into Digital Ocean
2. Click "Create" → "Droplets"
3. Choose these settings:
   - **Region**: Choose closest to your users (e.g., NYC, SFO)
   - **Image**: Ubuntu 24.04 LTS
   - **Size**: Basic → Regular → $12/month (2GB RAM minimum for PostgreSQL)
   - **Authentication**: SSH keys (recommended) or Password
   - **Hostname**: `sabc-app` or your preference

4. Click "Create Droplet" and wait 1-2 minutes

### Step 2: Note Your Server Details
```
Droplet IP: _______________  (e.g., 142.93.123.456)
Root Password: _____________ (if using password auth)
```

---

## 📦 PART 2: Initial Server Setup

### Step 1: Connect to Your Server
```bash
# From your local terminal:
ssh root@YOUR_DROPLET_IP
```

### Step 2: Update System & Install Dependencies
```bash
# Update package list
apt update && apt upgrade -y

# Install required packages
apt install -y python3-pip python3-venv postgresql postgresql-contrib nginx git curl

# Install Python build dependencies
apt install -y build-essential python3-dev libpq-dev

# Verify installations
python3 --version  # Should be 3.11+
psql --version     # Should be 14+
nginx -v           # Should be installed
```

### Step 3: Configure PostgreSQL
```bash
# Start PostgreSQL
systemctl start postgresql
systemctl enable postgresql

# Switch to postgres user
sudo -u postgres psql

# In PostgreSQL prompt, run:
CREATE USER sabc_user WITH PASSWORD 'CHANGE_THIS_PASSWORD';
CREATE DATABASE sabc OWNER sabc_user;
GRANT ALL PRIVILEGES ON DATABASE sabc TO sabc_user;
\q

# Test connection
PGPASSWORD='CHANGE_THIS_PASSWORD' psql -h localhost -U sabc_user -d sabc -c "SELECT 1;"
```

---

## 🔧 PART 3: Deploy Application

### Step 1: Clone Your Repository
```bash
# Create app directory
mkdir -p /var/www
cd /var/www

# Clone your repository
git clone https://github.com/YOUR_USERNAME/SABC.git sabc
cd sabc

# Set permissions
chown -R www-data:www-data /var/www/sabc
```

### Step 2: Setup Python Environment
```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables
```bash
# Create production environment file
cat > .env << 'EOF'
# Database Configuration
DATABASE_URL=postgresql://sabc_user:CHANGE_THIS_PASSWORD@localhost:5432/sabc

# Application Settings
SECRET_KEY=GENERATE_A_64_CHARACTER_RANDOM_STRING_HERE
LOG_LEVEL=INFO
DEBUG=false

# Email Configuration (for password reset)
SMTP_USERNAME=your_gmail@gmail.com
SMTP_PASSWORD=your_16_char_app_password
FROM_EMAIL=noreply@yourdomain.com
WEBSITE_URL=http://YOUR_DROPLET_IP
CLUB_NAME=South Austin Bass Club

# Server Settings
HOST=0.0.0.0
PORT=8000
EOF

# Generate a secure SECRET_KEY
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"
# Copy the output and update the SECRET_KEY in .env file

# Edit the file to update passwords and settings
nano .env
```

### Step 4: Initialize Database & Load Data
```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Initialize database schema
python scripts/init_postgres.py

# Load lakes data
python scripts/load_lakes.py

# Load holidays for 2025 and 2026
python scripts/load_holidays.py 2025 2026

# Create admin user (you'll be prompted for credentials)
python scripts/bootstrap_admin_postgres.py
```

---

## 🌐 PART 4: Configure Web Server

### Step 1: Create Systemd Service for FastAPI
```bash
# Create service file
cat > /etc/systemd/system/sabc.service << 'EOF'
[Unit]
Description=SABC FastAPI Application
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/var/www/sabc
Environment="PATH=/var/www/sabc/venv/bin"
EnvironmentFile=/var/www/sabc/.env
ExecStart=/var/www/sabc/venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
systemctl daemon-reload

# Start and enable the service
systemctl start sabc
systemctl enable sabc

# Check status
systemctl status sabc
```

### Step 2: Configure Nginx as Reverse Proxy
```bash
# Create Nginx configuration
cat > /etc/nginx/sites-available/sabc << 'EOF'
server {
    listen 80;
    server_name YOUR_DROPLET_IP;  # Replace with your IP or domain

    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 86400;
    }

    location /static {
        alias /var/www/sabc/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# Enable the site
ln -s /etc/nginx/sites-available/sabc /etc/nginx/sites-enabled/
rm /etc/nginx/sites-enabled/default  # Remove default site

# Test Nginx configuration
nginx -t

# Restart Nginx
systemctl restart nginx
systemctl enable nginx
```

### Step 3: Configure Firewall
```bash
# Setup UFW firewall
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# Check firewall status
ufw status
```

---

## ✅ PART 5: Test Your Deployment

### Step 1: Verify Services Are Running
```bash
# Check all services
systemctl status sabc      # Should be "active (running)"
systemctl status nginx     # Should be "active (running)"
systemctl status postgresql # Should be "active (running)"

# Check application logs
journalctl -u sabc -n 50 --no-pager
```

### Step 2: Test Application Access
```bash
# Test locally on server
curl http://localhost:8000/health

# From your local machine, open browser:
http://YOUR_DROPLET_IP

# You should see the SABC homepage!
```

### Step 3: Test Admin Login
1. Navigate to: `http://YOUR_DROPLET_IP/login`
2. Login with the admin credentials you created
3. Access admin panel: `http://YOUR_DROPLET_IP/admin`

---

## 🔒 PART 6: SSL Certificate (HTTPS) Setup

### Option A: Using Let's Encrypt (Free SSL)
```bash
# Install Certbot
apt install certbot python3-certbot-nginx -y

# Get certificate (replace with your domain)
certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal is configured automatically
# Test renewal
certbot renew --dry-run
```

### Option B: Using Cloudflare (Recommended)
1. Add your domain to Cloudflare (free tier)
2. Update your domain's nameservers to Cloudflare's
3. In Cloudflare dashboard:
   - SSL/TLS → Set to "Full"
   - Add A record pointing to your droplet IP
4. Update Nginx server_name to your domain

---

## 🔧 PART 7: Maintenance Commands

### Update Application Code
```bash
cd /var/www/sabc
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
systemctl restart sabc
```

### View Logs
```bash
# Application logs
journalctl -u sabc -f

# Nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log

# PostgreSQL logs
tail -f /var/log/postgresql/postgresql-*.log
```

### Backup Database
```bash
# Create backup directory
mkdir -p /var/backups/sabc

# Create backup
sudo -u postgres pg_dump sabc | gzip > /var/backups/sabc/backup_$(date +%Y%m%d_%H%M%S).sql.gz

# List backups
ls -lh /var/backups/sabc/
```

### Restart Services
```bash
# Restart application
systemctl restart sabc

# Restart everything
systemctl restart sabc nginx postgresql
```

---

## 📊 PART 8: Monitoring & Performance

### Setup Basic Monitoring
```bash
# Install monitoring tools
apt install htop ncdu -y

# Check resource usage
htop  # Press q to exit

# Check disk usage
df -h
ncdu /  # Navigate with arrows, q to exit

# Check service memory usage
systemctl status sabc --no-pager | grep Memory
```

### Setup Automated Backups (Cron)
```bash
# Create backup script
cat > /usr/local/bin/backup-sabc.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/var/backups/sabc"
mkdir -p $BACKUP_DIR
sudo -u postgres pg_dump sabc | gzip > $BACKUP_DIR/sabc_$(date +%Y%m%d).sql.gz
# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete
EOF

chmod +x /usr/local/bin/backup-sabc.sh

# Add to crontab (daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/backup-sabc.sh") | crontab -
```

---

## 🚨 PART 9: Troubleshooting

### Application Won't Start
```bash
# Check service status
systemctl status sabc

# Check for port conflicts
netstat -tulpn | grep 8000

# Check Python errors
cd /var/www/sabc
source venv/bin/activate
python app.py  # Run manually to see errors
```

### Database Connection Issues
```bash
# Test database connection
sudo -u postgres psql -d sabc -c "SELECT 1;"

# Check PostgreSQL is running
systemctl status postgresql

# Check database exists
sudo -u postgres psql -l
```

### Nginx Issues
```bash
# Test configuration
nginx -t

# Check error logs
tail -100 /var/log/nginx/error.log

# Restart
systemctl restart nginx
```

### Permission Issues
```bash
# Fix ownership
chown -R www-data:www-data /var/www/sabc

# Fix permissions
chmod -R 755 /var/www/sabc
```

---

## 📝 PART 10: Final Checklist

- [ ] Server is accessible at http://YOUR_DROPLET_IP
- [ ] Admin can login at /login
- [ ] Admin panel works at /admin
- [ ] Database has lakes loaded (check in admin panel)
- [ ] Calendar shows holidays
- [ ] Password reset email configured (test at /forgot-password)
- [ ] SSL certificate installed (if using domain)
- [ ] Firewall configured
- [ ] Backups scheduled
- [ ] Monitoring setup

---

## 🎉 Deployment Complete!

Your SABC application is now live!

### Next Steps:
1. Test all features thoroughly
2. Configure your domain name (if you have one)
3. Set up SSL certificate for HTTPS
4. Share the link with club members
5. Monitor logs for first few days

### Quick Links:
- **Your Site**: http://YOUR_DROPLET_IP
- **Admin Panel**: http://YOUR_DROPLET_IP/admin
- **Health Check**: http://YOUR_DROPLET_IP/health

### Need Help?
- Check logs: `journalctl -u sabc -f`
- Restart app: `systemctl restart sabc`
- Contact support or check GitHub issues

---

**Congratulations! Your South Austin Bass Club website is now live! 🎣**