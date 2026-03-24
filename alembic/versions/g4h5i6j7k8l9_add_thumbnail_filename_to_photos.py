"""Add thumbnail_filename to photos

Revision ID: g4h5i6j7k8l9
Revises: f3a7b8c9d0e1
Create Date: 2026-03-24

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "g4h5i6j7k8l9"
down_revision: Union[str, None] = "f3a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("photos", sa.Column("thumbnail_filename", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("photos", "thumbnail_filename")
