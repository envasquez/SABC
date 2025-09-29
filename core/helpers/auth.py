from typing import Any, Dict, Optional, Union

from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse

from core.db_schema import engine
from core.query_service import QueryService


def u(r: Request) -> Optional[Dict[str, Union[int, str, bool, None]]]:
    """Core function to get user from session."""
    if uid := r.session.get("user_id"):
        with engine.connect() as conn:
            qs = QueryService(conn)
            return qs.get_user_by_id(uid)
    return None


def admin(r: Request) -> Union[Dict[str, Union[int, str, bool, None]], RedirectResponse]:
    """Get admin user or return redirect."""
    user = u(r)
    if user and user["is_admin"]:
        return user
    return RedirectResponse("/login")


async def require_admin_async(request: Request) -> Dict[str, Any]:
    """Async version: require admin user, raises exception if not admin."""
    user = admin(request)
    if isinstance(user, RedirectResponse):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# Synchronous versions for non-async contexts
def require_auth(request: Request) -> Dict[str, Union[int, str, bool, None]]:
    """Synchronous version: require authenticated user."""
    user = u(request)
    if not user:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user


def require_admin(
    request: Request,
) -> Union[Dict[str, Union[int, str, bool, None]], RedirectResponse]:
    """Synchronous version: require admin user (used by admin routes)."""
    user = u(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if not user.get("is_admin"):
        return RedirectResponse("/", status_code=302)
    return user


def require_member(request: Request) -> Dict[str, Union[int, str, bool, None]]:
    """Require member user."""
    user = u(request)
    if not user:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    if not user.get("member"):
        raise HTTPException(status_code=403)
    return user


def get_user_optional(request: Request) -> Optional[Dict[str, Union[int, str, bool, None]]]:
    """Get user if authenticated, otherwise None."""
    return u(request)
