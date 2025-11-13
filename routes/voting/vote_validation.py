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

    # Validate time format and order
    try:
        from datetime import datetime

        start_time = datetime.strptime(vote_data["start_time"], "%H:%M")
        end_time = datetime.strptime(vote_data["end_time"], "%H:%M")

        if end_time <= start_time:
            return None, "End time must be after start time"

        # Validate reasonable tournament hours (4 AM to 11 PM)
        if start_time.hour < 4 or end_time.hour > 23:
            return None, "Tournament times must be between 4:00 AM and 11:00 PM"

    except ValueError:
        return None, "Invalid time format. Use HH:MM"

    lake_id_int = int(vote_data["lake_id"])
    if not validate_lake_ramp_combo(lake_id_int, vote_data["ramp_id"]):
        return None, "Invalid vote data"
    lake_name = find_lake_by_id(lake_id_int, "name")
    ramp_name = find_ramp_name_by_id(vote_data["ramp_id"])
    if not lake_name or not ramp_name:
        return None, "Lake or ramp not found"
    option_text = f"{lake_name} - {ramp_name} ({time_format_filter(vote_data['start_time'])} to {time_format_filter(vote_data['end_time'])})"
    return option_text, None


def get_or_create_option_id(poll_id: int, option_text: str, vote_data: dict, session=None) -> Optional[int]:
    """Get or create a poll option, handling race conditions with database constraint.

    Uses ON CONFLICT DO NOTHING to handle concurrent creation attempts safely.
    The unique constraint uq_poll_option_text (poll_id, option_text) prevents duplicates.

    Args:
        poll_id: The poll ID
        option_text: The option text
        vote_data: The vote data dict
        session: Existing SQLAlchemy session (if None, creates new session)
    """
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError

    def _execute(sess):
        """Inner function to execute the query with provided session."""
        try:
            # Try to insert new option using ON CONFLICT to handle race condition
            vote_data["lake_id"] = int(vote_data["lake_id"])
            vote_data_json = json.dumps(vote_data)
            result = sess.execute(
                text("""
                    INSERT INTO poll_options (poll_id, option_text, option_data)
                    VALUES (:poll_id, :option_text, CAST(:option_data AS jsonb))
                    ON CONFLICT (poll_id, option_text) DO NOTHING
                    RETURNING id
                """),
                {
                    "poll_id": poll_id,
                    "option_text": option_text,
                    "option_data": vote_data_json,
                },
            )
            sess.flush()

            # If INSERT succeeded, we get the ID back
            row = result.fetchone()
            if row:
                return row[0]

            # If INSERT was skipped due to conflict, fetch existing option
            existing_option = (
                sess.query(PollOption)
                .filter(PollOption.poll_id == poll_id)
                .filter(PollOption.option_text == option_text)
                .first()
            )
            return existing_option.id if existing_option else None

        except IntegrityError:
            # In case of any integrity error, try to fetch existing option
            sess.rollback()
            existing_option = (
                sess.query(PollOption)
                .filter(PollOption.poll_id == poll_id)
                .filter(PollOption.option_text == option_text)
                .first()
            )
            return existing_option.id if existing_option else None

    # Use provided session or create a new one
    if session is not None:
        return _execute(session)
    else:
        with get_session() as new_session:
            return _execute(new_session)
