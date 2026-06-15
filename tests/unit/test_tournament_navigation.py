"""Regression tests for Prev/Next tournament navigation (issue #345).

Navigation must traverse exactly the set of tournaments the homepage links a
"View Results" button for: SABC tournaments, not cancelled, that are either
complete or still upcoming. Two historical bugs are guarded here:

1. Ordering by raw tournament id (insertion order) instead of event date, so
   "Next" could jump to a chronologically earlier event that merely had a
   higher id (the cancelled Jan-2026 event in the original report).
2. Walking onto a past tournament that was never completed (no results) -- it
   has no homepage link, yet appeared in navigation.
"""

from datetime import date, time, timedelta

from core.db_schema import Event, Tournament, engine
from core.query_service import QueryService


def _make_tournament(
    session,
    *,
    event_date: date,
    name: str,
    complete: bool,
    is_cancelled: bool = False,
    event_type: str = "sabc_tournament",
) -> int:
    """Create an event + tournament and return the tournament id."""
    event = Event(
        date=event_date,
        year=event_date.year,
        name=name,
        event_type=event_type,
        is_cancelled=is_cancelled,
    )
    session.add(event)
    session.commit()
    session.refresh(event)

    tournament = Tournament(
        event_id=event.id,
        name=name,
        fish_limit=5,
        entry_fee=25.00,
        is_team=True,
        is_paper=False,
        big_bass_carryover=0.0,
        complete=complete,
        aoy_points=True,
        limit_type="angler",
        start_time=time(6, 0),
        end_time=time(15, 0),
    )
    session.add(tournament)
    session.commit()
    session.refresh(tournament)
    return tournament.id


class TestTournamentNavigation:
    """Prev/Next navigation only walks homepage-linked tournaments, by date."""

    def test_navigation_skips_phantom_and_cancelled(self, db_session):
        today = date.today()

        # Insert in an order that deliberately scrambles ids vs. dates so the
        # old "ORDER BY id" logic would fail: the cancelled event gets a low
        # id but an early date.
        may17_id = _make_tournament(
            db_session, event_date=today - timedelta(days=29), name="May 17", complete=True
        )
        # Cancelled, earlier date, but a HIGHER id than May 17 (reproduces #345).
        _make_tournament(
            db_session,
            event_date=today - timedelta(days=120),
            name="Cancelled Jan",
            complete=True,
            is_cancelled=True,
        )
        # Past but never completed -- no homepage link, must be skipped.
        phantom_may16_id = _make_tournament(
            db_session, event_date=today - timedelta(days=30), name="May 16 phantom", complete=False
        )
        april_id = _make_tournament(
            db_session, event_date=today - timedelta(days=60), name="April", complete=True
        )
        # Upcoming (incomplete but in the future) -- IS navigable.
        future_id = _make_tournament(
            db_session, event_date=today + timedelta(days=30), name="June upcoming", complete=False
        )

        with engine.connect() as conn:
            qs = QueryService(conn)

            # Previous from May 17 must land on April, skipping the past
            # incomplete "May 16 phantom" and the cancelled event.
            prev_id = qs.get_previous_tournament_id(may17_id, today - timedelta(days=29), today)
            assert prev_id == april_id

            # Next from May 17 must reach the upcoming June tournament,
            # skipping the cancelled event entirely.
            next_id = qs.get_next_tournament_id(may17_id, today - timedelta(days=29), today)
            assert next_id == future_id

            # The phantom is never reachable from either direction.
            assert (
                qs.get_next_tournament_id(april_id, today - timedelta(days=60), today) == may17_id
            )
            prev_of_future = qs.get_previous_tournament_id(
                future_id, today + timedelta(days=30), today
            )
            assert prev_of_future == may17_id
            assert prev_of_future != phantom_may16_id

    def test_endpoints_return_none_at_boundaries(self, db_session):
        today = date.today()
        only_id = _make_tournament(
            db_session, event_date=today - timedelta(days=5), name="Only", complete=True
        )
        with engine.connect() as conn:
            qs = QueryService(conn)
            assert qs.get_next_tournament_id(only_id, today - timedelta(days=5), today) is None
            assert qs.get_previous_tournament_id(only_id, today - timedelta(days=5), today) is None
