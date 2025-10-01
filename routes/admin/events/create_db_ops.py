import json
from datetime import datetime, timedelta
from typing import Any, Dict, List

from routes.dependencies import db, get_lakes_list


def create_event_record(event_params: Dict[str, Any]) -> int:
    event_params_filtered = {k: v for k, v in event_params.items() if k != "fish_limit"}
    result = db(
        """INSERT INTO events (date, year, name, event_type, description, start_time,
           weigh_in_time, lake_name, ramp_name, entry_fee, holiday_name)
           VALUES (:date, :year, :name, :event_type, :description, :start_time,
                   :weigh_in_time, :lake_name, :ramp_name, :entry_fee, :holiday_name)
           RETURNING id""",
        event_params_filtered,
    )
    if result:
        return result[0][0] if isinstance(result, list) else result

    raise ValueError("Failed to create event")


def create_tournament_record(event_id: int, tournament_params: Dict[str, Any]) -> None:
    tournament_params["event_id"] = event_id
    lake_id = None
    ramp_id = None
    if tournament_params.get("lake_name"):
        lake_result = db(
            "SELECT id FROM lakes WHERE yaml_key = :lake_name OR display_name = :lake_name",
            {"lake_name": tournament_params["lake_name"]},
        )
        if lake_result:
            lake_id = lake_result[0][0]
    if tournament_params.get("ramp_name") and lake_id:
        ramp_result = db(
            "SELECT id FROM ramps WHERE name = :ramp_name AND lake_id = :lake_id",
            {"ramp_name": tournament_params["ramp_name"], "lake_id": lake_id},
        )
        if ramp_result:
            ramp_id = ramp_result[0][0]
    tournament_params["lake_id"] = lake_id
    tournament_params["ramp_id"] = ramp_id
    db(
        """INSERT INTO tournaments (event_id, name, lake_id, ramp_id, lake_name, ramp_name,
           start_time, end_time, fish_limit, entry_fee, aoy_points)
           VALUES (:event_id, :name, :lake_id, :ramp_id, :lake_name, :ramp_name,
                   :start_time, :end_time, :fish_limit, :entry_fee, :aoy_points)""",
        tournament_params,
    )


def create_tournament_poll(
    event_id: int, name: str, description: str, date_obj: datetime, user_id: int
) -> int:
    poll_starts = (date_obj - timedelta(days=7)).isoformat()
    poll_closes = (date_obj - timedelta(days=5)).isoformat()
    poll_id = db(
        """INSERT INTO polls (title, description, event_id, created_by, starts_at, closes_at, poll_type)
           VALUES (:title, :description, :event_id, :created_by, :starts_at, :closes_at, 'tournament_location')
           RETURNING id""",
        {
            "title": name,
            "description": description if description else f"Vote for location for {name}",
            "event_id": event_id,
            "created_by": user_id,
            "starts_at": poll_starts,
            "closes_at": poll_closes,
        },
    )
    if isinstance(poll_id, list):
        poll_id = poll_id[0][0]
    return poll_id


def create_poll_options(poll_id: int) -> None:
    all_lakes: List[Dict[str, Any]] = get_lakes_list()
    for lake in all_lakes:
        option_data = {"lake_id": lake["id"]}
        db(
            """INSERT INTO poll_options (poll_id, option_text, option_data)
               VALUES (:poll_id, :option_text, :option_data)""",
            {
                "poll_id": poll_id,
                "option_text": lake["display_name"],
                "option_data": json.dumps(option_data),
            },
        )
