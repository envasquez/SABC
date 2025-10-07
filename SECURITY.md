# Security Guide - SABC Tournament Management System

## 🚨 CRITICAL: Credential Rotation Required

**If you are reading this after the security audit on 2025-10-07, you MUST rotate ALL credentials immediately.**

### Exposed Credentials (ROTATE IMMEDIATELY)

The following credentials were found exposed in a local `.env` file during security audit:

1. **Gmail SMTP Password**: `mjpu bxfh yglw geqo`
   - **Action Required**:
     - Revoke this Gmail app password at https://myaccount.google.com/apppasswords
     - Generate a new app password for "SABC FastAPI"
     - Update production environment variables
     - Never commit this to git

2. **Session Secret Key**: `your-secret-key-here` (weak placeholder)
   - **Action Required**:
     - Generate a new cryptographically secure secret key (see below)
     - Update all environments (dev, staging, production)
     - Invalidates all existing user sessions (expected)

3. **Database Password**: Review and rotate if compromised
   - **Action Required**:
     - Change PostgreSQL password for production database
     - Update environment variables in hosting platform
     - Test connectivity before deploying

---

## Environment Variable Security

### Generating Secure Secrets

```bash
# Generate a secure SECRET_KEY (64 characters recommended)
python3 -c "import secrets; print(secrets.token_urlsafe(48))"

# Alternative using openssl
openssl rand -base64 48

# For production, use 256-bit keys
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### Environment Variable Management

**NEVER commit `.env` files to git.**

```bash
# Check what's tracked
git ls-files | grep -E "\.env"

# If .env is tracked, remove it
git rm --cached .env
git commit -m "Remove .env from git tracking"
```

### Allowed Files (Examples Only)
- ✅ `.env.example` - Template with placeholder values
- ✅ `.env.production.example` - Production template
- ❌ `.env` - Contains real secrets (gitignored)
- ❌ `.env.local` - Local development secrets (gitignored)
- ❌ `.env.production` - Production secrets (gitignored)

---

## Production Deployment Checklist

### Before First Deployment

- [ ] Rotate all credentials from development/testing
- [ ] Generate unique SECRET_KEY for production
- [ ] Create new Gmail app password (if using email)
- [ ] Use strong database password (20+ chars, random)
- [ ] Configure DATABASE_URL via platform secrets (not .env)
- [ ] Set `ENVIRONMENT=production`
- [ ] Set `DEBUG=false`
- [ ] Set `LOG_LEVEL=WARNING` or `INFO`
- [ ] Enable HTTPS-only cookies
- [ ] Configure proper CORS origins
- [ ] Set up database backups
- [ ] Configure monitoring/alerting

### Environment Variables Required for Production

```bash
# Application Security
SECRET_KEY=<64-char-random-string>  # CRITICAL
ENVIRONMENT=production

# Database (use managed DB service)
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Email Service (for password resets)
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=<gmail-app-password>  # 16-char from Google
FROM_EMAIL=your-email@gmail.com
WEBSITE_URL=https://your-domain.com

# Logging
LOG_LEVEL=INFO
DEBUG=false

# Optional
PORT=8000
```

---

## Digital Ocean Deployment

For Digital Ocean App Platform:

1. **Use App Platform Secrets**
   - Go to App Settings → Environment Variables
   - Mark sensitive vars as "Secret" (encrypted at rest)
   - Never put secrets in `app.yaml`

2. **Managed PostgreSQL**
   - DATABASE_URL auto-injected by platform
   - Credentials rotate automatically
   - Use connection pooling

3. **Verify Configuration**
   ```bash
   # Test connection without exposing secrets
   doctl apps logs <app-id> --type=run
   ```

---

## Checking for Exposed Secrets

### Scan Local Files
```bash
# Search for potential secrets in tracked files
git grep -i "password\|secret\|key\|token" | grep -v ".example\|CLAUDE.md"

# Check for API keys
git grep -E "[A-Za-z0-9_-]{32,}"
```

### Scan Git History
```bash
# Search entire git history (slow but thorough)
git log --all --full-history --source --find-object=<file-hash>

# Use dedicated tools
pip install detect-secrets
detect-secrets scan
```

### Tools to Consider
- **Gitleaks** - https://github.com/gitleaks/gitleaks
- **TruffleHog** - https://github.com/trufflesecurity/trufflehog
- **detect-secrets** - https://github.com/Yelp/detect-secrets

---

## Incident Response

### If Credentials Are Exposed

1. **Immediate Actions** (within 1 hour):
   - Revoke/rotate ALL exposed credentials
   - Check access logs for unauthorized access
   - Force logout all users (rotate SECRET_KEY)
   - Document timeline of exposure

2. **Investigation** (within 24 hours):
   - Review git history for when secret was added
   - Check if pushed to GitHub/remote
   - Scan for data exfiltration
   - Review application logs for anomalies

3. **Remediation** (within 48 hours):
   - Update all systems with new credentials
   - Add pre-commit hooks to prevent future leaks
   - Enable secret scanning on GitHub
   - Document lessons learned

4. **Long-term**:
   - Implement secrets management service (Vault, AWS Secrets Manager)
   - Add automated secret scanning to CI/CD
   - Security training for all developers
   - Regular security audits

---

## Gmail App Password Setup

**Email service requires Gmail App Passwords (not regular password):**

1. Enable 2-Factor Authentication on Google Account
2. Go to https://myaccount.google.com/apppasswords
3. Sign in with your Gmail account
4. Select "App passwords"
5. Create new app password:
   - App name: "SABC FastAPI Production"
   - Copy the 16-character password (format: `xxxx xxxx xxxx xxxx`)
6. Use this password in `SMTP_PASSWORD` environment variable
7. **IMPORTANT**: This grants full email access - keep it secret

**If compromised**:
- Revoke at https://myaccount.google.com/apppasswords
- Generate new password
- Update environment variables
- No need to change main Gmail password

---

## Pre-commit Hooks (Recommended)

Prevent secrets from being committed:

```bash
# Install pre-commit
pip install pre-commit

# Add to .pre-commit-config.yaml
cat > .pre-commit-config.yaml <<EOF
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: check-added-large-files
      - id: check-merge-conflict
      - id: detect-private-key
EOF

# Initialize
pre-commit install
pre-commit run --all-files
```

---

## Security Contacts

- **Primary**: [Your security team email]
- **Emergency**: [On-call rotation]
- **Security Audits**: [External firm if applicable]

---

## References

- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/tutorial/security/)
- [Digital Ocean App Platform Security](https://docs.digitalocean.com/products/app-platform/reference/security/)

---

**Last Updated**: 2025-10-07
**Next Security Review**: [Schedule quarterly reviews]
