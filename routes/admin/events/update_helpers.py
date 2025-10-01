from datetime import datetime
from typing import Any, Dict

from sqlalchemy import Connection, text

from routes.dependencies import db


def prepare_event_params(
    event_id: int,
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
    date_obj = datetime.strptime(date, "%Y-%m-%d")
    year = date_obj.year
    event_params = {
        "event_id": event_id,
        "date": date,
        "year": year,
        "name": name,
        "event_type": event_type,
        "description": description,
        "start_time": start_time if event_type in ["sabc_tournament", "other_tournament"] else None,
        "weigh_in_time": weigh_in_time
        if event_type in ["sabc_tournament", "other_tournament"]
        else None,
        "lake_name": lake_name if lake_name else None,
        "ramp_name": ramp_name if ramp_name else None,
        "entry_fee": entry_fee if event_type == "sabc_tournament" else 0.00,
        "holiday_name": name if event_type == "holiday" else None,
    }
    tournament_params = {
        "event_id": event_id,
        "name": name,
        "lake_name": lake_name if lake_name else None,
        "ramp_name": ramp_name if ramp_name else None,
        "start_time": start_time,
        "end_time": weigh_in_time,
        "fish_limit": fish_limit,
        "entry_fee": entry_fee,
        "aoy_points": aoy_points.lower() == "true",
    }
    return event_params, tournament_params


def update_event_record(conn: Connection, event_params: Dict[str, Any]) -> int:
    result = conn.execute(
        text("""UPDATE events SET date = :date, year = :year, name = :name,
                event_type = :event_type, description = :description, start_time = :start_time,
                weigh_in_time = :weigh_in_time, lake_name = :lake_name, ramp_name = :ramp_name,
                entry_fee = :entry_fee, holiday_name = :holiday_name WHERE id = :event_id"""),
        event_params,
    )
    conn.commit()
    return result.rowcount


def update_tournament_record(conn: Connection, tournament_params: Dict[str, Any]) -> int:
    result = conn.execute(
        text("""UPDATE tournaments SET name = :name, lake_name = :lake_name,
                ramp_name = :ramp_name, start_time = :start_time, end_time = :end_time,
                fish_limit = :fish_limit, entry_fee = :entry_fee, aoy_points = :aoy_points
                WHERE event_id = :event_id"""),
        tournament_params,
    )
    conn.commit()
    return result.rowcount


def update_poll_closing_date(event_id: int, poll_closes_date: str) -> None:
    if not poll_closes_date:
        return
    try:
        closes_dt = datetime.fromisoformat(poll_closes_date)
        db(
            "UPDATE polls SET closes_at = :closes_at WHERE event_id = :event_id",
            {"closes_at": closes_dt.isoformat(), "event_id": event_id},
        )
    except ValueError:
        pass
