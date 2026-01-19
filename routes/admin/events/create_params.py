"""Parameter preparation for event creation."""

from datetime import datetime
from typing import Any, Dict


def prepare_create_event_params(
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
    """Prepare parameters for event and tournament creation."""
    date_obj = datetime.strptime(date, "%Y-%m-%d")
    year = date_obj.year

    # Handle times based on event type:
    # - Tournaments: only store if actually provided (times show as TBD until set)
    # - Other event types: no times
    effective_start_time: str | None = None
    effective_weigh_in_time: str | None = None

    if event_type in ("sabc_tournament", "other_tournament"):
        # Times are optional - leave as None until set via poll or manual edit
        effective_start_time = start_time if start_time else None
        effective_weigh_in_time = weigh_in_time if weigh_in_time else None

    event_params = {
        "date": date,
        "year": year,
        "name": name,
        "event_type": event_type,
        "description": description,
        "start_time": effective_start_time,
        "weigh_in_time": effective_weigh_in_time,
        "lake_name": lake_name if lake_name else None,
        "ramp_name": ramp_name if ramp_name else None,
        "entry_fee": entry_fee if event_type == "sabc_tournament" else 0.00,
        "fish_limit": fish_limit if event_type == "sabc_tournament" else None,
        "holiday_name": name if event_type == "holiday" else None,
    }

    tournament_params = {
        "name": name,
        "lake_name": lake_name if lake_name else None,
        "ramp_name": ramp_name if ramp_name else None,
        "start_time": effective_start_time,
        "end_time": effective_weigh_in_time,
        "fish_limit": fish_limit,
        "entry_fee": entry_fee,
        "aoy_points": aoy_points.lower() == "true",
    }

    return event_params, tournament_params
