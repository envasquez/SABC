# Security Policy - SABC Tournament Management

## Overview

This document outlines the security policies, practices, and procedures for the SABC Tournament Management System. Security is a top priority, and we take a defense-in-depth approach to protect member data and system integrity.

---

## Table of Contents

1. [Reporting Vulnerabilities](#reporting-vulnerabilities)
2. [Security Architecture](#security-architecture)
3. [Authentication & Authorization](#authentication--authorization)
4. [Data Protection](#data-protection)
5. [Secure Development](#secure-development)
6. [Infrastructure Security](#infrastructure-security)
7. [Incident Response](#incident-response)
8. [Credential Management](#credential-management)
9. [Compliance & Auditing](#compliance--auditing)

---

## Reporting Vulnerabilities

### Responsible Disclosure

If you discover a security vulnerability, please follow responsible disclosure:

1. **DO NOT** open a public GitHub issue
2. **Email** security details to the maintainers privately
3. **Include**:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)
4. **Allow** reasonable time for response (typically 48-72 hours)
5. **Coordinate** public disclosure timing with maintainers

### Contact

For security issues, contact:
- **Email**: [maintainer email - configure appropriately]
- **Subject**: "SABC Security Vulnerability Report"

### Response Timeline

| Severity | Initial Response | Resolution Target |
|----------|-----------------|-------------------|
| Critical | 24 hours | 7 days |
| High | 48 hours | 14 days |
| Medium | 72 hours | 30 days |
| Low | 7 days | 60 days |

### Recognition

We appreciate security researchers who help keep our system safe. Contributors who report valid vulnerabilities will be acknowledged in our security advisories (unless they prefer to remain anonymous).

---

## Security Architecture

### Defense in Depth

The SABC system implements multiple layers of security:

```
┌─────────────────────────────────────────────────────────────┐
│                     NETWORK LAYER                           │
│  • Firewall (UFW) - ports 22, 80, 443 only                 │
│  • TLS 1.3 encryption                                       │
│  • DDoS protection (Cloudflare optional)                    │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                   APPLICATION LAYER                         │
│  • HTTPS enforcement (HSTS)                                 │
│  • Security headers (CSP, X-Frame-Options, etc.)            │
│  • Rate limiting on auth endpoints                          │
│  • Request size limits                                      │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                   SESSION LAYER                             │
│  • Secure HTTP-only cookies                                 │
│  • CSRF token protection                                    │
│  • Session expiration and renewal                           │
│  • Server-side session storage                              │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                     DATA LAYER                              │
│  • Parameterized queries (SQL injection prevention)         │
│  • Input validation (Pydantic)                              │
│  • Output encoding (XSS prevention)                         │
│  • Encrypted passwords (bcrypt)                             │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                   DATABASE LAYER                            │
│  • Network isolation (Docker network)                       │
│  • Strong authentication                                    │
│  • Minimal privileges                                       │
│  • Encrypted connections                                    │
└─────────────────────────────────────────────────────────────┘
```

### Security Headers

The application sets the following security headers:

| Header | Value | Purpose |
|--------|-------|---------|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | Force HTTPS |
| `X-Frame-Options` | `DENY` | Prevent clickjacking |
| `X-Content-Type-Options` | `nosniff` | Prevent MIME sniffing |
| `X-XSS-Protection` | `1; mode=block` | Enable XSS filter |
| `Content-Security-Policy` | See below | Restrict resource loading |

**Content Security Policy**:
```
default-src 'self';
script-src 'self' 'unsafe-inline' cdn.jsdelivr.net unpkg.com;
style-src 'self' 'unsafe-inline' cdn.jsdelivr.net;
img-src 'self' data:;
font-src 'self' cdn.jsdelivr.net;
connect-src 'self';
frame-ancestors 'none';
```

---

## Authentication & Authorization

### Password Security

**Storage**:
- Passwords are hashed using bcrypt with cost factor 12
- Automatic salt generation
- No plaintext storage or logging

**Requirements**:
- Minimum 8 characters
- Must include uppercase and lowercase letters
- Must include at least one number
- Common passwords are rejected

**Implementation**:
```python
from core.helpers.password_validator import validate_password, hash_password

# Validation
valid, errors = validate_password(user_password)
if not valid:
    raise ValueError(errors)

# Hashing
hashed = hash_password(user_password)
```

### Session Management

**Session Configuration**:
- HTTP-only cookies (not accessible via JavaScript)
- Secure flag (HTTPS only in production)
- SameSite=Lax (CSRF protection)
- 24-hour default expiration
- Session invalidation on logout

**Session Data**:
- User ID
- Authentication timestamp
- Role flags (member, admin)

### Role-Based Access Control

| Role | Capabilities |
|------|-------------|
| Anonymous | View public pages (home, calendar, results, about) |
| Authenticated | View profile, change password |
| Member | Vote in polls, view roster, view member areas |
| Admin | Full management access, user administration |

**Authorization Enforcement**:
```python
from core.helpers.auth import require_member, require_admin

@router.get("/member-only")
async def member_route(request: Request):
    user = require_member(request)  # Raises 403 if not member
    # ...

@router.post("/admin/action")
async def admin_route(request: Request):
    user = require_admin(request)  # Raises 403 if not admin
    # ...
```

### CSRF Protection

All state-changing requests (POST, PUT, DELETE) require a valid CSRF token:

**Token Generation**:
- Unique per session
- Cryptographically random
- Tied to session ID

**Validation**:
- Token must match session
- Validated before processing request
- Invalid token returns 403 Forbidden

**Usage**:
```html
<form method="POST">
    {{ csrf_token(request) }}
    <!-- form fields -->
</form>
```

---

## Data Protection

### Input Validation

**Pydantic Models**:
All input data is validated using Pydantic models with strict type checking.

```python
from pydantic import BaseModel, EmailStr, constr

class UserCreate(BaseModel):
    email: EmailStr
    name: constr(min_length=1, max_length=100)
    password: constr(min_length=8)
```

### Output Encoding

**Jinja2 Auto-escaping**:
- All template output is auto-escaped by default
- Prevents XSS attacks from user-supplied data

**Manual Escaping**:
```python
from core.helpers.sanitize import sanitize_text

safe_text = sanitize_text(user_input, max_length=100)
```

### SQL Injection Prevention

**SQLAlchemy ORM**:
- All queries use parameterized statements
- No raw SQL with user input

```python
# ✅ Safe - Parameterized query
session.query(Angler).filter(Angler.email == user_email).first()

# ❌ Unsafe - Never do this
session.execute(f"SELECT * FROM anglers WHERE email = '{user_email}'")
```

### Sensitive Data Handling

**Filtered from logs and error reports**:
- Passwords (current and new)
- Session tokens
- CSRF tokens
- API keys
- Email content

**Sentry Integration**:
```python
# Automatic filtering of sensitive data
before_send=filter_sensitive_data
```

---

## Secure Development

### Pre-commit Hooks

Security checks run before every commit:

| Tool | Purpose |
|------|---------|
| Bandit | Python security linter |
| detect-private-key | Prevent key commits |
| Ruff | Security-focused linting |
| MyPy | Type safety enforcement |

### Code Review Requirements

Security-sensitive changes require:
- Review by maintainer
- All automated checks passing
- Security test coverage
- Documentation updates

### Security Testing

**Automated Tests**:
- CSRF protection tests
- SQL injection resistance tests
- XSS prevention tests
- Authorization tests
- Authentication tests

**Test Coverage**:
- Security tests: >95%
- Authentication: >90%
- Authorization: >90%

### Dependency Management

**Regular Updates**:
- Dependencies reviewed monthly
- Security advisories monitored
- Automated vulnerability scanning (Dependabot)

**Pinned Versions**:
- All dependencies pinned in requirements.txt
- Reproducible builds

---

## Infrastructure Security

### Firewall Configuration

**UFW Rules**:
```bash
# Default deny incoming
ufw default deny incoming
ufw default allow outgoing

# Allow SSH
ufw allow 22

# Allow HTTP/HTTPS
ufw allow 80
ufw allow 443

# Enable firewall
ufw enable
```

### Docker Security

**Container Isolation**:
- Non-root user inside containers
- Read-only filesystem where possible
- Minimal base images
- No privileged containers

**Network Isolation**:
```yaml
networks:
  frontend:    # Nginx only
  backend:     # App and database only
```

### SSL/TLS Configuration

**Let's Encrypt**:
- Automatic certificate renewal
- TLS 1.2+ only
- Strong cipher suites

**Nginx SSL Configuration**:
```nginx
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
ssl_prefer_server_ciphers off;
ssl_session_timeout 1d;
ssl_session_cache shared:SSL:50m;
ssl_stapling on;
ssl_stapling_verify on;
```

### Monitoring

**Security Monitoring**:
- Failed login attempts tracked
- Unusual traffic patterns detected
- Error rates monitored
- Sentry alerts for exceptions

**Metrics**:
```
failed_logins_total
http_requests_total{status="403"}
http_requests_total{status="401"}
```

---

## Incident Response

### Incident Classification

| Level | Description | Examples |
|-------|-------------|----------|
| P0 | Critical - Active breach | Data exfiltration, system compromise |
| P1 | High - Potential breach | Vulnerability being exploited |
| P2 | Medium - Security issue | Configuration weakness, minor vulnerability |
| P3 | Low - Minor issue | Security improvement opportunity |

### Response Procedure

**1. Detection**
- Automated monitoring alerts
- User reports
- Security researcher disclosure

**2. Containment**
- Isolate affected systems
- Preserve evidence
- Block malicious actors

**3. Investigation**
- Determine scope
- Identify root cause
- Document timeline

**4. Remediation**
- Fix vulnerability
- Deploy patches
- Verify fix effectiveness

**5. Recovery**
- Restore services
- Monitor for recurrence
- Update defenses

**6. Post-Incident**
- Document lessons learned
- Update procedures
- Communicate to stakeholders

### Communication

**Internal**:
- Immediate notification to maintainers
- Slack/Discord channel for coordination
- Post-incident review meeting

**External**:
- User notification if data affected
- Security advisory publication
- Regulatory notification if required

---

## Credential Management

### Secret Storage

**Environment Variables**:
All secrets stored in environment variables, never in code.

| Secret | Purpose | Rotation |
|--------|---------|----------|
| `SECRET_KEY` | Session encryption | Quarterly |
| `DATABASE_URL` | Database connection | Annually |
| `SMTP_PASSWORD` | Email sending | Annually |
| `SENTRY_DSN` | Error tracking | As needed |

### Rotation Procedures

**SECRET_KEY Rotation**:
```bash
# Generate new key
python -c "import secrets; print(secrets.token_urlsafe(48))"

# Update .env file
SECRET_KEY=new-generated-key

# Restart application (all sessions invalidated)
./restart.sh
```

**Database Password Rotation**:
```bash
# Update PostgreSQL password
docker compose exec db psql -U postgres -c "ALTER USER sabc PASSWORD 'new-password';"

# Update .env file
DB_PASSWORD=new-password
DATABASE_URL=postgresql://sabc:new-password@db:5432/sabc

# Restart application
./restart.sh
```

### Git Security

**.gitignore**:
```
.env
.env.local
.env.production
*.pem
*.key
secrets/
```

**Pre-commit Hook**:
```bash
# Prevents committing secrets
detect-private-key
```

---

## Compliance & Auditing

### Data Privacy

**Data Collection**:
- Minimal data collection principle
- Only data necessary for functionality
- No third-party tracking

**Data Retention**:
- Active accounts: Indefinite
- Deleted accounts: Data removed within 30 days
- Logs: 90 days retention

**Member Rights**:
- Access their data via Profile
- Request data deletion
- Export tournament history

### Audit Logging

**Logged Events**:
- Login attempts (success/failure)
- Admin actions
- Data modifications
- Security-relevant events

**Log Format**:
```
2024-03-15T10:30:00Z [INFO] auth.login - user_id=123 ip=192.168.1.1 success=true
2024-03-15T10:31:00Z [WARN] auth.login - email=test@example.com ip=192.168.1.1 success=false reason=invalid_password
```

### Security Reviews

**Quarterly**:
- Dependency vulnerability scan
- Access review (admin accounts)
- Log analysis

**Annually**:
- Full security audit
- Penetration testing (if resources allow)
- Policy review and update

---

## Best Practices for Users

### Strong Passwords

- Use unique password for this site
- Consider using a password manager
- Don't share your password
- Change password if you suspect compromise

### Account Security

- Log out from shared computers
- Report suspicious activity
- Keep email address current for password reset

### Reporting Issues

If you notice anything suspicious:
1. Don't click suspicious links
2. Report to club officers immediately
3. Change your password if concerned

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-11-30 | Initial security policy |

---

**Security is everyone's responsibility. Thank you for helping keep SABC safe!**
