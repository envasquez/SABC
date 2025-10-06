import json
from datetime import datetime, timedelta
from typing import Any, Dict

from sqlalchemy import or_

from core.db_schema import Event, Lake, Poll, PollOption, Ramp, Tournament, get_session


def create_event_record(event_params: Dict[str, Any]) -> int:
    event_params_filtered = {k: v for k, v in event_params.items() if k != "fish_limit"}

    with get_session() as session:
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
        session.add(event)
        session.flush()
        event_id = event.id

    return event_id


def create_tournament_record(event_id: int, tournament_params: Dict[str, Any]) -> None:
    with get_session() as session:
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
        session.add(tournament)


def create_tournament_poll(
    event_id: int, name: str, description: str, date_obj: datetime, user_id: int
) -> int:
    poll_starts = date_obj - timedelta(days=7)
    poll_closes = date_obj - timedelta(days=5)

    with get_session() as session:
        poll = Poll(
            title=name,
            description=description if description else f"Vote for location for {name}",
            event_id=event_id,
            created_by=user_id,
            starts_at=poll_starts,
            closes_at=poll_closes,
            poll_type="tournament_location",
        )
        session.add(poll)
        session.flush()
        poll_id = poll.id

    return poll_id


def create_poll_options(poll_id: int) -> None:
    with get_session() as session:
        all_lakes = session.query(Lake).order_by(Lake.display_name).all()

        for lake in all_lakes:
            option_data = {"lake_id": lake.id}
            poll_option = PollOption(
                poll_id=poll_id,
                option_text=lake.display_name,
                option_data=json.dumps(option_data),
            )
            session.add(poll_option)
