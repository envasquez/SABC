# SABC Tournament Management System - Web Deployment Guide

## 🚀 Quick Deploy to Digital Ocean (Recommended)

This guide will get your SABC site live on the web in about 30 minutes.

### Prerequisites
- A domain name (optional, but recommended)
- Credit card for hosting (~$6/month minimum)
- Your code in a GitHub repository (recommended) or ready to upload

---

## Option 1: Digital Ocean Deployment (Easiest)

### Step 1: Create Digital Ocean Account
1. Go to [DigitalOcean.com](https://www.digitalocean.com)
2. Sign up (get $200 free credit with new account)
3. Create a new project called "SABC"

### Step 2: Create a Droplet (Server)
1. Click **"Create" → "Droplets"**
2. Choose these settings:
   - **Region**: Choose closest to your users (e.g., San Francisco)
   - **Image**: Ubuntu 22.04 LTS
   - **Size**: Basic → Regular → $6/month (1GB RAM, 25GB SSD)
   - **Authentication**: Password (easier) or SSH Key (more secure)
   - **Hostname**: `sabc-tournament`
3. Click **"Create Droplet"**
4. Wait 1 minute, then copy your server's IP address

### Step 3: Connect to Your Server
```bash
# On your local computer (Mac/Linux Terminal or Windows PowerShell)
ssh root@YOUR_SERVER_IP

# When prompted, enter the password you set
```

### Step 4: Install Everything (Copy & Paste)
```bash
# Update system (2 minutes)
apt update && apt upgrade -y

# Install required software (3 minutes)
apt install python3 python3-pip python3-venv nginx git supervisor -y

# Create application directory
mkdir -p /var/www
cd /var/www

# Clone your repository (replace with your GitHub URL)
git clone https://github.com/YOUR_USERNAME/sabc.git
cd sabc

# OR: Upload files manually using SFTP/FileZilla if not using Git
```

### Step 5: Setup Python Application
```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install dependencies (2 minutes)
pip install -r requirements.txt

# Initialize database
python database.py

# Create admin user (follow prompts)
python bootstrap_admin.py
```

### Step 6: Configure Environment
```bash
# Create production configuration
cp .env.example .env

# Generate secure secret key
echo "SECRET_KEY=$(openssl rand -base64 32)" >> .env

# Edit configuration
nano .env
```

Update these values in `.env`:
```env
SECRET_KEY=<already set above>
DATABASE_URL=sqlite:////var/www/sabc/sabc.db
ENVIRONMENT=production
HOST=127.0.0.1
PORT=8000
WORKERS=2
```

Press `Ctrl+X`, then `Y`, then `Enter` to save.

### Step 7: Setup Nginx Web Server
```bash
# Remove default site
rm /etc/nginx/sites-enabled/default

# Create new configuration
nano /etc/nginx/sites-available/sabc
```

Paste this configuration (replace YOUR_DOMAIN_OR_IP):
```nginx
server {
    listen 80;
    server_name YOUR_DOMAIN_OR_IP;
    
    client_max_body_size 10M;
    
    location /static/ {
        alias /var/www/sabc/static/;
        expires 30d;
    }
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Save and enable:
```bash
# Enable site
ln -s /etc/nginx/sites-available/sabc /etc/nginx/sites-enabled/

# Test configuration
nginx -t

# Reload nginx
systemctl restart nginx
```

### Step 8: Setup Auto-Start with Supervisor
```bash
# Create supervisor configuration
nano /etc/supervisor/conf.d/sabc.conf
```

Paste this:
```ini
[program:sabc]
command=/var/www/sabc/venv/bin/gunicorn app:app -c gunicorn.conf.py
directory=/var/www/sabc
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/sabc.log
environment=PATH="/var/www/sabc/venv/bin",HOME="/var/www/sabc"
```

Save and start:
```bash
# Set permissions
chown -R www-data:www-data /var/www/sabc
chmod -R 755 /var/www/sabc

# Update supervisor
supervisorctl reread
supervisorctl update
supervisorctl start sabc

# Check status
supervisorctl status sabc
```

### Step 9: Access Your Site!
Open your browser and go to:
```
http://YOUR_SERVER_IP
```

Your site should be live! 🎉

---

## Option 2: Add a Domain Name

### Step 1: Point Domain to Server
1. Log into your domain registrar (GoDaddy, Namecheap, etc.)
2. Find DNS settings
3. Add an "A Record":
   - **Type**: A
   - **Host**: @ (or leave blank)
   - **Value**: YOUR_SERVER_IP
   - **TTL**: 3600
4. Add another for www:
   - **Type**: A
   - **Host**: www
   - **Value**: YOUR_SERVER_IP
   - **TTL**: 3600

Wait 5-30 minutes for DNS to propagate.

### Step 2: Update Nginx for Domain
```bash
# Edit nginx configuration
nano /etc/nginx/sites-available/sabc

# Change server_name line to:
server_name yourdomain.com www.yourdomain.com;

# Reload nginx
systemctl reload nginx
```

### Step 3: Add Free SSL Certificate
```bash
# Install certbot
apt install certbot python3-certbot-nginx -y

# Get certificate (follow prompts)
certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Test auto-renewal
certbot renew --dry-run
```

Your site is now available at:
- `https://yourdomain.com` (secure)
- `http://yourdomain.com` (redirects to HTTPS)

---

## Option 3: Alternative Hosting Providers

### AWS Lightsail (Similar to Digital Ocean)
1. Go to [AWS Lightsail](https://lightsail.aws.amazon.com)
2. Create instance → Ubuntu 22.04
3. Choose $5/month plan
4. Follow same steps as Digital Ocean above

### Linode
1. Go to [Linode.com](https://www.linode.com)
2. Create Linode → Ubuntu 22.04
3. Choose Nanode 1GB ($5/month)
4. Follow same steps as Digital Ocean above

### Vultr
1. Go to [Vultr.com](https://www.vultr.com)
2. Deploy new server → Ubuntu 22.04
3. Choose $6/month plan
4. Follow same steps as Digital Ocean above

---

## 🛠️ Maintenance Commands

### Update Your Site
```bash
cd /var/www/sabc
git pull
source venv/bin/activate
pip install -r requirements.txt
supervisorctl restart sabc
```

### View Logs
```bash
# Application logs
tail -f /var/log/sabc.log

# Nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### Backup Database
```bash
# Manual backup
cp /var/www/sabc/sabc.db /var/www/sabc/backups/sabc-$(date +%Y%m%d).db

# Add automatic daily backups
crontab -e
# Add this line:
0 2 * * * cp /var/www/sabc/sabc.db /var/www/sabc/backups/sabc-$(date +\%Y\%m\%d).db
```

### Restart Services
```bash
# Restart application
supervisorctl restart sabc

# Restart nginx
systemctl restart nginx

# Check status
supervisorctl status sabc
systemctl status nginx
```

---

## 🔧 Troubleshooting

### Site Not Loading?
```bash
# Check if app is running
supervisorctl status sabc

# Check nginx
systemctl status nginx

# Check for errors
tail -50 /var/log/sabc.log
tail -50 /var/log/nginx/error.log
```

### Permission Errors?
```bash
# Fix ownership
chown -R www-data:www-data /var/www/sabc
chmod -R 755 /var/www/sabc
chmod 664 /var/www/sabc/sabc.db
```

### Database Locked?
```bash
# Restart application
supervisorctl restart sabc

# If still locked, check for stuck processes
ps aux | grep python
# Kill any old processes
```

### Can't Connect via SSH?
- Check server IP is correct
- Ensure firewall isn't blocking port 22
- Try password instead of SSH key

---

## 💰 Hosting Costs

**Minimal Setup:**
- Digital Ocean Droplet: $6/month
- Domain name: $10-15/year (optional)
- **Total: ~$6-8/month**

**Recommended Setup:**
- Digital Ocean Droplet: $12/month (2GB RAM)
- Domain name: $10-15/year
- Backups: $2/month
- **Total: ~$15/month**

---

## 📱 Quick Deploy Checklist

- [ ] Created hosting account (Digital Ocean, etc.)
- [ ] Created server/droplet
- [ ] Connected via SSH
- [ ] Installed Python, Nginx, Git
- [ ] Cloned/uploaded code
- [ ] Installed Python dependencies
- [ ] Created database
- [ ] Created admin user
- [ ] Configured environment (.env)
- [ ] Setup Nginx
- [ ] Setup Supervisor
- [ ] Site is accessible via IP
- [ ] (Optional) Added domain name
- [ ] (Optional) Added SSL certificate
- [ ] Setup backups

---

## 🆘 Need Help?

1. **Check logs first** - Most issues are visible in logs
2. **Verify file permissions** - www-data should own files
3. **Test each component** - nginx, supervisor, python app
4. **Google the error message** - Someone else had the same issue

**Common Issues:**
- Port 8000 already in use → Kill old process
- Database locked → Restart application
- 502 Bad Gateway → App not running, check supervisor
- Permission denied → Fix ownership with chown

---

Your SABC Tournament Management System should now be live on the web! 🎣🏆

**Next Steps:**
1. Share your site URL with club members
2. Create member accounts
3. Start adding tournaments and polls
4. Configure regular backups
5. Monitor logs for any issues
