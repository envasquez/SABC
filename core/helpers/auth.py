from typing import Annotated, Any, Dict, Optional, Union

from fastapi import Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from core.db_schema import engine
from core.query_service import QueryService


def u(r: Request) -> Optional[Dict[str, Union[int, str, bool, None]]]:
    if uid := r.session.get("user_id"):
        with engine.connect() as conn:
            qs = QueryService(conn)
            return qs.get_user_by_id(uid)
    return None


def admin(r: Request) -> Union[Dict[str, Union[int, str, bool, None]], RedirectResponse]:
    user = u(r)
    if user and user["is_admin"]:
        return user
    return RedirectResponse("/login")


async def require_admin_async(request: Request) -> Dict[str, Any]:
    user = admin(request)
    if isinstance(user, RedirectResponse):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def require_auth(request: Request) -> Dict[str, Union[int, str, bool, None]]:
    user = u(request)
    if not user:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user


def require_admin(
    request: Request,
) -> Union[Dict[str, Union[int, str, bool, None]], RedirectResponse]:
    user = u(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    if not user.get("is_admin"):
        return RedirectResponse("/", status_code=302)
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
