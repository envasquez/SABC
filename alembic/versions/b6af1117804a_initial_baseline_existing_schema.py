"""Initial baseline - existing schema

This is a baseline migration for the existing SABC database.
It doesn't perform any operations - it just marks the current schema state
so that future migrations can be applied incrementally.

To mark the database as being at this revision without running any changes:
    alembic stamp head

Revision ID: b6af1117804a
Revises:
Create Date: 2025-10-09 18:11:21.664308

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "b6af1117804a"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No changes - this is a baseline migration for existing database."""
    pass


def downgrade() -> None:
    """No changes - this is a baseline migration for existing database."""
    pass
