from typing import Any, Dict, List

from sqlalchemy import Date, cast, exists, func, select

from core.db_schema import Event, Poll, Result, Tournament, get_session


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
                exists(select(1).where(Poll.event_id == Event.id)).label("has_poll"),
                exists(select(1).where(Tournament.event_id == Event.id)).label("has_tournament"),
                exists(
                    select(1).where((Poll.event_id == Event.id) & (Poll.closed.is_(False)))
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
                exists(select(1).where(Poll.event_id == Event.id)).label("has_poll"),
                exists(select(1).where(Tournament.event_id == Event.id)).label("has_tournament"),
                func.coalesce(Tournament.complete, False).label("tournament_complete"),
                exists(select(1).where(Result.tournament_id == Tournament.id)).label("has_results"),
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
