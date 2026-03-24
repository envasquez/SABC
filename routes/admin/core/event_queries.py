from typing import Any, Dict, List, Literal

from sqlalchemy import Date, cast, exists, func, select
from sqlalchemy.orm import Session

from core.db_schema import Event, Poll, Result, Tournament, get_session


def _build_sabc_tournament_query(
    session: Session,
    time_filter: Literal["past", "upcoming"],
) -> List[Dict[str, Any]]:
    """Build a query for SABC tournaments with common fields.

    Args:
        session: Database session
        time_filter: "past" for past tournaments, "upcoming" for future ones

    Returns:
        List of tournament dictionaries with event details
    """
    # Common columns for both queries
    base_columns = [
        Event.id,
        Event.date,
        Event.name,
        Event.description,
        Event.event_type,
        Event.entry_fee,
        Event.lake_name,
        Event.start_time,
        Event.weigh_in_time,
        Event.holiday_name,
        exists(select(1).where(Poll.event_id == Event.id).correlate_except(Poll)).label("has_poll"),
        exists(select(1).where(Tournament.event_id == Event.id).correlate_except(Tournament)).label(
            "has_tournament"
        ),
        func.coalesce(Tournament.complete, False).label("tournament_complete"),
    ]

    # Add time-specific column
    if time_filter == "past":
        base_columns.append(
            exists(
                select(1).where(Result.tournament_id == Tournament.id).correlate_except(Result)
            ).label("has_results")
        )
    else:
        base_columns.append(
            exists(
                select(1)
                .where((Poll.event_id == Event.id) & (Poll.closed.is_(False)))
                .correlate_except(Poll)
            ).label("poll_active")
        )

    # Build query with appropriate filter and order
    query = session.query(*base_columns).outerjoin(Tournament, Event.id == Tournament.event_id)

    if time_filter == "past":
        query = query.filter(
            Event.date < cast(func.current_date(), Date),
            Event.event_type == "sabc_tournament",
        ).order_by(Event.date.desc())
    else:
        query = query.filter(
            Event.date >= cast(func.current_date(), Date),
            Event.event_type == "sabc_tournament",
        ).order_by(Event.date)

    results = query.all()

    # Convert to dictionaries
    tournaments = []
    for e in results:
        tournament_dict: Dict[str, Any] = {
            "id": e[0],
            "date": e[1],
            "name": e[2] or "",
            "description": e[3] or "",
            "event_type": e[4] or "sabc_tournament",
            "entry_fee": e[5],
            "lake_name": e[6],
            "start_time": e[7],
            "weigh_in_time": e[8],
            "holiday_name": e[9],
            "has_poll": bool(e[10]),
            "has_tournament": bool(e[11]),
            "tournament_complete": bool(e[12]),
        }
        # Add time-specific field
        if time_filter == "past":
            tournament_dict["has_results"] = bool(e[13])
        else:
            tournament_dict["poll_active"] = bool(e[13])
        tournaments.append(tournament_dict)

    return tournaments


def get_sabc_tournaments(
    time_filter: Literal["past", "upcoming"],
) -> List[Dict[str, Any]]:
    """Get SABC tournaments with all details for admin dashboard.

    Args:
        time_filter: "past" for past tournaments, "upcoming" for future ones

    Returns:
        List of tournament dictionaries
    """
    with get_session() as session:
        return _build_sabc_tournament_query(session, time_filter)


def get_upcoming_events_data(page: int, per_page: int) -> tuple[List[Dict[str, Any]], int]:
    offset = (page - 1) * per_page

    with get_session() as session:
        # Get total count
        total = (
            session.query(func.count(Event.id))
            .filter(Event.date >= cast(func.current_date(), Date))
            .scalar()
            or 0
        )

        # Get upcoming events with subqueries for existence checks
        events_query = (
            session.query(
                Event.id,
                Event.date,
                Event.name,
                Event.description,
                Event.event_type,
                Event.year,
                func.extract("dow", Event.date).label("day_num"),
                exists(select(1).where(Poll.event_id == Event.id).correlate_except(Poll)).label(
                    "has_poll"
                ),
                exists(
                    select(1).where(Tournament.event_id == Event.id).correlate_except(Tournament)
                ).label("has_tournament"),
                exists(
                    select(1)
                    .where((Poll.event_id == Event.id) & (Poll.closed.is_(False)))
                    .correlate_except(Poll)
                ).label("poll_active"),
                Event.start_time,
                Event.weigh_in_time,
                Event.entry_fee,
                Event.lake_name,
                Event.ramp_name,
                Event.holiday_name,
                func.coalesce(Tournament.complete, False).label("tournament_complete"),
            )
            .outerjoin(Tournament, Event.id == Tournament.event_id)
            .filter(Event.date >= cast(func.current_date(), Date))
            .order_by(Event.date)
            .limit(per_page)
            .offset(offset)
            .all()
        )

        events = [
            {
                "id": e[0],
                "date": e[1],
                "name": e[2] or "",
                "description": e[3] or "",
                "event_type": e[4] or "sabc_tournament",
                "day_name": e[6],
                "has_poll": bool(e[7]),
                "has_tournament": bool(e[8]),
                "poll_active": bool(e[9]),
                "start_time": e[10],
                "weigh_in_time": e[11],
                "entry_fee": e[12],
                "lake_name": e[13],
                "ramp_name": e[14],
                "holiday_name": e[15],
                "tournament_complete": bool(e[16]),
            }
            for e in events_query
        ]

    return events, total


def get_past_events_data(page: int, per_page: int) -> tuple[List[Dict[str, Any]], int]:
    offset = (page - 1) * per_page

    with get_session() as session:
        # Get total count
        total = (
            session.query(func.count(Event.id))
            .filter(
                Event.date < cast(func.current_date(), Date),
                Event.event_type == "sabc_tournament",
            )
            .scalar()
            or 0
        )

        # Get past events
        past_events_query = (
            session.query(
                Event.id,
                Event.date,
                Event.name,
                Event.description,
                Event.event_type,
                Event.entry_fee,
                Event.lake_name,
                Event.start_time,
                Event.weigh_in_time,
                Event.holiday_name,
                exists(select(1).where(Poll.event_id == Event.id).correlate_except(Poll)).label(
                    "has_poll"
                ),
                exists(
                    select(1).where(Tournament.event_id == Event.id).correlate_except(Tournament)
                ).label("has_tournament"),
                func.coalesce(Tournament.complete, False).label("tournament_complete"),
                exists(
                    select(1).where(Result.tournament_id == Tournament.id).correlate_except(Result)
                ).label("has_results"),
            )
            .outerjoin(Tournament, Event.id == Tournament.event_id)
            .filter(
                Event.date < cast(func.current_date(), Date),
                Event.event_type == "sabc_tournament",
            )
            .order_by(Event.date.desc())
            .limit(per_page)
            .offset(offset)
            .all()
        )

        past_events = [
            {
                "id": e[0],
                "date": e[1],
                "name": e[2] or "",
                "description": e[3] or "",
                "event_type": e[4] or "sabc_tournament",
                "entry_fee": e[5],
                "lake_name": e[6],
                "start_time": e[7],
                "weigh_in_time": e[8],
                "holiday_name": e[9],
                "has_poll": bool(e[10]),
                "has_tournament": bool(e[11]),
                "tournament_complete": bool(e[12]),
                "has_results": bool(e[13]),
            }
            for e in past_events_query
        ]

    return past_events, total
