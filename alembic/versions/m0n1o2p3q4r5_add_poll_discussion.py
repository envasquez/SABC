"""Add poll discussion (comments + reactions)

Creates two tables backing the per-poll discussion board:

* ``poll_comments`` — member comments on a poll, with one level of threading
  via ``parent_comment_id`` and an ``updated_at`` marker set on edit.
* ``poll_comment_reactions`` — 👍 ("agree") reactions, one per angler per
  comment (unique constraint), toggled on/off.

Both cascade-delete with their parent poll / comment / angler so removing a
poll or member cleans up the associated discussion automatically.

Revision ID: m0n1o2p3q4r5
Revises: l9m0n1o2p3q4
Create Date: 2026-07-14 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "m0n1o2p3q4r5"
down_revision: Union[str, None] = "l9m0n1o2p3q4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "poll_comments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("poll_id", sa.Integer(), nullable=False),
        sa.Column("angler_id", sa.Integer(), nullable=False),
        sa.Column("parent_comment_id", sa.Integer(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["poll_id"], ["polls.id"], ondelete="CASCADE", name="fk_poll_comments_poll_id"
        ),
        sa.ForeignKeyConstraint(
            ["angler_id"], ["anglers.id"], ondelete="CASCADE", name="fk_poll_comments_angler_id"
        ),
        sa.ForeignKeyConstraint(
            ["parent_comment_id"],
            ["poll_comments.id"],
            ondelete="CASCADE",
            name="fk_poll_comments_parent_comment_id",
        ),
    )
    op.create_index("ix_poll_comments_poll_id", "poll_comments", ["poll_id"])
    op.create_index("ix_poll_comments_angler_id", "poll_comments", ["angler_id"])
    op.create_index("ix_poll_comments_parent_comment_id", "poll_comments", ["parent_comment_id"])

    op.create_table(
        "poll_comment_reactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("comment_id", sa.Integer(), nullable=False),
        sa.Column("angler_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["comment_id"],
            ["poll_comments.id"],
            ondelete="CASCADE",
            name="fk_poll_comment_reactions_comment_id",
        ),
        sa.ForeignKeyConstraint(
            ["angler_id"],
            ["anglers.id"],
            ondelete="CASCADE",
            name="fk_poll_comment_reactions_angler_id",
        ),
        sa.UniqueConstraint("comment_id", "angler_id", name="uq_poll_comment_reaction"),
    )
    op.create_index(
        "ix_poll_comment_reactions_comment_id", "poll_comment_reactions", ["comment_id"]
    )
    op.create_index("ix_poll_comment_reactions_angler_id", "poll_comment_reactions", ["angler_id"])


def downgrade() -> None:
    op.drop_index("ix_poll_comment_reactions_angler_id", table_name="poll_comment_reactions")
    op.drop_index("ix_poll_comment_reactions_comment_id", table_name="poll_comment_reactions")
    op.drop_table("poll_comment_reactions")

    op.drop_index("ix_poll_comments_parent_comment_id", table_name="poll_comments")
    op.drop_index("ix_poll_comments_angler_id", table_name="poll_comments")
    op.drop_index("ix_poll_comments_poll_id", table_name="poll_comments")
    op.drop_table("poll_comments")
