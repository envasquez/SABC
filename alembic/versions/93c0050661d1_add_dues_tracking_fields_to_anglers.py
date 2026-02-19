"""Add dues tracking fields to anglers

Revision ID: 93c0050661d1
Revises: 79e50a317657
Create Date: 2026-02-19 07:26:52.889804

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "93c0050661d1"
down_revision: Union[str, None] = "79e50a317657"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add dues tracking fields to anglers table."""
    op.add_column("anglers", sa.Column("dues_paid_through", sa.Date(), nullable=True))
    op.add_column(
        "anglers", sa.Column("dues_banner_dismissed_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    """Remove dues tracking fields from anglers table."""
    op.drop_column("anglers", "dues_banner_dismissed_at")
    op.drop_column("anglers", "dues_paid_through")
