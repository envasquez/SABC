from datetime import datetime
from typing import Any, Dict

from sqlalchemy.orm import Session

from core.db_schema import Event, Poll, Tournament, get_session
from core.helpers.logging import get_logger
from core.helpers.timezone import make_aware

logger = get_logger(__name__)


def prepare_event_params(
    event_id: int,
    date: str,
    name: str,
    event_type: str,
    description: str,
    start_time: str,
    weigh_in_time: str,
    lake_name: str,
    ramp_name: str,
    entry_fee: float,
    fish_limit: int,
    aoy_points: str = "true",
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    date_obj = datetime.strptime(date, "%Y-%m-%d")
    year = date_obj.year
    event_params = {
        "event_id": event_id,
        "date": date,
        "year": year,
        "name": name,
        "event_type": event_type,
        "description": description,
        "start_time": start_time if event_type in ["sabc_tournament", "other_tournament"] else None,
        "weigh_in_time": weigh_in_time
        if event_type in ["sabc_tournament", "other_tournament"]
        else None,
        "lake_name": lake_name if lake_name else None,
        "ramp_name": ramp_name if ramp_name else None,
        "entry_fee": entry_fee if event_type == "sabc_tournament" else 0.00,
        "holiday_name": name if event_type == "holiday" else None,
    }
    tournament_params = {
        "event_id": event_id,
        "name": name,
        "lake_name": lake_name if lake_name else None,
        "ramp_name": ramp_name if ramp_name else None,
        "start_time": start_time,
        "end_time": weigh_in_time,
        "fish_limit": fish_limit,
        "entry_fee": entry_fee,
        "aoy_points": aoy_points.lower() == "true",
    }
    return event_params, tournament_params


def update_event_record(session: Session, event_params: Dict[str, Any]) -> int:
    event = session.query(Event).filter(Event.id == event_params["event_id"]).first()
    if event:
        event.date = datetime.strptime(event_params["date"], "%Y-%m-%d").date()
        event.year = event_params["year"]
        event.name = event_params["name"]
        event.event_type = event_params["event_type"]
        event.description = event_params["description"]
        event.start_time = (
            datetime.strptime(event_params["start_time"], "%H:%M").time()
            if event_params["start_time"]
            else None
        )
        event.weigh_in_time = (
            datetime.strptime(event_params["weigh_in_time"], "%H:%M").time()
            if event_params["weigh_in_time"]
            else None
        )
        event.lake_name = event_params["lake_name"]
        event.ramp_name = event_params["ramp_name"]
        event.entry_fee = event_params["entry_fee"]
        event.holiday_name = event_params["holiday_name"]
        # Update is_cancelled if provided
        if "is_cancelled" in event_params:
            event.is_cancelled = event_params["is_cancelled"]
        return 1
    return 0


def update_tournament_record(session: Session, tournament_params: Dict[str, Any]) -> int:
    from sqlalchemy import or_

    from core.db_schema import Lake, Ramp

    tournament = (
        session.query(Tournament)
        .filter(Tournament.event_id == tournament_params["event_id"])
        .first()
    )
    if tournament:
        # Look up lake_id and ramp_id from lake_name and ramp_name
        lake_id = None
        ramp_id = None

        if tournament_params.get("lake_name"):
            lake = (
                session.query(Lake)
                .filter(
                    or_(
                        Lake.yaml_key == tournament_params["lake_name"],
                        Lake.display_name == tournament_params["lake_name"],
                    )
                )
                .first()
            )
            if lake:
                lake_id = lake.id

        if tournament_params.get("ramp_name") and lake_id:
            ramp = (
                session.query(Ramp)
                .filter(Ramp.name == tournament_params["ramp_name"], Ramp.lake_id == lake_id)
                .first()
            )
            if ramp:
                ramp_id = ramp.id

        tournament.name = tournament_params["name"]
        tournament.lake_id = lake_id
        tournament.ramp_id = ramp_id
        tournament.lake_name = tournament_params["lake_name"]
        tournament.ramp_name = tournament_params["ramp_name"]
        tournament.start_time = (
            datetime.strptime(tournament_params["start_time"], "%H:%M").time()
            if tournament_params["start_time"]
            else None
        )
        tournament.end_time = (
            datetime.strptime(tournament_params["end_time"], "%H:%M").time()
            if tournament_params["end_time"]
            else None
        )
        tournament.fish_limit = tournament_params["fish_limit"]
        tournament.entry_fee = tournament_params["entry_fee"]
        tournament.aoy_points = tournament_params["aoy_points"]
        return 1
    return 0


def update_poll_closing_date(event_id: int, poll_closes_date: str) -> None:
    if not poll_closes_date:
        return
    try:
        # Interpret form datetime as Central Time (club timezone)
        closes_dt = make_aware(datetime.fromisoformat(poll_closes_date))
        with get_session() as session:
            poll = session.query(Poll).filter(Poll.event_id == event_id).first()
            if poll:
                poll.closes_at = closes_dt
    except ValueError as e:
        logger.warning(
            f"Invalid poll_closes_date format for event {event_id}: '{poll_closes_date}'. "
            f"Expected ISO format (YYYY-MM-DD HH:MM:SS). Error: {e}. "
            f"Poll closing date not updated."
        )


def update_tournament_poll_id(event_id: int, poll_id: int | None) -> None:
    """Update the poll_id on a tournament and the event_id on the poll.

    This creates a bidirectional link:
    - Tournament.poll_id -> Poll
    - Poll.event_id -> Event

    Args:
        event_id: Event ID to find the tournament
        poll_id: Poll ID to associate (or None to clear)
    """
    with get_session() as session:
        tournament = session.query(Tournament).filter(Tournament.event_id == event_id).first()
        if tournament:
            tournament.poll_id = poll_id
            logger.info(f"Updated tournament poll_id to {poll_id} for event {event_id}")

        # Also update the poll's event_id to enable seasonal history
        if poll_id:
            poll = session.query(Poll).filter(Poll.id == poll_id).first()
            if poll:
                poll.event_id = event_id
                logger.info(f"Updated poll {poll_id} event_id to {event_id}")
