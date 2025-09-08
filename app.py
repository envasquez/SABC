import os
import json
import bcrypt
import uvicorn
from typing import Optional
from datetime import date, datetime, timedelta
from fastapi import *
from fastapi.responses import *
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import text

from core.database import db
from core.filters import (
    date_format_filter,
    from_json_filter,
    month_number_filter,
    time_format_filter,
)
from core.auth_helpers import u, admin
from core.lakes import (
    load_lakes_data, get_lakes_list, get_ramps_for_lake, get_all_ramps,
    find_lake_by_id, find_ramp_name_by_id, validate_lake_ramp_combo, find_lake_data_by_db_name
)
from core.validators import validate_event_data, get_federal_holidays

app = FastAPI(redirect_slashes=False)
app.add_middleware(
    SessionMiddleware, secret_key=os.environ.get("SECRET_KEY", "dev-key-change-in-production")
)
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")
templates.env.filters["from_json"] = from_json_filter
templates.env.filters["date_format"] = date_format_filter
templates.env.filters["time_format"] = time_format_filter
templates.env.filters["date_format_dd_mm_yyyy"] = lambda d: date_format_filter(d, "dd-mm-yyyy")
templates.env.filters["month_number"] = month_number_filter

exec(open("app_routes.py").read())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
