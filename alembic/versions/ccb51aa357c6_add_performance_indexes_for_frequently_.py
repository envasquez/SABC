"""Add performance indexes for frequently queried columns

This migration adds indexes to improve query performance for:
1. Poll votes - composite index on (poll_id, angler_id) for vote lookups
2. Results - index on tournament_id for tournament results queries
3. Password reset tokens - index on token for password reset lookups
4. Polls - composite index on (event_id, starts_at, closes_at) for poll queries

Revision ID: ccb51aa357c6
Revises: 1d153ef88dd8
Create Date: 2025-10-12 21:33:16.050277

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision: str = "ccb51aa357c6"
down_revision: Union[str, None] = "1d153ef88dd8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add performance indexes for frequently queried columns."""
    conn = op.get_bind()

    # Add composite index on poll_votes for (poll_id, angler_id) lookups
    conn.execute(
        sa.text("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE indexname = 'idx_poll_votes_poll_angler'
            ) THEN
                CREATE INDEX idx_poll_votes_poll_angler
                ON poll_votes(poll_id, angler_id);
            END IF;
        END $$;
    """)
    )

    # Add index on results.tournament_id for tournament results queries
    conn.execute(
        sa.text("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE indexname = 'idx_results_tournament'
            ) THEN
                CREATE INDEX idx_results_tournament
                ON results(tournament_id);
            END IF;
        END $$;
    """)
    )

    # Add index on password_reset_tokens.token for password reset lookups
    conn.execute(
        sa.text("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE indexname = 'idx_reset_tokens_token'
            ) THEN
                CREATE INDEX idx_reset_tokens_token
                ON password_reset_tokens(token);
            END IF;
        END $$;
    """)
    )

    # Add composite index on polls for event and date range queries
    conn.execute(
        sa.text("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE indexname = 'idx_polls_event_dates'
            ) THEN
                CREATE INDEX idx_polls_event_dates
                ON polls(event_id, starts_at, closes_at);
            END IF;
        END $$;
    """)
    )

    # Add index on poll_votes.poll_id for vote counting queries
    conn.execute(
        sa.text("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE indexname = 'idx_poll_votes_poll_id'
            ) THEN
                CREATE INDEX idx_poll_votes_poll_id
                ON poll_votes(poll_id);
            END IF;
        END $$;
    """)
    )

    print("✅ Performance indexes created successfully")


def downgrade() -> None:
    """Remove performance indexes."""
    conn = op.get_bind()

    conn.execute(sa.text("DROP INDEX IF EXISTS idx_poll_votes_poll_angler"))
    conn.execute(sa.text("DROP INDEX IF EXISTS idx_results_tournament"))
    conn.execute(sa.text("DROP INDEX IF EXISTS idx_reset_tokens_token"))
    conn.execute(sa.text("DROP INDEX IF EXISTS idx_polls_event_dates"))
    conn.execute(sa.text("DROP INDEX IF EXISTS idx_poll_votes_poll_id"))

    print("✅ Performance indexes removed")
