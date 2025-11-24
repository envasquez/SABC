"""Helper functions for tournament operations."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Result

from core.db_schema import get_session


def auto_complete_past_tournaments() -> int:
    """
    Automatically mark past tournaments as complete if date has passed AND has results.

    Returns:
        Number of tournaments updated
    """
    with get_session() as session:
        # SQLite-compatible UPDATE using subquery instead of FROM clause
        # A tournament is complete if: date/time has passed AND has 1 or more results
        result: Result[Any] = session.execute(
            text(
                """
                UPDATE tournaments
                SET complete = TRUE
                WHERE event_id IN (
                    SELECT id FROM events
                    WHERE date < CURRENT_DATE
                )
                AND complete = FALSE
                AND id IN (
                    SELECT DISTINCT tournament_id FROM results
                )
                """
            )
        )
        session.commit()
        # MyPy doesn't recognize rowcount on Result[Any], but it exists at runtime
        return result.rowcount if result.rowcount is not None else 0  # type: ignore[attr-defined]
