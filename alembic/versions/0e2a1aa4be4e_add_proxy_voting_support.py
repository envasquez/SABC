"""Add proxy voting support

Revision ID: 0e2a1aa4be4e
Revises: d2195fd0305e
Create Date: 2025-11-12 19:20:08.198183

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0e2a1aa4be4e'
down_revision: Union[str, None] = 'd2195fd0305e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add columns to poll_votes table for proxy voting
    op.add_column('poll_votes', sa.Column('cast_by_admin_id', sa.Integer(), nullable=True))
    op.add_column('poll_votes', sa.Column('cast_by_admin', sa.Boolean(), nullable=False, server_default='false'))

    # Add foreign key constraint to anglers table
    op.create_foreign_key(
        'fk_poll_votes_cast_by_admin',
        'poll_votes',
        'anglers',
        ['cast_by_admin_id'],
        ['id'],
        ondelete='SET NULL'
    )

    # Add index for audit queries
    op.create_index(
        'ix_poll_votes_cast_by_admin_id',
        'poll_votes',
        ['cast_by_admin_id']
    )


def downgrade() -> None:
    # Remove index
    op.drop_index('ix_poll_votes_cast_by_admin_id', table_name='poll_votes')

    # Remove foreign key constraint
    op.drop_constraint('fk_poll_votes_cast_by_admin', 'poll_votes', type_='foreignkey')

    # Remove columns
    op.drop_column('poll_votes', 'cast_by_admin')
    op.drop_column('poll_votes', 'cast_by_admin_id')
