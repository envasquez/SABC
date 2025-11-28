import os
import re
from typing import Any, Dict, List, Sequence

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
    safe_json_filter,
    templates,
    time_format_filter,
)
from core.helpers.logging import configure_logging, get_logger
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

    # Rate limiting (disabled in test environment to avoid rate limit errors in test suites)
    is_test_env = os.environ.get("ENVIRONMENT") == "test"
    limiter = Limiter(key_func=get_remote_address, enabled=not is_test_env)
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

    # CSRF protection middleware (disabled in test environment to simplify testing)
    if os.environ.get("ENVIRONMENT") != "test":
        app.add_middleware(
            CSRFMiddleware,
            secret=os.environ.get("SECRET_KEY", "dev-key-change-in-production"),
            cookie_name="csrf_token",
            cookie_secure=os.environ.get("ENVIRONMENT", "development") == "production",
            cookie_samesite="lax",
            header_name="x-csrf-token",
            # Exempt authentication endpoints - they have their own security measures
            # These endpoints either use email verification, session management, or rate limiting
            exempt_urls=[
                re.compile(r"^/login$"),  # Login - protected by rate limiting + bcrypt
                re.compile(r"^/logout$"),  # Logout - session-based, no sensitive state change
                re.compile(r"^/register$"),  # Registration - email verification required
                re.compile(r"^/forgot-password$"),  # Password reset request - email verification
                re.compile(r"^/reset-password$"),  # Password reset - cryptographic tokens
            ],
        )

    app.mount("/static", StaticFiles(directory="static"), name="static")

    templates.env.filters["from_json"] = from_json_filter
    templates.env.filters["date_format"] = date_format_filter
    templates.env.filters["time_format"] = time_format_filter
    templates.env.filters["date_format_dd_mm_yyyy"] = lambda d: date_format_filter(d, "dd-mm-yyyy")
    templates.env.filters["month_number"] = month_number_filter
    templates.env.filters["safe_json"] = safe_json_filter

    # Add CSRF token to global template context
    templates.env.globals["get_csrf_token"] = get_csrf_token

    # Logger for exception handlers
    error_logger = get_logger("exception_handler")

    def _sanitize_validation_errors(errors: Sequence[Any]) -> List[Dict[str, Any]]:
        """
        Sanitize validation errors to prevent information disclosure.
        Returns only field names and error types, not internal details.
        """
        sanitized = []
        for error in errors:
            sanitized.append(
                {
                    "loc": error.get("loc", []),
                    "type": error.get("type", "validation_error"),
                    "msg": error.get("msg", "Invalid value"),
                }
            )
        return sanitized

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Log full error details for debugging (not exposed to user)
        error_logger.warning(
            "Validation error",
            extra={
                "path": request.url.path,
                "method": request.method,
                "errors": exc.errors(),
            },
        )

        # Return sanitized error response (no body content, no internal details)
        return JSONResponse(
            status_code=422,
            content={"detail": _sanitize_validation_errors(exc.errors())},
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        error_logger.warning(
            "ValueError in request",
            extra={"path": request.url.path, "error": str(exc)},
        )
        return JSONResponse(status_code=400, content={"error": "Invalid request data"})

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """
        Global exception handler for unhandled exceptions.
        Logs full error details but returns a generic message to prevent info disclosure.
        """
        error_logger.error(
            "Unhandled exception",
            extra={
                "path": request.url.path,
                "method": request.method,
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
            exc_info=True,
        )

        # Return generic error message - never expose internal details
        return JSONResponse(
            status_code=500,
            content={"error": "An internal error occurred. Please try again later."},
        )

    return app
