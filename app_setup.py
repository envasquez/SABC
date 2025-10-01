import os
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from core.deps import (
    CustomJSONEncoder,
    date_format_filter,
    from_json_filter,
    month_number_filter,
    templates,
    time_format_filter,
)
from core.helpers.logging import configure_logging
from core.security_middleware import SecurityHeadersMiddleware


def create_app() -> FastAPI:
    configure_logging(log_level=os.environ.get("LOG_LEVEL", "INFO"))

    app = FastAPI(
        redirect_slashes=False,
        default_response_class=JSONResponse,
    )

    class CustomJSONResponse(JSONResponse):
        def render(self, content: Any) -> bytes:
            import json

            return json.dumps(content, cls=CustomJSONEncoder, ensure_ascii=False).encode("utf-8")

    app.default_response_class = CustomJSONResponse

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        SessionMiddleware, secret_key=os.environ.get("SECRET_KEY", "dev-key-change-in-production")
    )
    app.mount("/static", StaticFiles(directory="static"), name="static")

    templates.env.filters["from_json"] = from_json_filter
    templates.env.filters["date_format"] = date_format_filter
    templates.env.filters["time_format"] = time_format_filter
    templates.env.filters["date_format_dd_mm_yyyy"] = lambda d: date_format_filter(d, "dd-mm-yyyy")
    templates.env.filters["month_number"] = month_number_filter

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
