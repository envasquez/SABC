"""Authentication and authorization helper functions with full type safety."""

from typing import Annotated, Dict, Optional, Union

from fastapi import Depends, HTTPException, Request

from core.db_schema import engine
from core.query_service import QueryService

UserDict = Dict[str, Union[int, str, bool, None]]


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
        raise HTTPException(status_code=303, headers={"Location": "/login"})
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
        raise HTTPException(status_code=302, headers={"Location": "/login"})
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
        raise HTTPException(status_code=303, headers={"Location": "/login"})
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
