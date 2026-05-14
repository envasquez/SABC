"""Helper functions for tournament operations."""

from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.engine import Result

from core.db_schema import get_session


def auto_complete_past_tournaments(tournament_id: Optional[int] = None) -> int:
    """
    Mark a past tournament complete if its event date has passed AND it has results.

    Previously this ran a full-table UPDATE on every page render of
    ``/tournaments/{id}`` and the admin enter-results page. Now scoped to a
    single tournament_id when provided, so it becomes a one-row index lookup
    instead of a table scan.

    When ``tournament_id`` is ``None`` (legacy / batch usage) the original
    full-table behavior is preserved.

    Args:
        tournament_id: Specific tournament to consider. Required for the
            single-row fast path.

    Returns:
        Number of tournaments updated.
    """
    with get_session() as session:
        if tournament_id is not None:
            result: Result[Any] = session.execute(
                text(
                    """
                    UPDATE tournaments
                    SET complete = TRUE
                    WHERE id = :tid
                    AND complete = FALSE
                    AND event_id IN (
                        SELECT id FROM events WHERE date < CURRENT_DATE
                    )
                    AND (
                        id IN (SELECT DISTINCT tournament_id FROM results)
                        OR id IN (SELECT DISTINCT tournament_id FROM team_results)
                    )
                    """
                ),
                {"tid": tournament_id},
            )
        else:
            # Legacy batch path: still supported for callers that genuinely
            # want a sweep (e.g. cron, scripts).
            result = session.execute(
                text(
                    """
                    UPDATE tournaments
                    SET complete = TRUE
                    WHERE event_id IN (
                        SELECT id FROM events
                        WHERE date < CURRENT_DATE
                    )
                    AND complete = FALSE
                    AND (
                        id IN (SELECT DISTINCT tournament_id FROM results)
                        OR id IN (SELECT DISTINCT tournament_id FROM team_results)
                    )
                    """
                )
            )
        session.commit()
        # MyPy doesn't recognize rowcount on Result[Any], but it exists at runtime
        return result.rowcount if result.rowcount is not None else 0  # type: ignore[attr-defined]
