# Staging Environment Setup - SABC Tournament Management

This document provides complete instructions for setting up and managing the staging environment for the South Austin Bass Club (SABC) tournament management application.

## Overview

The staging environment is a production-like environment used for:
- Testing new features before production deployment
- Validating database migrations
- Load testing and performance validation
- QA and user acceptance testing
- Training and demonstration purposes

## Architecture

```
Production:  https://sabc.example.com  → Production DB (PostgreSQL)
Staging:     https://staging.sabc.example.com → Staging DB (PostgreSQL)
Development: http://localhost:8000 → Local SQLite/PostgreSQL
```

## Digital Ocean App Platform Setup

### Prerequisites

1. Digital Ocean account with App Platform access
2. Production app already deployed and working
3. GitHub repository access
4. Domain DNS access (for staging subdomain)

### Step 1: Create Staging Database

1. Go to Digital Ocean → Databases
2. Click "Create Database Cluster"
3. Configuration:
   - **Database Engine**: PostgreSQL 17
   - **Plan**: Basic ($12/month) or same as production
   - **Datacenter Region**: Same as production (for best performance)
   - **Database Name**: `sabc_staging`
   - **Cluster Name**: `sabc-staging-db`
4. Click "Create Database Cluster"
5. Wait for provisioning (5-10 minutes)
6. Note the connection details (will be auto-injected into app)

### Step 2: Create Staging App

1. Go to Digital Ocean → Apps
2. Click "Create App"
3. **Source**: Choose your GitHub repository
4. **Branch**: `staging` (create this branch if it doesn't exist)
5. **Autodeploy**: Enable (deploy on every push to staging branch)

### Step 3: Configure Staging App

#### App Spec Configuration

```yaml
name: sabc-staging
region: nyc

# Database
databases:
  - name: sabc-staging-db
    engine: PG
    production: false
    cluster_name: sabc-staging-db

# Web Service
services:
  - name: web
    github:
      repo: your-org/SABC
      branch: staging
      deploy_on_push: true

    # Build
    build_command: pip install -r requirements.txt

    # Runtime
    run_command: |
      alembic upgrade head && \
      uvicorn app:app --host 0.0.0.0 --port 8080

    # Environment
    environment_slug: python
    instance_count: 1
    instance_size_slug: basic-xxs  # $5/month

    # Routes
    routes:
      - path: /

    # Health Check
    health_check:
      http_path: /health
      initial_delay_seconds: 30
      period_seconds: 10
      timeout_seconds: 5
      success_threshold: 1
      failure_threshold: 3

    # Environment Variables
    envs:
      - key: ENVIRONMENT
        value: staging

      - key: DATABASE_URL
        scope: RUN_TIME
        type: SECRET
        # Auto-injected from database connection

      - key: SECRET_KEY
        scope: RUN_TIME
        type: SECRET
        value: ${staging.SECRET_KEY}  # Generate new key for staging

      - key: SMTP_SERVER
        value: smtp.gmail.com

      - key: SMTP_PORT
        value: "587"

      - key: SMTP_USERNAME
        scope: RUN_TIME
        type: SECRET
        value: ${staging.SMTP_USERNAME}

      - key: SMTP_PASSWORD
        scope: RUN_TIME
        type: SECRET
        value: ${staging.SMTP_PASSWORD}

      - key: SENTRY_DSN
        scope: RUN_TIME
        type: SECRET
        value: ${staging.SENTRY_DSN}  # Separate Sentry project for staging

      - key: LOG_LEVEL
        value: DEBUG

      - key: SESSION_TIMEOUT
        value: "86400"  # 24 hours

      - key: RELEASE_VERSION
        value: staging-${_self.COMMIT_SHORT_SHA}

# Jobs (run before deployment)
jobs:
  - name: migrate-db
    kind: PRE_DEPLOY
    github:
      repo: your-org/SABC
      branch: staging
    build_command: pip install -r requirements.txt
    run_command: alembic upgrade head
    environment_slug: python
    envs:
      - key: DATABASE_URL
        scope: RUN_TIME
        type: SECRET
```

### Step 4: Configure Environment Secrets

In Digital Ocean App Platform dashboard:

1. Navigate to your staging app → Settings → App-Level Environment Variables
2. Add the following secrets:

```bash
# Generate new SECRET_KEY for staging (64+ characters)
SECRET_KEY=<generate-new-random-key>

# SMTP credentials (can use same as production or separate staging account)
SMTP_USERNAME=your-staging-email@example.com
SMTP_PASSWORD=<app-specific-password>

# Sentry DSN (create separate Sentry project for staging)
SENTRY_DSN=https://xxx@yyy.ingest.sentry.io/zzz
```

### Step 5: Configure Custom Domain

1. In your DNS provider, add CNAME record:
   ```
   staging.sabc.example.com → <digital-ocean-app-url>
   ```

2. In Digital Ocean App Platform:
   - Go to Settings → Domains
   - Click "Add Domain"
   - Enter: `staging.sabc.example.com`
   - Let Digital Ocean provision SSL certificate (automatic)

### Step 6: Initial Deployment

1. Create `staging` branch in GitHub:
   ```bash
   git checkout master
   git checkout -b staging
   git push origin staging
   ```

2. Digital Ocean will automatically:
   - Pull code from staging branch
   - Install dependencies
   - Run database migrations (PRE_DEPLOY job)
   - Start the application
   - Provision SSL certificate

3. Monitor deployment in Digital Ocean dashboard
4. Check logs for any errors
5. Verify app is accessible at staging URL

## Staging Workflow

### Deploying to Staging

```bash
# 1. Create feature branch
git checkout -b feature/new-feature

# 2. Develop and test locally
nix develop -c start-app
nix develop -c run-tests

# 3. Commit changes
git add .
git commit -m "Add new feature"

# 4. Merge to staging branch
git checkout staging
git merge feature/new-feature
git push origin staging

# 5. Digital Ocean auto-deploys to staging
# Monitor: https://cloud.digitalocean.com/apps/

# 6. Test on staging
# Visit: https://staging.sabc.example.com

# 7. If tests pass, merge to master for production
git checkout master
git merge staging
git push origin master
```

### Manual Deployment

If auto-deploy is disabled:

```bash
# In Digital Ocean dashboard
Apps → sabc-staging → Settings → Deploy
```

Or via CLI:

```bash
doctl apps create-deployment <app-id>
```

## Database Management

### Accessing Staging Database

```bash
# Get connection string from Digital Ocean
# Dashboard → Databases → sabc-staging-db → Connection Details

# Connect via psql
psql "postgresql://user:pass@host:port/sabc_staging?sslmode=require"

# Or use connection string in your app
export DATABASE_URL="postgresql://user:pass@host:port/sabc_staging?sslmode=require"
```

### Resetting Staging Data

Create a script to reset staging database with fresh test data:

```bash
# scripts/reset_staging_db.sh
#!/bin/bash

# This script resets the staging database and populates it with test data
# WARNING: This deletes all data in staging database!

set -e

echo "⚠️  WARNING: This will DELETE ALL DATA in staging database!"
echo "Press Ctrl+C to cancel, or Enter to continue..."
read

# Get staging database connection string from Digital Ocean
# You'll need to set this manually or retrieve from DO API
STAGING_DB_URL="${STAGING_DATABASE_URL}"

if [ -z "$STAGING_DB_URL" ]; then
    echo "Error: STAGING_DATABASE_URL not set"
    exit 1
fi

echo "🗑️  Dropping all tables..."
psql "$STAGING_DB_URL" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

echo "📦 Running Alembic migrations..."
DATABASE_URL="$STAGING_DB_URL" alembic upgrade head

echo "🌱 Seeding test data..."
python scripts/seed_staging_data.py

echo "✅ Staging database reset complete!"
echo "🌐 Visit: https://staging.sabc.example.com"
```

### Seeding Test Data

Create `scripts/seed_staging_data.py`:

```python
"""Seed staging database with realistic test data."""

import os
from datetime import datetime, timedelta
from core.db_schema import get_session
from core.db_schema.models import Angler, Event, Tournament, Lake, Ramp, Poll, PollOption
from core.helpers.password_validator import hash_password

def seed_staging_data():
    """Populate staging database with test data."""
    with get_session() as session:
        # Create test admin user
        admin = Angler(
            name="Test Admin",
            email="admin@staging.sabc.test",
            password=hash_password("TestPassword123!"),
            member=True,
            is_admin=True,
            phone="512-555-0001"
        )
        session.add(admin)

        # Create test members
        members = []
        for i in range(1, 11):
            member = Angler(
                name=f"Test Member {i}",
                email=f"member{i}@staging.sabc.test",
                password=hash_password("TestPassword123!"),
                member=True,
                is_admin=False,
                phone=f"512-555-{str(i).zfill(4)}"
            )
            members.append(member)
            session.add(member)

        # Create test lakes
        lake = Lake(
            name="Test Lake Travis",
            location="Austin, TX"
        )
        session.add(lake)
        session.flush()

        # Create test ramps
        ramp = Ramp(
            lake_id=lake.id,
            name="Test Ramp",
            coordinates="30.3916,-97.8827"
        )
        session.add(ramp)
        session.flush()

        # Create test events
        for month in range(1, 7):
            event_date = datetime(2025, month, 15)
            event = Event(
                date=event_date,
                name=f"Test Tournament {month}",
                event_type="tournament",
                year=2025
            )
            session.add(event)
            session.flush()

            # Create tournament for event
            tournament = Tournament(
                event_id=event.id,
                lake_id=lake.id,
                ramp_id=ramp.id,
                complete=False
            )
            session.add(tournament)
            session.flush()

            # Create poll for tournament location
            poll = Poll(
                event_id=event.id,
                title=f"Vote for Tournament {month} Location",
                poll_type="tournament_location",
                starts_at=event_date - timedelta(days=14),
                closes_at=event_date - timedelta(days=7),
                created_by=admin.id
            )
            session.add(poll)
            session.flush()

            # Create poll options
            option = PollOption(
                poll_id=poll.id,
                option_text=f"Test Lake Travis - Test Ramp",
                option_data='{"lake_id": ' + str(lake.id) + ', "ramp_id": ' + str(ramp.id) + '}'
            )
            session.add(option)

        session.commit()
        print("✅ Staging data seeded successfully!")
        print(f"   - Admin: admin@staging.sabc.test / TestPassword123!")
        print(f"   - Members: member1-10@staging.sabc.test / TestPassword123!")

if __name__ == "__main__":
    seed_staging_data()
```

## Monitoring Staging

### Application Logs

```bash
# View real-time logs in Digital Ocean dashboard
Apps → sabc-staging → Runtime Logs

# Or via CLI
doctl apps logs <app-id> --type run --follow
```

### Sentry Monitoring

1. Create separate Sentry project for staging:
   - Project name: `sabc-staging`
   - Platform: Python
2. Get DSN and add to staging environment variables
3. Errors will appear in Sentry dashboard with `environment: staging` tag

### Prometheus Metrics

Access metrics at:
```
https://staging.sabc.example.com/metrics
```

## Testing on Staging

### Manual Testing Checklist

- [ ] Homepage loads correctly
- [ ] User can register new account
- [ ] User can login/logout
- [ ] Member can view polls
- [ ] Member can vote in active poll
- [ ] Admin can create events
- [ ] Admin can create tournaments
- [ ] Admin can enter results
- [ ] Email notifications work
- [ ] Password reset flow works
- [ ] All public pages render correctly

### Automated Testing

Run integration tests against staging:

```bash
# Set staging URL
export TEST_BASE_URL="https://staging.sabc.example.com"

# Run tests
pytest tests/integration/ --base-url=$TEST_BASE_URL
```

### Load Testing

```bash
# Run load test against staging
locust -f tests/load/locustfile.py \
  --host=https://staging.sabc.example.com \
  --users 50 \
  --spawn-rate 5 \
  --run-time 300s
```

## Troubleshooting

### App Won't Start

1. Check build logs in Digital Ocean dashboard
2. Verify all environment variables are set
3. Check database connection (DATABASE_URL)
4. Verify migrations ran successfully

### Database Connection Issues

```bash
# Test connection from command line
psql "$STAGING_DATABASE_URL"

# Check Alembic version
alembic current

# Run migrations manually
alembic upgrade head
```

### SSL Certificate Issues

- Wait 5-10 minutes after adding domain (certificate provisioning)
- Verify DNS CNAME record is correct
- Check Digital Ocean domain settings

### Performance Issues

1. Check instance size (may need to upgrade from basic-xxs)
2. Review Prometheus metrics at /metrics
3. Check database query performance
4. Review Sentry performance traces

## Cost Estimate

| Component | Cost |
|-----------|------|
| App Instance (basic-xxs) | $5/month |
| PostgreSQL Database (Basic) | $12/month |
| Bandwidth | ~$1/month |
| **Total** | **~$18/month** |

## Security Considerations

1. **Separate Credentials**: Use different SECRET_KEY and SMTP credentials than production
2. **Separate Database**: Never point staging at production database
3. **Test Data Only**: Don't put real member data in staging
4. **Access Control**: Consider IP whitelisting for staging environment
5. **Sentry Project**: Use separate Sentry project to avoid alert fatigue

## Deployment Checklist

Before promoting staging to production:

- [ ] All tests passing in CI/CD
- [ ] Manual testing completed on staging
- [ ] Load testing shows acceptable performance
- [ ] Database migrations tested on staging
- [ ] No errors in Sentry for 24+ hours
- [ ] Monitoring and alerts working correctly
- [ ] Security scan passing (Bandit, Safety)
- [ ] Code review completed
- [ ] Stakeholder approval obtained

## Promoting to Production

```bash
# 1. Ensure staging is fully tested
# 2. Merge staging to master
git checkout master
git merge staging
git push origin master

# 3. Tag release
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0

# 4. Production auto-deploys (if configured)
# Or deploy manually in Digital Ocean dashboard
```

## Maintenance

### Weekly Tasks

- [ ] Check staging logs for errors
- [ ] Review Sentry issues
- [ ] Verify staging database is in sync with production schema
- [ ] Test new features on staging

### Monthly Tasks

- [ ] Reset staging database with fresh test data
- [ ] Update staging dependencies
- [ ] Review and clean up old test data
- [ ] Verify SSL certificates are valid

## Support

For issues with staging environment:

1. Check Digital Ocean App Platform status page
2. Review staging logs in Digital Ocean dashboard
3. Check Sentry for application errors
4. Contact DevOps team or project lead

---

**Last Updated**: 2025-10-09
**Environment**: Staging
**Status**: Active
