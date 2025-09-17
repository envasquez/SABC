import bcrypt

from core.database import db
from core.db_schema import engine
from core.deps import templates
from core.filters import time_format_filter
from core.helpers.auth import admin, u
from core.query_service import QueryService


def find_lake_by_id(lake_id, field="name"):
    with engine.connect() as conn:
        qs = QueryService(conn)
        lake = qs.get_lake_by_id(lake_id)
        if not lake:
            return None
        return lake.get(field, lake["name"]) if field != "name" else lake["name"]


def find_lake_data_by_db_name(name):
    with engine.connect() as conn:
        qs = QueryService(conn)
        return qs.fetch_one("SELECT * FROM lakes WHERE name = :name", {"name": name})


def find_ramp_name_by_id(ramp_id):
    with engine.connect() as conn:
        qs = QueryService(conn)
        ramp = qs.get_ramp_by_id(ramp_id)
        return ramp["name"] if ramp else None


def get_all_ramps():
    with engine.connect() as conn:
        qs = QueryService(conn)
        return qs.fetch_all("SELECT * FROM ramps ORDER BY name")


def get_lakes_list():
    with engine.connect() as conn:
        qs = QueryService(conn)
        return qs.get_lakes_list()


def get_ramps_for_lake(lake_id):
    with engine.connect() as conn:
        qs = QueryService(conn)
        return qs.get_ramps_for_lake(lake_id)


def validate_lake_ramp_combo(lake_id, ramp_id):
    with engine.connect() as conn:
        qs = QueryService(conn)
        return qs.validate_lake_ramp_combo(lake_id, ramp_id)


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
