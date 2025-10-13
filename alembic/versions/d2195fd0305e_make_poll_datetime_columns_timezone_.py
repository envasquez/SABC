"""Make poll datetime columns timezone-aware

Revision ID: d2195fd0305e
Revises: ccb51aa357c6
Create Date: 2025-10-13 11:15:46.529054

"""

from typing import Sequence, Union

from alembic import op  # type: ignore[attr-defined]

# revision identifiers, used by Alembic.
revision: str = "d2195fd0305e"
down_revision: Union[str, None] = "ccb51aa357c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Convert polls table datetime columns to timezone-aware (TIMESTAMPTZ)
    # Existing naive timestamps are assumed to be UTC
    op.execute("""
        ALTER TABLE polls
        ALTER COLUMN created_at TYPE TIMESTAMPTZ
        USING created_at AT TIME ZONE 'UTC'
    """)
    op.execute("""
        ALTER TABLE polls
        ALTER COLUMN starts_at TYPE TIMESTAMPTZ
        USING starts_at AT TIME ZONE 'UTC'
    """)
    op.execute("""
        ALTER TABLE polls
        ALTER COLUMN closes_at TYPE TIMESTAMPTZ
        USING closes_at AT TIME ZONE 'UTC'
    """)

    # Convert poll_votes table datetime column to timezone-aware
    op.execute("""
        ALTER TABLE poll_votes
        ALTER COLUMN voted_at TYPE TIMESTAMPTZ
        USING voted_at AT TIME ZONE 'UTC'
    """)


def downgrade() -> None:
    # Revert polls table datetime columns to timezone-naive (TIMESTAMP)
    op.execute("""
        ALTER TABLE polls
        ALTER COLUMN created_at TYPE TIMESTAMP
        USING created_at AT TIME ZONE 'UTC'
    """)
    op.execute("""
        ALTER TABLE polls
        ALTER COLUMN starts_at TYPE TIMESTAMP
        USING starts_at AT TIME ZONE 'UTC'
    """)
    op.execute("""
        ALTER TABLE polls
        ALTER COLUMN closes_at TYPE TIMESTAMP
        USING closes_at AT TIME ZONE 'UTC'
    """)

    # Revert poll_votes table datetime column to timezone-naive
    op.execute("""
        ALTER TABLE poll_votes
        ALTER COLUMN voted_at TYPE TIMESTAMP
        USING voted_at AT TIME ZONE 'UTC'
    """)
