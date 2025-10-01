from typing import Annotated, Any, Dict, Optional, Union

from fastapi import Depends, HTTPException, Request

from core.db_schema import engine
from core.query_service import QueryService


def u(r: Request) -> Optional[Dict[str, Union[int, str, bool, None]]]:
    if uid := r.session.get("user_id"):
        with engine.connect() as conn:
            qs = QueryService(conn)
            return qs.get_user_by_id(uid)
    return None


def admin(r: Request) -> Dict[str, Union[int, str, bool, None]]:
    user = u(r)
    if user and user["is_admin"]:
        return user
    raise HTTPException(status_code=302, headers={"Location": "/login"})


async def require_admin_async(request: Request) -> Dict[str, Any]:
    return admin(request)


def require_auth(request: Request) -> Dict[str, Union[int, str, bool, None]]:
    user = u(request)
    if not user:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user


def require_admin(request: Request) -> Dict[str, Union[int, str, bool, None]]:
    user = u(request)
    if not user:
        raise HTTPException(status_code=302, headers={"Location": "/login"})
    if not user.get("is_admin"):
        raise HTTPException(status_code=302, headers={"Location": "/"})
    return user


def require_member(request: Request) -> Dict[str, Union[int, str, bool, None]]:
    user = u(request)
    if not user:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    if not user.get("member"):
        raise HTTPException(status_code=403)
    return user


def get_user_optional(request: Request) -> Optional[Dict[str, Union[int, str, bool, None]]]:
    return u(request)


AdminUser = Annotated[Dict[str, Any], Depends(require_admin)]
AuthUser = Annotated[Dict[str, Any], Depends(require_auth)]
MemberUser = Annotated[Dict[str, Any], Depends(require_member)]
OptionalUser = Annotated[Optional[Dict[str, Any]], Depends(get_user_optional)]
