"""Update default entry fee to 50

Change the server-side default for events.entry_fee and tournaments.entry_fee
from 25.00 to 50.00 ($50 per boat). Only affects the default for future rows;
existing entry fees are left unchanged.

Revision ID: l9m0n1o2p3q4
Revises: k8l9m0n1o2p3
Create Date: 2026-07-13 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "l9m0n1o2p3q4"
down_revision: Union[str, None] = "k8l9m0n1o2p3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "events",
        "entry_fee",
        existing_type=sa.NUMERIC(),
        server_default=sa.text("50.00"),
        existing_nullable=True,
    )
    op.alter_column(
        "tournaments",
        "entry_fee",
        existing_type=sa.NUMERIC(),
        server_default=sa.text("50.00"),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "tournaments",
        "entry_fee",
        existing_type=sa.NUMERIC(),
        server_default=sa.text("25.00"),
        existing_nullable=True,
    )
    op.alter_column(
        "events",
        "entry_fee",
        existing_type=sa.NUMERIC(),
        server_default=sa.text("25.00"),
        existing_nullable=True,
    )
