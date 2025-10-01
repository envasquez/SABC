"""Route dependencies and helper functions."""

import bcrypt

from core.database import db
from core.db_schema import engine
from core.deps import templates, time_format_filter
from core.helpers.auth import admin, u
from routes.dependencies.angler_helpers import get_admin_anglers_list
from routes.dependencies.event_helpers import get_admin_events_data, validate_event_data
from routes.dependencies.holidays import get_federal_holidays
from routes.dependencies.lake_helpers import (
    find_lake_by_id,
    find_ramp_name_by_id,
    get_all_ramps,
    get_lakes_list,
    get_ramps_for_lake,
    validate_lake_ramp_combo,
)

__all__ = [
    "admin",
    "u",
    "db",
    "templates",
    "engine",
    "bcrypt",
    "find_lake_by_id",
    "find_ramp_name_by_id",
    "get_all_ramps",
    "get_lakes_list",
    "get_ramps_for_lake",
    "validate_lake_ramp_combo",
    "get_admin_anglers_list",
    "get_federal_holidays",
    "validate_event_data",
    "get_admin_events_data",
    "time_format_filter",
]
