"""Authentication and authorization helper functions with full type safety."""

from typing import Annotated, Dict, Optional, Union

from fastapi import Depends, HTTPException, Request

from core.db_schema import engine
from core.query_service import QueryService

UserDict = Dict[str, Union[int, str, bool, None]]


def u(r: Request) -> Optional[UserDict]:
    """
    Get current user from session.

    Args:
        r: FastAPI Request object

    Returns:
        User dictionary if authenticated, None otherwise
    """
    if uid := r.session.get("user_id"):
        with engine.connect() as conn:
            qs = QueryService(conn)
            return qs.get_user_by_id(uid)
    return None


def admin(r: Request) -> UserDict:
    """
    Get current user and require admin privileges (legacy function).

    Args:
        r: FastAPI Request object

    Returns:
        User dictionary if admin

    Raises:
        HTTPException: 302 redirect if not authenticated or not admin
    """
    user = u(r)
    if user and user["is_admin"]:
        return user
    raise HTTPException(status_code=302, headers={"Location": "/login"})


async def require_admin_async(request: Request) -> UserDict:
    """
    Async version of require_admin for FastAPI dependencies.

    Args:
        request: FastAPI Request object

    Returns:
        User dictionary if admin

    Raises:
        HTTPException: 302 redirect if not authenticated or not admin
    """
    return admin(request)


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
    user = u(request)
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
    user = u(request)
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
    user = u(request)
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
    return u(request)


# Type aliases for FastAPI dependency injection
AdminUser = Annotated[UserDict, Depends(require_admin)]
AuthUser = Annotated[UserDict, Depends(require_auth)]
MemberUser = Annotated[UserDict, Depends(require_member)]
OptionalUser = Annotated[Optional[UserDict], Depends(get_user_optional)]
