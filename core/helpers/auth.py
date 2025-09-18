from typing import Any, Dict, Optional, Union

from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse

from core.database import db


def u(r: Request) -> Optional[Dict[str, Union[int, str, bool, None]]]:
    """Core function to get user from session."""
    if uid := r.session.get("user_id"):
        res = db(
            "SELECT id, name, email, member, is_admin, year_joined, phone FROM anglers WHERE id=:id",
            {"id": uid},
        )
        return (
            dict(zip(["id", "name", "email", "member", "is_admin", "year_joined", "phone"], res[0]))
            if res
            else None
        )
    return None


def admin(r: Request) -> Union[Dict[str, Union[int, str, bool, None]], RedirectResponse]:
    """Get admin user or return redirect."""
    user = u(r)
    if user and user["is_admin"]:
        return user
    return RedirectResponse("/login")


# Async wrapper functions for use with FastAPI dependency injection
async def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """Get current user from session, returns None if not authenticated."""
    user = u(request)
    if isinstance(user, RedirectResponse):
        return None
    return user


async def require_user(request: Request) -> Dict[str, Any]:
    """Require authenticated user, raises exception if not authenticated."""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


async def require_admin_async(request: Request) -> Dict[str, Any]:
    """Async version: require admin user, raises exception if not admin."""
    user = admin(request)
    if isinstance(user, RedirectResponse):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


async def get_user_or_redirect(request: Request) -> Union[Dict[str, Any], RedirectResponse]:
    """Get user or return redirect response for template-based routes."""
    user = u(request)
    if user is None:
        return RedirectResponse("/login")
    return user


async def get_admin_or_redirect(request: Request) -> Union[Dict[str, Any], RedirectResponse]:
    """Get admin or return redirect response for template-based routes."""
    return admin(request)


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
