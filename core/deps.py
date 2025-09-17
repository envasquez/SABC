"""
Centralized dependencies for FastAPI dependency injection.
Reduces code duplication across routes.
"""

import json
from decimal import Decimal
from typing import Any, Optional

from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import Connection

from core.db_schema import engine
from core.filters import time_format_filter


class CustomJSONEncoder(json.JSONEncoder):
    """Handle Decimal serialization globally."""

    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


templates = Jinja2Templates(directory="templates")
templates.env.filters["time_format"] = time_format_filter


def render(template_name: str, request: Request, **context) -> Any:
    """Simplified template rendering with automatic request/user context."""
    return templates.TemplateResponse(template_name, {"request": request, **context})


async def get_db():
    """Database connection dependency."""
    with engine.connect() as conn:
        yield conn


async def get_current_user(request: Request) -> Optional[dict]:
    """Get current user from session, returns None if not authenticated."""
    from core.helpers.auth import u

    user = u(request)
    if isinstance(user, RedirectResponse):
        return None
    return user


async def require_user(request: Request) -> dict:
    """Require authenticated user, raises exception if not authenticated."""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


async def require_admin(request: Request) -> dict:
    """Require admin user, raises exception if not admin."""
    from core.helpers.auth import admin

    user = admin(request)
    if isinstance(user, RedirectResponse):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


async def get_user_or_redirect(request: Request) -> Any:
    """Get user or return redirect response for template-based routes."""
    from core.helpers.auth import u

    return u(request)


async def get_admin_or_redirect(request: Request) -> Any:
    """Get admin or return redirect response for template-based routes."""
    from core.helpers.auth import admin

    return admin(request)


def db_query(conn: Connection, query: str, params: Optional[dict] = None) -> list[dict]:
    """Execute query and return results as list of dicts."""
    from sqlalchemy import text

    result = conn.execute(text(query), params or {})
    return [dict(row._mapping) for row in result]


def db_query_one(conn: Connection, query: str, params: Optional[dict] = None) -> Optional[dict]:
    """Execute query and return first result as dict or None."""
    results = db_query(conn, query, params)
    return results[0] if results else None
