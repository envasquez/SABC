"""Add v_angler_tournament_results and v_team_tournament_results views

Revision ID: k8l9m0n1o2p3
Revises: j7k8l9m0n1o2
Create Date: 2026-05-26

Adds two read-only views that mask the ``results`` + ``team_results``
table duality so reader code doesn't have to know which format
(individual vs team) a tournament uses. This is the foundation step
for migrating the ~30 reader sites that currently each implement their
own UNION/EXISTS dance (or worse, silently miss team-format tournaments).

Why two views, not one:
- ``v_angler_tournament_results`` answers "what is this angler's result
  in this tournament?" — replaces profile/roster individual leaderboards,
  big-bass-per-angler, AOY-style queries, and the strategy-(A) sites
  that currently read ``results`` and miss team-format data.
- ``v_team_tournament_results`` answers "what teams/boats fished this
  tournament?" — replaces homepage podium, team awards, profile team
  finishes, and the synthetic-team logic in
  core/query_service/tournament_queries.get_team_results.

Both views:
- Exclude the "Admin User" seed angler (currently filtered ad-hoc in
  ~10 reader sites). Centralizing the filter here is the only safe
  place — every reader of the views gets it for free.
- Use UNION ALL with NOT EXISTS guards to avoid double-counting when
  both tables are populated for the same (tournament, angler) pair.
  Several existing call sites in core/query_service/data_queries.py
  lack these guards and double-count today — see follow-up phase.

NOT in scope here:
- Reader migrations. This migration only creates the views; the ~30
  reader sites stay on raw ``results``/``team_results`` queries until
  follow-up phases migrate them one cluster at a time.
- Reconciling ``Tournament.is_team`` vs ``Tournament.aoy_points``. The
  views don't depend on either flag — the table contents tell them
  what to do. Flag cleanup is a separate concern.
"""

from typing import Sequence, Union

from alembic import op

from core.db_schema.views import ALL_VIEW_DROP_SQL, ALL_VIEWS_SQL

# revision identifiers, used by Alembic.
revision: str = "k8l9m0n1o2p3"
down_revision: Union[str, None] = "j7k8l9m0n1o2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the two unification views. SQL lives in core/db_schema/views.py
    so the test fixture (which runs Base.metadata.create_all instead of
    Alembic) can materialize the same views in SQLite."""
    for sql in ALL_VIEWS_SQL:
        op.execute(sql)


def downgrade() -> None:
    """Drop both views. Reader code that depends on them will fail at
    query time — only run if all readers are first migrated back."""
    for sql in ALL_VIEW_DROP_SQL:
        op.execute(sql)
