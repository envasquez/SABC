import json
import logging
import os
from datetime import date, datetime, timedelta
from typing import Optional

import bcrypt
import uvicorn
from fastapi import FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from starlette.middleware.sessions import SessionMiddleware

import routes.dependencies as deps
from core.helpers.auth import admin, u
from core.database import db
from core.helpers.logging_config import configure_logging, get_logger
from core.filters import (
    date_format_filter,
    from_json_filter,
    month_number_filter,
    time_format_filter,
)
from core.helpers.queries import (
    find_lake_by_id,
    find_lake_data_by_db_name,
    find_ramp_name_by_id,
    get_all_ramps,
    get_lakes_list,
    get_ramps_for_lake,
    validate_lake_ramp_combo,
)
from core.validators import get_federal_holidays, validate_event_data

configure_logging(log_level=os.environ.get("LOG_LEVEL", "INFO"))
logger = get_logger(__name__)

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
deps.templates = templates

from routes import (
    api,
    auth,
    public,
    static,
)
from routes.admin import (
    core as admin_core,
)
from routes.admin import (
    events as admin_events,
)
from routes.admin import (
    events_crud as admin_events_crud,
)

# admin_news removed - was duplicate of admin_core
from routes.admin import (
    polls as admin_polls,
)
from routes.admin import (
    tournaments as admin_tournaments,
)
from routes.admin import (
    users as admin_users,
)
from routes.admin import (
    lakes as admin_lakes,
)

app.include_router(auth.router)
app.include_router(admin_lakes.router)
app.include_router(admin_core.router)
app.include_router(admin_events.router)
app.include_router(admin_events_crud.router)
app.include_router(admin_polls.router)
app.include_router(admin_tournaments.router)
app.include_router(admin_users.router)
app.include_router(api.router)
app.include_router(static.router)
app.include_router(public.router)  # MUST be last due to catch-all route


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
