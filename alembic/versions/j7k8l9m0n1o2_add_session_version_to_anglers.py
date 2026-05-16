"""Add session_version to anglers

Revision ID: j7k8l9m0n1o2
Revises: 1fee957f8379
Create Date: 2026-05-13

Adds a per-user session_version counter used to invalidate previously
issued session cookies (e.g. after a password change). Session cookies
are signed by SECRET_KEY but not server-validated; embedding this
version in the session and checking it on each request lets us revoke
sessions without rotating SECRET_KEY for the whole app.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "j7k8l9m0n1o2"
down_revision: Union[str, None] = "1fee957f8379"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add session_version column to anglers (default 1, NOT NULL)."""
    op.add_column(
        "anglers",
        sa.Column(
            "session_version",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )


def downgrade() -> None:
    """Remove session_version column from anglers."""
    op.drop_column("anglers", "session_version")
