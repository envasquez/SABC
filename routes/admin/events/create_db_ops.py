import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from core.db_schema import Event, Lake, Poll, PollOption, Ramp, Tournament, get_session


def create_event_record(event_params: Dict[str, Any], session: Optional[Session] = None) -> int:
    """Create event record within an existing session or create a new one.

    Args:
        event_params: Event parameters dictionary
        session: Optional existing session. If None, creates and manages its own session.

    Returns:
        int: Created event ID
    """
    event_params_filtered = {k: v for k, v in event_params.items() if k != "fish_limit"}

    def _create(sess: Session) -> int:
        event = Event(
            date=datetime.strptime(event_params_filtered["date"], "%Y-%m-%d").date(),
            year=event_params_filtered["year"],
            name=event_params_filtered["name"],
            event_type=event_params_filtered["event_type"],
            description=event_params_filtered["description"],
            start_time=(
                datetime.strptime(event_params_filtered["start_time"], "%H:%M").time()
                if event_params_filtered["start_time"]
                else None
            ),
            weigh_in_time=(
                datetime.strptime(event_params_filtered["weigh_in_time"], "%H:%M").time()
                if event_params_filtered["weigh_in_time"]
                else None
            ),
            lake_name=event_params_filtered["lake_name"],
            ramp_name=event_params_filtered["ramp_name"],
            entry_fee=event_params_filtered["entry_fee"],
            holiday_name=event_params_filtered["holiday_name"],
        )
        sess.add(event)
        sess.flush()
        return event.id

    if session is not None:
        # Use provided session (caller manages commit)
        return _create(session)
    else:
        # Create and manage own session
        with get_session() as sess:
            event_id = _create(sess)
            # Context manager will commit
        return event_id


def create_tournament_record(
    event_id: int, tournament_params: Dict[str, Any], session: Optional[Session] = None
) -> None:
    """Create tournament record within an existing session or create a new one.

    Args:
        event_id: Event ID to link tournament to
        tournament_params: Tournament parameters dictionary
        session: Optional existing session. If None, creates and manages its own session.
    """

    def _create(sess: Session) -> None:
        lake_id = None
        ramp_id = None

        if tournament_params.get("lake_name"):
            lake = (
                sess.query(Lake)
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
                sess.query(Ramp)
                .filter(Ramp.name == tournament_params["ramp_name"], Ramp.lake_id == lake_id)
                .first()
            )
            if ramp:
                ramp_id = ramp.id

        tournament = Tournament(
            event_id=event_id,
            name=tournament_params["name"],
            lake_id=lake_id,
            ramp_id=ramp_id,
            lake_name=tournament_params["lake_name"],
            ramp_name=tournament_params["ramp_name"],
            start_time=(
                datetime.strptime(tournament_params["start_time"], "%H:%M").time()
                if tournament_params["start_time"]
                else None
            ),
            end_time=(
                datetime.strptime(tournament_params["end_time"], "%H:%M").time()
                if tournament_params["end_time"]
                else None
            ),
            fish_limit=tournament_params["fish_limit"],
            entry_fee=tournament_params["entry_fee"],
            aoy_points=tournament_params["aoy_points"],
        )
        sess.add(tournament)

    if session is not None:
        # Use provided session (caller manages commit)
        _create(session)
    else:
        # Create and manage own session
        with get_session() as sess:
            _create(sess)
            # Context manager will commit


def create_tournament_poll(
    event_id: int,
    name: str,
    description: str,
    date_obj: datetime,
    user_id: int,
    session: Optional[Session] = None,
) -> int:
    """Create tournament poll within an existing session or create a new one.

    Args:
        event_id: Event ID to link poll to
        name: Poll title
        description: Poll description
        date_obj: Tournament date
        user_id: Creator user ID
        session: Optional existing session. If None, creates and manages its own session.

    Returns:
        int: Created poll ID
    """
    poll_starts = date_obj - timedelta(days=7)
    poll_closes = date_obj - timedelta(days=5)

    def _create(sess: Session) -> int:
        poll = Poll(
            title=name,
            description=description if description else f"Vote for location for {name}",
            event_id=event_id,
            created_by=user_id,
            starts_at=poll_starts,
            closes_at=poll_closes,
            poll_type="tournament_location",
        )
        sess.add(poll)
        sess.flush()
        return poll.id

    if session is not None:
        # Use provided session (caller manages commit)
        return _create(session)
    else:
        # Create and manage own session
        with get_session() as sess:
            poll_id = _create(sess)
            # Context manager will commit
        return poll_id


def create_poll_options(poll_id: int, session: Optional[Session] = None) -> None:
    """Create poll options for all lakes within an existing session or create a new one.

    Args:
        poll_id: Poll ID to create options for
        session: Optional existing session. If None, creates and manages its own session.
    """

    def _create(sess: Session) -> None:
        all_lakes = sess.query(Lake).order_by(Lake.display_name).all()

        for lake in all_lakes:
            option_data = {"lake_id": lake.id}
            poll_option = PollOption(
                poll_id=poll_id,
                option_text=lake.display_name,
                option_data=json.dumps(option_data),
            )
            sess.add(poll_option)

    if session is not None:
        # Use provided session (caller manages commit)
        _create(session)
    else:
        # Create and manage own session
        with get_session() as sess:
            _create(sess)
            # Context manager will commit


def link_tournament_to_poll(event_id: int, poll_id: int) -> None:
    """Link a tournament to a poll by setting the tournament's poll_id.

    Args:
        event_id: Event ID to find the tournament
        poll_id: Poll ID to link to the tournament
    """
    with get_session() as session:
        tournament = session.query(Tournament).filter(Tournament.event_id == event_id).first()
        if tournament:
            tournament.poll_id = poll_id
