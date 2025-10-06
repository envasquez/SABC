import json
from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlalchemy import exists, select

from core.db_schema import Poll, PollOption, PollVote, get_session
from routes.dependencies import (
    find_lake_by_id,
    find_ramp_name_by_id,
    time_format_filter,
    validate_lake_ramp_combo,
)


def validate_poll_state(poll_id: int, user_id: int) -> Optional[str]:
    with get_session() as session:
        # Check if user already voted
        already_voted = session.query(
            exists(
                select(1).where(PollVote.poll_id == poll_id).where(PollVote.angler_id == user_id)
            )
        ).scalar()

        # Get poll details
        poll = session.query(Poll).filter(Poll.id == poll_id).first()

        if not poll:
            return "Poll not found"

        if already_voted or poll.closed:
            return "Poll not found, already voted, or closed"

        # Use timezone-aware datetime comparison to avoid timing attacks
        now = datetime.now(timezone.utc)
        poll_start = poll.starts_at
        poll_end = poll.closes_at

        # Make naive datetimes timezone-aware if needed
        if poll_start.tzinfo is None:
            poll_start = poll_start.replace(tzinfo=timezone.utc)
        if poll_end.tzinfo is None:
            poll_end = poll_end.replace(tzinfo=timezone.utc)

        if not (poll_start <= now <= poll_end):
            return "Poll not accepting votes"

        return None


def validate_tournament_location_vote(vote_data: dict) -> Tuple[Optional[str], Optional[str]]:
    required_fields = ["lake_id", "ramp_id", "start_time", "end_time"]
    if not all(f in vote_data for f in required_fields):
        return None, "Invalid vote data"
    lake_id_int = int(vote_data["lake_id"])
    if not validate_lake_ramp_combo(lake_id_int, vote_data["ramp_id"]):
        return None, "Invalid vote data"
    lake_name = find_lake_by_id(lake_id_int, "name")
    ramp_name = find_ramp_name_by_id(vote_data["ramp_id"])
    if not lake_name or not ramp_name:
        return None, "Lake or ramp not found"
    option_text = f"{lake_name} - {ramp_name} ({time_format_filter(vote_data['start_time'])} to {time_format_filter(vote_data['end_time'])})"
    return option_text, None


def get_or_create_option_id(poll_id: int, option_text: str, vote_data: dict) -> Optional[int]:
    with get_session() as session:
        # Check for existing option
        existing_option = (
            session.query(PollOption)
            .filter(PollOption.poll_id == poll_id)
            .filter(PollOption.option_text == option_text)
            .first()
        )

        if existing_option:
            return existing_option.id

        # Create new option
        vote_data["lake_id"] = int(vote_data["lake_id"])
        new_option = PollOption(
            poll_id=poll_id,
            option_text=option_text,
            option_data=json.dumps(vote_data),
        )
        session.add(new_option)
        session.flush()  # Flush to get the ID
        return new_option.id
