import os
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.sessions import SessionMiddleware

from core.csrf_middleware import CSRFMiddleware
from core.deps import (
    CustomJSONEncoder,
    date_format_filter,
    from_json_filter,
    month_number_filter,
    templates,
    time_format_filter,
)
from core.helpers.logging import configure_logging
from core.monitoring import init_sentry
from core.monitoring.middleware import MetricsMiddleware
from core.security_middleware import SecurityHeadersMiddleware


def get_csrf_token(request: Request) -> str:
    """Extract CSRF token from request cookies."""
    return request.cookies.get("csrf_token", "")


def create_app() -> FastAPI:
    # Initialize monitoring before anything else
    init_sentry()
    configure_logging(log_level=os.environ.get("LOG_LEVEL", "INFO"))

    app = FastAPI(
        redirect_slashes=False,
        default_response_class=JSONResponse,
    )

    class CustomJSONResponse(JSONResponse):
        def render(self, content: Any) -> bytes:
            import json

            return json.dumps(content, cls=CustomJSONEncoder, ensure_ascii=False).encode("utf-8")

    app.default_response_class = CustomJSONResponse  # type: ignore[attr-defined]

    # Rate limiting
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    # Metrics middleware (should be early in the chain)
    app.add_middleware(MetricsMiddleware)

    app.add_middleware(SecurityHeadersMiddleware)

    # Session middleware with secure configuration
    app.add_middleware(
        SessionMiddleware,
        secret_key=os.environ.get("SECRET_KEY", "dev-key-change-in-production"),
        session_cookie="sabc_session",
        max_age=int(os.environ.get("SESSION_TIMEOUT", "86400")),  # Default 24 hours
        same_site="lax",  # "lax" for better compatibility, "strict" for maximum security
        https_only=os.environ.get("ENVIRONMENT", "development") == "production",
    )

    # CSRF protection middleware
    app.add_middleware(
        CSRFMiddleware,
        secret=os.environ.get("SECRET_KEY", "dev-key-change-in-production"),
        cookie_name="csrf_token",
        cookie_secure=os.environ.get("ENVIRONMENT", "development") == "production",
        cookie_samesite="lax",
        header_name="x-csrf-token",
    )

    app.mount("/static", StaticFiles(directory="static"), name="static")

    templates.env.filters["from_json"] = from_json_filter
    templates.env.filters["date_format"] = date_format_filter
    templates.env.filters["time_format"] = time_format_filter
    templates.env.filters["date_format_dd_mm_yyyy"] = lambda d: date_format_filter(d, "dd-mm-yyyy")
    templates.env.filters["month_number"] = month_number_filter

    # Add CSRF token to global template context
    templates.env.globals["get_csrf_token"] = get_csrf_token

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors(), "body": exc.body},
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"error": str(exc)})

    return app
