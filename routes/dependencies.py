from typing import Any, Dict, List, Optional

import bcrypt

from core.database import db
from core.db_schema import engine
from core.deps import templates
from core.filters import time_format_filter
from core.helpers.auth import admin, u
from core.query_service import QueryService


def find_lake_by_id(lake_id: int, field: str = "name") -> Optional[str]:
    with engine.connect() as conn:
        qs = QueryService(conn)
        lake = qs.get_lake_by_id(lake_id)
        if not lake:
            return None
        return lake.get(field, lake["name"]) if field != "name" else lake["name"]


def find_lake_data_by_db_name(name: str) -> Optional[Dict[str, Any]]:
    with engine.connect() as conn:
        qs = QueryService(conn)
        return qs.fetch_one("SELECT * FROM lakes WHERE display_name = :name", {"name": name})


def find_ramp_name_by_id(ramp_id: int) -> Optional[str]:
    with engine.connect() as conn:
        qs = QueryService(conn)
        ramp = qs.get_ramp_by_id(ramp_id)
        return ramp["name"] if ramp else None


def get_all_ramps() -> List[Dict[str, Any]]:
    with engine.connect() as conn:
        qs = QueryService(conn)
        return qs.fetch_all("SELECT * FROM ramps ORDER BY name")


def get_lakes_list() -> List[Dict[str, Any]]:
    with engine.connect() as conn:
        qs = QueryService(conn)
        return qs.get_lakes_list()


def get_ramps_for_lake(lake_id: int) -> List[Dict[str, Any]]:
    with engine.connect() as conn:
        qs = QueryService(conn)
        return qs.get_ramps_for_lake(lake_id)


def validate_lake_ramp_combo(lake_id, ramp_id):
    with engine.connect() as conn:
        qs = QueryService(conn)
        return qs.validate_lake_ramp_combo(lake_id, ramp_id)


def get_admin_anglers_list():
    with engine.connect() as conn:
        qs = QueryService(conn)
        return qs.get_admin_anglers_list()


def get_admin_events_data(upcoming_page: int = 1, past_page: int = 1, per_page: int = 20):
    upcoming_offset = (upcoming_page - 1) * per_page
    past_offset = (past_page - 1) * per_page
    with engine.connect() as conn:
        qs = QueryService(conn)
        return qs.get_admin_events_data(per_page, upcoming_offset, per_page, past_offset)


from core.validators import get_federal_holidays, validate_event_data  # noqa

__all__ = [
    "admin",
    "u",
    "db",
    "templates",
    "engine",
    "bcrypt",
    "find_lake_by_id",
    "find_lake_data_by_db_name",
    "find_ramp_name_by_id",
    "get_all_ramps",
    "get_lakes_list",
    "get_ramps_for_lake",
    "validate_lake_ramp_combo",
    "get_federal_holidays",
    "validate_event_data",
    "time_format_filter",
]
