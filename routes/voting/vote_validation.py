import json
from datetime import datetime
from typing import Optional, Tuple

from routes.dependencies import (
    db,
    find_lake_by_id,
    find_ramp_name_by_id,
    time_format_filter,
    validate_lake_ramp_combo,
)


def validate_poll_state(poll_id: int, user_id: int) -> Optional[str]:
    poll_check = db(
        """SELECT p.id, p.closed, p.starts_at, p.closes_at,
           EXISTS(SELECT 1 FROM poll_votes pv WHERE pv.poll_id = p.id AND pv.angler_id = :user_id) as already_voted
           FROM polls p WHERE p.id = :poll_id""",
        {"poll_id": poll_id, "user_id": user_id},
    )

    if not poll_check or len(poll_check) == 0:
        return "Poll not found"

    poll_row = poll_check[0]
    already_voted = poll_row[4]
    is_closed = poll_row[1]
    starts_at = poll_row[2]
    closes_at = poll_row[3]
    if already_voted or is_closed:
        return "Poll not found, already voted, or closed"

    if not (
        datetime.fromisoformat(starts_at) <= datetime.now() <= datetime.fromisoformat(closes_at)
    ):
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
    existing_option = db(
        "SELECT id FROM poll_options WHERE poll_id = :poll_id AND option_text = :option_text",
        {"poll_id": poll_id, "option_text": option_text},
    )
    if existing_option:
        return existing_option[0][0]

    vote_data["lake_id"] = int(vote_data["lake_id"])
    db(
        "INSERT INTO poll_options (poll_id, option_text, option_data) VALUES (:poll_id, :option_text, :option_data)",
        {"poll_id": poll_id, "option_text": option_text, "option_data": json.dumps(vote_data)},
    )
    res = db("SELECT lastval()")
    return res[0][0] if res and len(res) > 0 else None
