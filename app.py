import os

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from core.deps import CustomJSONEncoder, templates
from core.filters import (
    date_format_filter,
    from_json_filter,
    month_number_filter,
    time_format_filter,
)
from core.helpers.logging_config import configure_logging, get_logger
from core.security_middleware import SecurityHeadersMiddleware

configure_logging(log_level=os.environ.get("LOG_LEVEL", "INFO"))
logger = get_logger(__name__)

# Create app with custom JSON encoder for Decimal support
app = FastAPI(
    redirect_slashes=False,
    default_response_class=JSONResponse,
)


# Configure custom JSON response class for FastAPI
class CustomJSONResponse(JSONResponse):
    def render(self, content) -> bytes:
        import json

        return json.dumps(content, cls=CustomJSONEncoder, ensure_ascii=False).encode("utf-8")


app.default_response_class = CustomJSONResponse

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    SessionMiddleware, secret_key=os.environ.get("SECRET_KEY", "dev-key-change-in-production")
)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure template filters
templates.env.filters["from_json"] = from_json_filter
templates.env.filters["date_format"] = date_format_filter
templates.env.filters["time_format"] = time_format_filter
templates.env.filters["date_format_dd_mm_yyyy"] = lambda d: date_format_filter(d, "dd-mm-yyyy")
templates.env.filters["month_number"] = month_number_filter


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body},
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={"error": str(exc)})


from routes import (
    api,
    auth,
    awards,
    pages,
    static,
    tournaments_public,
    voting,
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
from routes.admin import (
    lakes as admin_lakes,
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

# Public route modules (consolidated)
app.include_router(voting.router)
app.include_router(tournaments_public.router)
app.include_router(awards.router)
app.include_router(pages.router)  # MUST be last due to catch-all route


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
