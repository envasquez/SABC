"""
Centralized dependencies for FastAPI dependency injection.
Reduces code duplication across routes.
"""

import json
from decimal import Decimal
from typing import Any, AsyncGenerator, Dict, Optional, Union

from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import Connection

from core.db_schema import engine
from core.filters import time_format_filter
from core.helpers.auth import admin, require_admin_async  # noqa: E402, F401


class CustomJSONEncoder(json.JSONEncoder):
    """Handle Decimal serialization globally."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


templates = Jinja2Templates(directory="templates")
templates.env.filters["time_format"] = time_format_filter


def render(template_name: str, request: Request, **context) -> Any:
    """Simplified template rendering with automatic request/user context."""
    return templates.TemplateResponse(template_name, {"request": request, **context})


async def get_db() -> AsyncGenerator[Connection, None]:
    """Database connection dependency."""
    with engine.connect() as conn:
        yield conn


async def get_admin_or_redirect(request: Request) -> Union[Dict[str, Any], RedirectResponse]:
    """Get admin user or return redirect response for template-based routes."""
    return admin(request)


# Alias for consistency in deps module - re-exported for backward compatibility
require_admin = require_admin_async
