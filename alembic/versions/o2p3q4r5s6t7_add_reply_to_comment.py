"""Add reply_to_comment_id to poll_comments

Camp-A ("flat with attribution") threading: a reply can now target any comment
in the thread, including another reply, but it still stores its thread root in
``parent_comment_id`` so the display stays one level deep. ``reply_to_comment_id``
records the specific comment that was replied to, powering the "Replying to
<name>" label and the reply email notification.

ON DELETE SET NULL: if the targeted comment is removed, replies to it survive
(they just lose the attribution label).

Revision ID: o2p3q4r5s6t7
Revises: n1o2p3q4r5s6
Create Date: 2026-07-28 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "o2p3q4r5s6t7"
down_revision: Union[str, None] = "n1o2p3q4r5s6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "poll_comments",
        sa.Column("reply_to_comment_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_poll_comments_reply_to_comment_id",
        "poll_comments",
        "poll_comments",
        ["reply_to_comment_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_poll_comments_reply_to_comment_id", "poll_comments", ["reply_to_comment_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_poll_comments_reply_to_comment_id", table_name="poll_comments")
    op.drop_constraint("fk_poll_comments_reply_to_comment_id", "poll_comments", type_="foreignkey")
    op.drop_column("poll_comments", "reply_to_comment_id")
