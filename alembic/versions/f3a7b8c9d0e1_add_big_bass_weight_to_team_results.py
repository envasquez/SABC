"""Add big_bass_weight column to team_results

Revision ID: f3a7b8c9d0e1
Revises: 8f50ddcd1de8
Create Date: 2026-03-23 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f3a7b8c9d0e1"
down_revision: Union[str, None] = "8f50ddcd1de8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "team_results",
        sa.Column("big_bass_weight", sa.Numeric(), nullable=True, server_default="0.0"),
    )


def downgrade() -> None:
    op.drop_column("team_results", "big_bass_weight")
