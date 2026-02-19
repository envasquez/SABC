"""Authentication and authorization helper functions with full type safety."""

from datetime import date
from typing import Annotated, Any, Dict, Optional, Union
from urllib.parse import quote

from fastapi import Depends, HTTPException, Request

from core.db_schema import engine
from core.query_service import QueryService

UserDict = Dict[str, Union[int, str, bool, None]]


def is_dues_current(user: Dict[str, Any]) -> bool:
    """
    Check if user's dues are paid through today or later.

    Args:
        user: User dictionary with dues_paid_through field

    Returns:
        True if dues are current (paid through today or later), False otherwise
    """
    dues_paid_through = user.get("dues_paid_through")
    if dues_paid_through is None:
        return False
    # Handle case where value comes as string from some query results
    if isinstance(dues_paid_through, str):
        dues_paid_through = date.fromisoformat(dues_paid_through)
    return dues_paid_through >= date.today()


def _build_login_redirect_url(request: Request) -> str:
    """
    Build login URL with 'next' parameter for post-login redirect.

    Args:
        request: FastAPI Request object

    Returns:
        Login URL with encoded next parameter
    """
    current_path = str(request.url.path)
    if request.url.query:
        current_path += f"?{request.url.query}"
    next_param = quote(current_path, safe="/?&=")
    return f"/login?next={next_param}"


def get_current_user(request: Request) -> Optional[UserDict]:
    """
    Get current user from session.

    Args:
        request: FastAPI Request object

    Returns:
        User dictionary if authenticated, None otherwise
    """
    if uid := request.session.get("user_id"):
        with engine.connect() as conn:
            qs = QueryService(conn)
            return qs.get_user_by_id(uid)
    return None


def require_auth(request: Request) -> UserDict:
    """
    Require user to be authenticated.

    Args:
        request: FastAPI Request object

    Returns:
        User dictionary if authenticated

    Raises:
        HTTPException: 303 redirect to login if not authenticated
    """
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=303, headers={"Location": _build_login_redirect_url(request)}
        )
    return user


def require_admin(request: Request) -> UserDict:
    """
    Require user to be authenticated and have admin privileges.

    Args:
        request: FastAPI Request object

    Returns:
        User dictionary if admin

    Raises:
        HTTPException: 302 redirect if not authenticated or not admin
    """
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=302, headers={"Location": _build_login_redirect_url(request)}
        )
    if not user.get("is_admin"):
        raise HTTPException(status_code=302, headers={"Location": "/"})
    return user


def require_member(request: Request) -> UserDict:
    """
    Require user to be authenticated and have member status.

    Args:
        request: FastAPI Request object

    Returns:
        User dictionary if member

    Raises:
        HTTPException: 303 redirect if not authenticated, 403 if not a member
    """
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=303, headers={"Location": _build_login_redirect_url(request)}
        )
    if not user.get("member"):
        raise HTTPException(status_code=403)
    return user


def get_user_optional(request: Request) -> Optional[UserDict]:
    """
    Get current user if authenticated, None otherwise.

    Args:
        request: FastAPI Request object

    Returns:
        User dictionary if authenticated, None otherwise
    """
    return get_current_user(request)


# Type aliases for FastAPI dependency injection
AdminUser = Annotated[UserDict, Depends(require_admin)]
AuthUser = Annotated[UserDict, Depends(require_auth)]
MemberUser = Annotated[UserDict, Depends(require_member)]
OptionalUser = Annotated[Optional[UserDict], Depends(get_user_optional)]
