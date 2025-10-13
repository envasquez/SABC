# Database Migrations Guide

This guide explains how to manage database schema changes using Alembic migrations in the SABC project.

## Overview

The SABC application uses Alembic for database migration management. Migrations are version-controlled changes to the database schema that can be applied or rolled back.

## Migration History

### Current Migrations

1. **b6af1117804a** - Initial baseline (existing schema)
2. **1d153ef88dd8** - Database constraints and cascades
3. **ccb51aa357c6** - Performance indexes (Week 3 optimization)

## Common Operations

### Check Current Migration Version

```bash
alembic current
```

### View Migration History

```bash
alembic history --verbose
```

### Apply All Pending Migrations

```bash
alembic upgrade head
```

### Rollback One Migration

```bash
alembic downgrade -1
```

### Create a New Migration

#### Auto-generate from model changes:

```bash
alembic revision --autogenerate -m "Add new column to users table"
```

#### Create empty migration for manual SQL:

```bash
alembic revision -m "Add custom index"
```

## Migration Best Practices

### 1. Always Test Migrations

```bash
# Test upgrade
alembic upgrade head

# Test downgrade
alembic downgrade -1

# Re-apply
alembic upgrade head
```

### 2. Make Migrations Idempotent

Always use `IF EXISTS` and `IF NOT EXISTS` checks:

```python
conn.execute(sa.text("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_name') THEN
            CREATE INDEX idx_name ON table_name(column_name);
        END IF;
    END $$;
"""))
```

### 3. Include Downgrade Logic

Every migration should have proper `downgrade()` function:

```python
def downgrade() -> None:
    """Remove changes made in upgrade."""
    conn = op.get_bind()
    conn.execute(sa.text("DROP INDEX IF EXISTS idx_name"))
```

### 4. Document Migration Purpose

Include comprehensive docstrings:

```python
"""Add indexes for poll voting performance

This migration adds:
1. Composite index on (poll_id, angler_id) for vote lookups
2. Index on poll_id for vote counting

Revision ID: abc123def456
Revises: previous_revision
Create Date: 2025-01-15 10:30:00
"""
```

## Production Deployment

### Automatic Migration Application

**Migrations are automatically applied on production startup!**

The production Docker Compose configuration ([docker-compose.prod.yml](../docker-compose.prod.yml:33-34)) runs `alembic upgrade head` during container startup, ensuring the database schema is always up-to-date.

Startup sequence:
1. Wait for PostgreSQL to be ready (15 seconds)
2. **Apply database migrations** (`alembic upgrade head`)
3. Setup database views
4. Create admin user if needed
5. Start FastAPI server

This means:
- ✅ New deployments automatically get the latest schema
- ✅ No manual migration steps required during deployment
- ✅ Migrations are idempotent and safe to re-run
- ✅ Failed migrations prevent the server from starting (fail-fast)

### Manual Deployment (if needed)

If you need to apply migrations manually outside of Docker:

1. **Backup Database**
   ```bash
   pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql
   ```

2. **Check Current Version**
   ```bash
   alembic current
   ```

3. **Review Pending Migrations**
   ```bash
   alembic history
   ```

4. **Apply Migrations**
   ```bash
   alembic upgrade head
   ```

5. **Verify Success**
   ```bash
   alembic current
   # Should show latest migration
   ```

### Rollback Plan

If migration fails:

```bash
# Rollback to previous version
alembic downgrade -1

# Or rollback to specific version
alembic downgrade <revision_id>

# Restore from backup if needed
psql $DATABASE_URL < backup_file.sql
```

## Migration Structure

### File Organization

```
alembic/
├── versions/
│   ├── b6af1117804a_initial_baseline.py
│   ├── 1d153ef88dd8_add_constraints.py
│   └── ccb51aa357c6_add_indexes.py
├── env.py                 # Alembic environment config
├── script.py.mako         # Migration template
└── alembic.ini            # Alembic configuration
```

### Migration File Template

```python
"""Brief description of changes

Detailed explanation of what this migration does and why.

Revision ID: generated_id
Revises: parent_id
Create Date: timestamp
"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = 'generated_id'
down_revision: Union[str, None] = 'parent_id'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply migration changes."""
    conn = op.get_bind()

    # Your upgrade logic here
    conn.execute(sa.text("""
        -- SQL commands
    """))

    print("✅ Migration applied successfully")


def downgrade() -> None:
    """Revert migration changes."""
    conn = op.get_bind()

    # Your downgrade logic here
    conn.execute(sa.text("""
        -- SQL commands to revert
    """))

    print("✅ Migration reverted successfully")
```

## Common Migration Patterns

### Adding a Column

```python
def upgrade() -> None:
    op.add_column('table_name',
        sa.Column('new_column', sa.String(50), nullable=True)
    )

def downgrade() -> None:
    op.drop_column('table_name', 'new_column')
```

### Adding an Index

```python
def upgrade() -> None:
    op.create_index('idx_table_column', 'table_name', ['column_name'])

def downgrade() -> None:
    op.drop_index('idx_table_column')
```

### Adding a Foreign Key

```python
def upgrade() -> None:
    op.create_foreign_key(
        'fk_table_ref',
        'source_table', 'reference_table',
        ['source_column'], ['ref_column']
    )

def downgrade() -> None:
    op.drop_constraint('fk_table_ref', 'source_table')
```

## Troubleshooting

### Migration Out of Sync

```bash
# Check current state
alembic current

# Stamp database to specific version (use with caution!)
alembic stamp <revision_id>
```

### Multiple Migration Branches

```bash
# List all heads
alembic heads

# Merge branches
alembic merge <rev1> <rev2> -m "Merge branches"
```

### Migration Conflicts

1. Pull latest migrations
2. Check for conflicts: `alembic history`
3. Create merge migration if needed
4. Test thoroughly before deploying

## See Also

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [DATABASE_MIGRATIONS.md](DATABASE_MIGRATIONS.md) - Quick reference
- [CLAUDE.md](../CLAUDE.md) - Project development guidelines
