"""Shared dependencies for all route modules."""

import json
from datetime import datetime

import bcrypt
from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import text

from core.auth_helpers import admin, u
from core.database import db
from core.lakes import (
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
from database import engine

# Templates instance
templates = Jinja2Templates(directory="templates")
