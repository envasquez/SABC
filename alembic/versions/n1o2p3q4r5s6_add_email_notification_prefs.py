"""Add email notification preferences to anglers

Adds three boolean columns to ``anglers``:

* ``email_opt_in``   — master switch; False means the member never receives
  any notification email, regardless of the category flags below.
* ``notify_news``     — email when club news is posted.
* ``notify_replies``  — email when someone replies to the member's poll comment.

All default TRUE (server_default) so existing members keep receiving the news
emails they already get and start receiving reply notifications; members opt
out from their profile.

Revision ID: n1o2p3q4r5s6
Revises: m0n1o2p3q4r5
Create Date: 2026-07-28 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "n1o2p3q4r5s6"
down_revision: Union[str, None] = "m0n1o2p3q4r5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_COLUMNS = ("email_opt_in", "notify_news", "notify_replies")


def upgrade() -> None:
    for col in _COLUMNS:
        op.add_column(
            "anglers",
            sa.Column(col, sa.Boolean(), nullable=False, server_default=sa.text("true")),
        )


def downgrade() -> None:
    for col in reversed(_COLUMNS):
        op.drop_column("anglers", col)
