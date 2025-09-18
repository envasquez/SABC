"""
Centralized dependencies for FastAPI dependency injection.
Reduces code duplication across routes.
"""

import json
from decimal import Decimal
from typing import Any, AsyncGenerator, Dict, Optional

from fastapi import Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import Connection

from core.db_schema import engine
from core.filters import time_format_filter
from core.helpers.auth import require_admin_async  # noqa: E402


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


# Alias for consistency in deps module - re-exported for backward compatibility
require_admin = require_admin_async


def db_query(
    conn: Connection, query: str, params: Optional[Dict[str, Any]] = None
) -> list[Dict[str, Any]]:
    """Execute query and return results as list of dicts."""
    from sqlalchemy import text

    result = conn.execute(text(query), params or {})
    return [dict(row._mapping) for row in result]


def db_query_one(
    conn: Connection, query: str, params: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """Execute query and return first result as dict or None."""
    results = db_query(conn, query, params)
    return results[0] if results else None
