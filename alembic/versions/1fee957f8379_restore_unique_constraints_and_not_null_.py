"""restore unique constraints and not null fks

Revision ID: 1fee957f8379
Revises: i6j7k8l9m0n1
Create Date: 2026-05-13 20:20:03.954019

Restores four UNIQUE constraints that were silently dropped by migration
1ed98f6d9bcc when it added FK indexes:

  - anglers_email_key (anglers.email)
  - events_date_key (events.date)
  - officer_positions_position_year_key (officer_positions.position, year)
  - unique_tournament_team (team_results.tournament_id, angler1_id, angler2_id)

Also tightens NOT NULL on six required FK columns that should never be
nullable. Most importantly, poll_votes.poll_id and poll_votes.angler_id
being nullable bypasses uq_poll_vote_angler (NULL != NULL in Postgres),
allowing one angler to vote N times if the FK is NULL.

The upgrade is defensive: it queries for violations BEFORE altering and
raises RuntimeError with a clear remediation hint instead of letting the
DDL fail mid-flight. Pairs with scripts/audit_db_integrity.py.
"""

from typing import List, Sequence, Tuple, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1fee957f8379"
down_revision: Union[str, None] = "i6j7k8l9m0n1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Columns that must be NOT NULL after this migration. angler2_id on
# team_results is intentionally excluded: solo entries legitimately
# store NULL there.
_NOT_NULL_FKS: List[Tuple[str, str]] = [
    ("poll_votes", "poll_id"),
    ("poll_votes", "angler_id"),
    ("results", "tournament_id"),
    ("results", "angler_id"),
    ("team_results", "tournament_id"),
    ("team_results", "angler1_id"),
]


def upgrade() -> None:
    conn = op.get_bind()

    # --- Defensive pre-checks for UNIQUE constraints ---------------------

    dup_emails = conn.execute(
        sa.text(
            "SELECT email, COUNT(*) AS cnt FROM anglers "
            "WHERE email IS NOT NULL "
            "GROUP BY email HAVING COUNT(*) > 1"
        )
    ).fetchall()
    if dup_emails:
        raise RuntimeError(
            f"Cannot restore UNIQUE(anglers.email): {len(dup_emails)} duplicate "
            f"email(s) exist. Run scripts/audit_db_integrity.py for details, "
            f"deduplicate via a data migration, then retry."
        )

    dup_event_dates = conn.execute(
        sa.text("SELECT date, COUNT(*) AS cnt FROM events GROUP BY date HAVING COUNT(*) > 1")
    ).fetchall()
    if dup_event_dates:
        raise RuntimeError(
            f"Cannot restore UNIQUE(events.date): {len(dup_event_dates)} "
            f"duplicate date(s) exist. Run scripts/audit_db_integrity.py for "
            f"details and resolve via a data migration before retrying."
        )

    dup_officer = conn.execute(
        sa.text(
            "SELECT position, year, COUNT(*) AS cnt FROM officer_positions "
            "GROUP BY position, year HAVING COUNT(*) > 1"
        )
    ).fetchall()
    if dup_officer:
        raise RuntimeError(
            f"Cannot restore UNIQUE(officer_positions.position, year): "
            f"{len(dup_officer)} duplicate (position, year) pair(s) exist. "
            f"Run scripts/audit_db_integrity.py for details and resolve via a "
            f"data migration before retrying."
        )

    # team_results uniqueness uses postgresql_nulls_not_distinct=False, so
    # rows with NULL angler2_id never collide with each other. Only flag
    # rows that violate the would-be constraint where all keys are NOT NULL.
    dup_team = conn.execute(
        sa.text(
            "SELECT tournament_id, angler1_id, angler2_id, COUNT(*) AS cnt "
            "FROM team_results "
            "WHERE tournament_id IS NOT NULL "
            "  AND angler1_id IS NOT NULL "
            "  AND angler2_id IS NOT NULL "
            "GROUP BY tournament_id, angler1_id, angler2_id "
            "HAVING COUNT(*) > 1"
        )
    ).fetchall()
    if dup_team:
        raise RuntimeError(
            f"Cannot restore UNIQUE(team_results.tournament_id, angler1_id, "
            f"angler2_id): {len(dup_team)} duplicate team(s) exist. Run "
            f"scripts/audit_db_integrity.py for details and resolve via a "
            f"data migration before retrying."
        )

    # --- Defensive pre-checks for NOT NULL -------------------------------

    for table, col in _NOT_NULL_FKS:
        null_count = conn.execute(
            sa.text(f"SELECT COUNT(*) FROM {table} WHERE {col} IS NULL")
        ).scalar()
        if null_count:
            raise RuntimeError(
                f"Cannot ALTER {table}.{col} TO NOT NULL: {null_count} NULL "
                f"row(s) exist. Run scripts/audit_db_integrity.py for samples "
                f"and resolve via a data migration before retrying."
            )

    # --- Apply changes ---------------------------------------------------

    op.create_unique_constraint("anglers_email_key", "anglers", ["email"])
    op.create_unique_constraint("events_date_key", "events", ["date"])
    op.create_unique_constraint(
        "officer_positions_position_year_key",
        "officer_positions",
        ["position", "year"],
    )
    op.create_unique_constraint(
        "unique_tournament_team",
        "team_results",
        ["tournament_id", "angler1_id", "angler2_id"],
    )

    for table, col in _NOT_NULL_FKS:
        op.alter_column(table, col, existing_type=sa.Integer(), nullable=False)


def downgrade() -> None:
    for table, col in reversed(_NOT_NULL_FKS):
        op.alter_column(table, col, existing_type=sa.Integer(), nullable=True)

    op.drop_constraint("unique_tournament_team", "team_results", type_="unique")
    op.drop_constraint("officer_positions_position_year_key", "officer_positions", type_="unique")
    op.drop_constraint("events_date_key", "events", type_="unique")
    op.drop_constraint("anglers_email_key", "anglers", type_="unique")
