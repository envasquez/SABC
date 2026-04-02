"""Add FK constraints for winning_option_id and last_edited_by

Revision ID: i6j7k8l9m0n1
Revises: h5i6j7k8l9m0
Create Date: 2026-04-01

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "i6j7k8l9m0n1"
down_revision: Union[str, None] = "h5i6j7k8l9m0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Clean up any orphaned references before adding constraints
    op.execute(
        """
        UPDATE polls SET winning_option_id = NULL
        WHERE winning_option_id IS NOT NULL
        AND winning_option_id NOT IN (SELECT id FROM poll_options)
        """
    )
    op.execute(
        """
        UPDATE news SET last_edited_by = NULL
        WHERE last_edited_by IS NOT NULL
        AND last_edited_by NOT IN (SELECT id FROM anglers)
        """
    )

    # Add FK constraint for polls.winning_option_id -> poll_options.id
    op.create_foreign_key(
        "fk_polls_winning_option_id",
        "polls",
        "poll_options",
        ["winning_option_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Add FK constraint for news.last_edited_by -> anglers.id
    op.create_foreign_key(
        "fk_news_last_edited_by",
        "news",
        "anglers",
        ["last_edited_by"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_news_last_edited_by", "news", type_="foreignkey")
    op.drop_constraint("fk_polls_winning_option_id", "polls", type_="foreignkey")
