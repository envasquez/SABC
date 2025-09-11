"""Shared dependencies for all route modules."""

# Re-export everything needed by route modules
from typing import Optional

import bcrypt
from fastapi.templating import Jinja2Templates

from core.auth_helpers import admin, u
from core.database import db
from core.database_engine import engine
from core.filters import time_format_filter
from core.db_helpers import (
    find_lake_by_id,
    find_lake_data_by_db_name,
    find_ramp_name_by_id,
    get_all_ramps,
    get_lakes_list,
    get_ramps_for_lake,
    load_lakes_data,
    validate_lake_ramp_combo,
)
from core.validators import get_federal_holidays, validate_event_data

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
    "load_lakes_data",
    "validate_lake_ramp_combo",
    "get_federal_holidays",
    "validate_event_data",
    "time_format_filter",
]
templates: Optional[Jinja2Templates] = None
