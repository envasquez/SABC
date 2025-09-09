import os

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from core.filters import (
    date_format_filter,
    from_json_filter,
    month_number_filter,
    time_format_filter,
)
from routes import (
    admin_core,
    admin_events,
    admin_events_crud,
    admin_polls,
    admin_tournaments,
    admin_users,
    api,
    auth,
    calendar,
    public,
    static,
    tournaments,
)

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

# Include all routers
app.include_router(auth.router)
app.include_router(public.router)
app.include_router(tournaments.router)
app.include_router(calendar.router)
app.include_router(api.router)
app.include_router(static.router)

# Admin routers with prefix
app.include_router(admin_core.router, prefix="/admin")
app.include_router(admin_events.router, prefix="/admin")
app.include_router(admin_events_crud.router, prefix="/admin")
app.include_router(admin_polls.router, prefix="/admin")
app.include_router(admin_tournaments.router, prefix="/admin")
app.include_router(admin_users.router, prefix="/admin")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
