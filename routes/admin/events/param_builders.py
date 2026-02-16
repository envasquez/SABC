"""Shared parameter builders for event create/update operations."""

from datetime import datetime
from typing import Any, Dict, Optional


def prepare_event_params(
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
    event_id: Optional[int] = None,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Prepare parameters for event and tournament create/update.

    Args:
        event_id: If provided, included in params (for updates). Omit for creates.
    """
    date_obj = datetime.strptime(date, "%Y-%m-%d")
    year = date_obj.year

    # Times only apply to tournaments
    is_tournament = event_type in ("sabc_tournament", "other_tournament")
    effective_start_time = start_time if start_time and is_tournament else None
    effective_weigh_in_time = weigh_in_time if weigh_in_time and is_tournament else None

    event_params: Dict[str, Any] = {
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

    tournament_params: Dict[str, Any] = {
        "name": name,
        "lake_name": lake_name if lake_name else None,
        "ramp_name": ramp_name if ramp_name else None,
        "start_time": effective_start_time,
        "end_time": effective_weigh_in_time,
        "fish_limit": fish_limit,
        "entry_fee": entry_fee,
        "aoy_points": aoy_points.lower() == "true",
    }

    # Include event_id for update operations
    if event_id is not None:
        event_params["event_id"] = event_id
        tournament_params["event_id"] = event_id

    return event_params, tournament_params
