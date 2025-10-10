# Database Migrations - SABC

This document describes how to manage database schema changes using Alembic for the SABC tournament management system.

## Overview

SABC uses [Alembic](https://alembic.sqlalchemy.org/) for database migrations. Alembic tracks schema changes and allows for controlled, versioned database updates.

**Key Benefits:**
- Version-controlled schema changes
- Automatic migration script generation
- Rollback capability for failed deployments
- Safe, incremental database updates
- Audit trail of all schema changes

## Quick Reference

```bash
# Check current migration version
nix develop -c alembic current

# Show migration history
nix develop -c alembic history

# Create a new migration (auto-generate from model changes)
nix develop -c alembic revision --autogenerate -m "Add column to anglers table"

# Apply all pending migrations
nix develop -c alembic upgrade head

# Rollback one migration
nix develop -c alembic downgrade -1

# Rollback to specific revision
nix develop -c alembic downgrade <revision_id>
```

## Directory Structure

```
SABC/
├── alembic/                    # Alembic migrations directory
│   ├── versions/               # Migration scripts
│   │   └── b6af1117804a_initial_baseline.py
│   ├── env.py                  # Alembic environment configuration
│   ├── script.py.mako          # Migration template
│   └── README                  # Alembic README
├── alembic.ini                 # Alembic configuration file
└── DATABASE_MIGRATIONS.md      # This file
```

## Creating Migrations

### 1. Make Changes to SQLAlchemy Models

Edit the model definitions in `core/db_schema/models.py`:

```python
# Example: Adding a new column
class Angler(Base):
    __tablename__ = "anglers"
    # ... existing columns ...
    phone_verified = Column(Boolean, default=False)  # NEW COLUMN
```

### 2. Generate Migration Script

Alembic can auto-generate migration scripts by comparing your SQLAlchemy models with the database:

```bash
nix develop -c alembic revision --autogenerate -m "Add phone_verified to anglers"
```

This creates a new file in `alembic/versions/` with:
- Upgrade operations (apply the change)
- Downgrade operations (revert the change)

### 3. Review the Generated Migration

**IMPORTANT:** Always review auto-generated migrations before applying them!

```bash
# Find the newest migration file
ls -lt alembic/versions/

# Review the migration
cat alembic/versions/xxxxx_add_phone_verified_to_anglers.py
```

Check for:
- Correct table and column names
- Proper data types
- Appropriate default values
- Safe operations (no data loss)

### 4. Edit if Necessary

Auto-generated migrations may need manual adjustments:

```python
def upgrade() -> None:
    # Add the column with a default value
    op.add_column('anglers', sa.Column('phone_verified', sa.Boolean(), nullable=False, server_default='false'))

def downgrade() -> None:
    # Remove the column
    op.drop_column('anglers', 'phone_verified')
```

### 5. Apply the Migration

```bash
# Development/staging
nix develop -c alembic upgrade head

# Production (via deployment script)
# See "Deployment Integration" section below
```

## Migration Best Practices

### DO:
✅ **Always review auto-generated migrations** before applying
✅ **Use descriptive migration messages** (e.g., "Add phone_verified to anglers")
✅ **Test migrations in staging** before production
✅ **Keep migrations small and focused** (one logical change per migration)
✅ **Add data migrations when needed** (e.g., populate new columns)
✅ **Use server_default** for new NOT NULL columns on existing tables
✅ **Test both upgrade() and downgrade()** operations

### DON'T:
❌ **Never edit existing migrations** that have been deployed
❌ **Never skip migrations** (always apply in order)
❌ **Don't delete migration files** from alembic/versions/
❌ **Don't modify data directly** - use data migration scripts
❌ **Don't assume auto-generate is perfect** - always review

## Common Migration Scenarios

### Adding a Column

```python
def upgrade() -> None:
    op.add_column('anglers',
        sa.Column('phone_verified', sa.Boolean(), nullable=False, server_default='false')
    )

def downgrade() -> None:
    op.drop_column('anglers', 'phone_verified')
```

### Modifying a Column

```python
def upgrade() -> None:
    op.alter_column('anglers', 'email',
        existing_type=sa.String(length=255),
        type_=sa.String(length=320),  # New max email length
        nullable=False
    )

def downgrade() -> None:
    op.alter_column('anglers', 'email',
        existing_type=sa.String(length=320),
        type_=sa.String(length=255),
        nullable=False
    )
```

### Adding an Index

```python
def upgrade() -> None:
    op.create_index('ix_anglers_email', 'anglers', ['email'])

def downgrade() -> None:
    op.drop_index('ix_anglers_email', 'anglers')
```

### Data Migration Example

```python
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column

def upgrade() -> None:
    # Add the column
    op.add_column('anglers', sa.Column('status', sa.String(20), nullable=True))

    # Populate data for existing rows
    anglers = table('anglers',
        column('id', sa.Integer),
        column('member', sa.Boolean),
        column('status', sa.String)
    )

    op.execute(
        anglers.update()
        .where(anglers.c.member == True)
        .values(status='active')
    )

    op.execute(
        anglers.update()
        .where(anglers.c.member == False)
        .values(status='inactive')
    )

    # Make column non-nullable
    op.alter_column('anglers', 'status', nullable=False)

def downgrade() -> None:
    op.drop_column('anglers', 'status')
```

## Testing Migrations

### Local Testing

```bash
# 1. Check current state
nix develop -c alembic current

# 2. Apply migration
nix develop -c alembic upgrade head

# 3. Verify database schema
psql -h localhost -U postgres -d sabc -c "\d anglers"

# 4. Test rollback
nix develop -c alembic downgrade -1

# 5. Re-apply
nix develop -c alembic upgrade head
```

### Automated Testing

Migrations should be tested in CI/CD:

```bash
# Reset test database
nix develop -c reset-db

# Apply all migrations
nix develop -c alembic upgrade head

# Run application tests
nix develop -c run-tests
```

## Deployment Integration

### Pre-Deployment Steps

1. **Commit migrations** to version control
2. **Test in staging** environment
3. **Verify rollback** works
4. **Review production data** for compatibility

### Digital Ocean App Platform

Add migration step to `.do/app.yaml`:

```yaml
jobs:
  - name: migrate-db
    kind: PRE_DEPLOY
    instance_count: 1
    instance_size_slug: professional-xs
    run_command: alembic upgrade head
```

**Note:** Digital Ocean will run migrations before deploying new app version.

### Manual Deployment

```bash
# 1. Backup production database
pg_dump -h production-db -U user -d sabc > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. Apply migrations
alembic upgrade head

# 3. Verify
alembic current

# 4. If issues occur, rollback
alembic downgrade -1
```

## Troubleshooting

### Migration Fails with "Can't locate revision"

**Problem:** Alembic can't find a migration revision.

**Solution:**
```bash
# Check what the database thinks the current revision is
nix develop -c alembic current

# Check migration history
nix develop -c alembic history

# If database is ahead of migrations, stamp to correct revision
nix develop -c alembic stamp <revision_id>
```

### "Target database is not up to date"

**Problem:** Database schema doesn't match any migration.

**Solution:**
```bash
# For existing databases, stamp to baseline
nix develop -c alembic stamp b6af1117804a

# Then apply pending migrations
nix develop -c alembic upgrade head
```

### Auto-generate Detects Unwanted Changes

**Problem:** `alembic revision --autogenerate` creates migrations for existing tables.

**Cause:** Database schema differs from SQLAlchemy models.

**Solution:**
1. Ensure database is up to date: `alembic upgrade head`
2. If models were manually changed, update database first
3. Review model definitions in `core/db_schema/models.py`

### Migration Fails During Deployment

**Problem:** Migration fails in production.

**Recovery:**
```bash
# 1. Check alembic version table
psql -d sabc -c "SELECT * FROM alembic_version;"

# 2. Manually rollback if needed
alembic downgrade -1

# 3. Fix the migration script
# 4. Re-deploy
```

## Migration Workflow

```
┌─────────────────────────────────────────────┐
│ 1. Modify SQLAlchemy models                 │
│    (core/db_schema/models.py)               │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│ 2. Generate migration                       │
│    alembic revision --autogenerate          │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│ 3. Review & edit migration script           │
│    alembic/versions/xxxxx.py                │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│ 4. Test locally                             │
│    alembic upgrade head                     │
│    alembic downgrade -1                     │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│ 5. Commit to version control                │
│    git add alembic/versions/xxxxx.py        │
│    git commit -m "Add migration"            │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│ 6. Deploy to staging                        │
│    Automatic via CI/CD                      │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│ 7. Test in staging                          │
│    Verify schema & data                     │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│ 8. Deploy to production                     │
│    PRE_DEPLOY: alembic upgrade head         │
└─────────────────────────────────────────────┘
```

## Environment Configuration

Alembic uses the `DATABASE_URL` environment variable to connect to the database:

```bash
# Development (default in alembic/env.py)
DATABASE_URL=postgresql://postgres:dev123@localhost:5432/sabc

# Staging
DATABASE_URL=postgresql://user:pass@staging-db:5432/sabc_staging

# Production (Digital Ocean managed database)
DATABASE_URL=${DB_URL}  # Auto-injected by Digital Ocean
```

The connection string is configured in `alembic/env.py` and reads from the environment.

## Schema Versioning

### Baseline Migration

The initial migration `b6af1117804a_initial_baseline_existing_schema.py` is a **no-op migration** that marks the starting point for version control. It doesn't change the database - it just records that the schema exists.

For existing databases:
```bash
# Mark database as being at baseline
alembic stamp b6af1117804a
```

For new databases:
```bash
# Apply all migrations from scratch
alembic upgrade head
```

### Migration Naming

Use clear, descriptive names:
- ✅ `alembic revision -m "Add phone_verified column to anglers"`
- ✅ `alembic revision -m "Create tournament_sponsors table"`
- ✅ `alembic revision -m "Add index on results.tournament_id"`
- ❌ `alembic revision -m "Update database"` (too vague)

## Additional Resources

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [PostgreSQL ALTER TABLE](https://www.postgresql.org/docs/current/sql-altertable.html)

## Support

For questions or issues with migrations:
1. Review this documentation
2. Check Alembic logs: `nix develop -c alembic history --verbose`
3. Consult the team before modifying production database
4. Always test in staging first!

---

**Last Updated:** 2025-10-09
**Alembic Version:** 1.13.1
**Initial Baseline Revision:** b6af1117804a
