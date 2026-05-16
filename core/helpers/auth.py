"""Authentication and authorization helper functions with full type safety."""

from datetime import date
from typing import Annotated, Optional
from urllib.parse import quote

from fastapi import Depends, HTTPException, Request

from core.db_schema import engine
from core.query_service import QueryService
from core.types import UserDict


def is_dues_current(user: UserDict) -> bool:
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

    Validates the embedded session_version against the angler row. If the
    session predates this field, or the DB has been bumped (e.g. on a
    password change from another device), the cookie is treated as
    revoked: the session is cleared and None is returned, forcing a
    re-login.

    Args:
        request: FastAPI Request object

    Returns:
        User dictionary if authenticated, None otherwise
    """
    uid = request.session.get("user_id")
    if not uid:
        return None
    with engine.connect() as conn:
        qs = QueryService(conn)
        user = qs.get_user_by_id(uid)
    if user is None:
        # User deleted out from under the session
        request.session.clear()
        return None
    session_ver = request.session.get("session_version")
    db_ver = user.get("session_version")
    if session_ver != db_ver:
        # Cookie was issued before this revision was bumped (or pre-dates
        # the session_version field entirely) -> force re-login.
        request.session.clear()
        return None
    return user


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


# Backwards-compatible alias of `get_current_user`.
#
# The audit flagged `get_user_optional` as an identity wrapper. The
# `OptionalUser` dependency below is repointed directly at `get_current_user`,
# but the wrapper symbol is kept as an alias because several route modules
# (routes/pages/{home,awards,calendar,roster,data}.py) still import and call
# `get_user_optional` directly. Removing the name would break those imports.
get_user_optional = get_current_user


# Type aliases for FastAPI dependency injection
AdminUser = Annotated[UserDict, Depends(require_admin)]
AuthUser = Annotated[UserDict, Depends(require_auth)]
MemberUser = Annotated[UserDict, Depends(require_member)]
OptionalUser = Annotated[Optional[UserDict], Depends(get_current_user)]
