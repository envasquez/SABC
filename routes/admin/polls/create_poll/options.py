import json
from typing import Any, Dict

from routes.dependencies import db, find_lake_by_id, get_lakes_list


def create_tournament_location_options(poll_id: int, form: Dict[str, Any], event: tuple) -> None:
    selected_lake_ids = form.getlist("lake_ids")
    if selected_lake_ids:
        for lake_id_raw in selected_lake_ids:
            if isinstance(lake_id_raw, str):
                lake_name = find_lake_by_id(int(lake_id_raw), "name")
                if lake_name:
                    db(
                        "INSERT INTO poll_options (poll_id, option_text, option_data) VALUES (:poll_id, :option_text, :option_data)",
                        {
                            "poll_id": poll_id,
                            "option_text": lake_name,
                            "option_data": json.dumps({"lake_id": int(lake_id_raw)}),
                        },
                    )
    else:
        all_lakes = get_lakes_list()
        for lake in all_lakes:
            db(
                "INSERT INTO poll_options (poll_id, option_text, option_data) VALUES (:poll_id, :option_text, :option_data)",
                {
                    "poll_id": poll_id,
                    "option_text": lake["display_name"],
                    "option_data": json.dumps({"lake_id": lake["id"]}),
                },
            )


def create_generic_poll_options(poll_id: int, form: Dict[str, Any]) -> None:
    poll_options = form.getlist("poll_options[]")
    for option_text_raw in poll_options:
        if isinstance(option_text_raw, str) and option_text_raw.strip():
            db(
                "INSERT INTO poll_options (poll_id, option_text, option_data) VALUES (:poll_id, :option_text, :option_data)",
                {
                    "poll_id": poll_id,
                    "option_text": option_text_raw.strip(),
                    "option_data": json.dumps({}),
                },
            )


def create_other_poll_options(poll_id: int, form: Dict[str, Any]) -> None:
    for key in form.keys():
        value = form[key]
        if key.startswith("option_") and isinstance(value, str) and value.strip():
            db(
                "INSERT INTO poll_options (poll_id, option_text, option_data) VALUES (:poll_id, :option_text, :option_data)",
                {
                    "poll_id": poll_id,
                    "option_text": value.strip(),
                    "option_data": json.dumps({}),
                },
            )
