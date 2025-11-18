import json
from typing import Any, Dict, Union

from starlette.datastructures import FormData

from core.db_schema import PollOption, get_session
from routes.dependencies import find_lake_by_id, get_lakes_list


def create_tournament_location_options(
    poll_id: int, form: Union[FormData, Dict[str, Any]], event: tuple
) -> None:
    with get_session() as session:
        # Handle both FormData and dict
        if isinstance(form, FormData):
            selected_lake_ids = form.getlist("lake_ids")
        else:
            selected_lake_ids = form.get("lake_ids", [])
        if selected_lake_ids:
            for lake_id_raw in selected_lake_ids:
                if isinstance(lake_id_raw, str):
                    lake_name = find_lake_by_id(int(lake_id_raw), "name")
                    if lake_name:
                        new_option = PollOption(
                            poll_id=poll_id,
                            option_text=lake_name,
                            option_data=json.dumps({"lake_id": int(lake_id_raw)}),
                        )
                        session.add(new_option)
        else:
            all_lakes = get_lakes_list()
            for lake in all_lakes:
                new_option = PollOption(
                    poll_id=poll_id,
                    option_text=lake["display_name"],
                    option_data=json.dumps({"lake_id": lake["id"]}),
                )
                session.add(new_option)


def create_generic_poll_options(poll_id: int, form: Union[FormData, Dict[str, Any]]) -> None:
    # Handle both FormData and dict
    if isinstance(form, FormData):
        poll_options = form.getlist("poll_options[]")
    else:
        poll_options = form.get("poll_options[]", [])

    # Validate that at least one option is provided
    valid_options = [
        opt for opt in poll_options if isinstance(opt, str) and opt.strip()
    ]
    if not valid_options:
        raise ValueError("At least one poll option is required")

    with get_session() as session:
        for option_text_raw in valid_options:
            new_option = PollOption(
                poll_id=poll_id,
                option_text=option_text_raw.strip(),
                option_data=json.dumps({}),
            )
            session.add(new_option)


def create_other_poll_options(poll_id: int, form: Union[FormData, Dict[str, Any]]) -> None:
    with get_session() as session:
        for key in form.keys():
            value = form[key]
            if key.startswith("option_") and isinstance(value, str) and value.strip():
                new_option = PollOption(
                    poll_id=poll_id,
                    option_text=value.strip(),
                    option_data=json.dumps({}),
                )
                session.add(new_option)
