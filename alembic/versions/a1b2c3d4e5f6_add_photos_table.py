"""Add photos table

Revision ID: a1b2c3d4e5f6
Revises: 4ac79f8a3507
Create Date: 2025-12-18 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "4ac79f8a3507"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "photos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("angler_id", sa.Integer(), nullable=False),
        sa.Column("tournament_id", sa.Integer(), nullable=True),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("caption", sa.String(200), nullable=True),
        sa.Column("is_big_bass", sa.Boolean(), nullable=True, default=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["angler_id"], ["anglers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_photos_angler_id"), "photos", ["angler_id"], unique=False)
    op.create_index(op.f("ix_photos_tournament_id"), "photos", ["tournament_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_photos_tournament_id"), table_name="photos")
    op.drop_index(op.f("ix_photos_angler_id"), table_name="photos")
    op.drop_table("photos")
