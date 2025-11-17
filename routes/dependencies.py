"""Route dependencies - compatibility layer.

This module provides backwards compatibility by re-exporting
all dependencies from the routes.dependencies package.
"""

from routes.dependencies import (
    admin,
    bcrypt,
    db,
    engine,
    find_lake_by_id,
    find_ramp_name_by_id,
    get_admin_anglers_list,
    get_admin_events_data,
    get_all_ramps,
    get_current_user,
    get_federal_holidays,
    get_lakes_list,
    get_ramps_for_lake,
    templates,
    time_format_filter,
    validate_event_data,
    validate_lake_ramp_combo,
)

__all__ = [
    "admin",
    "get_current_user",
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
