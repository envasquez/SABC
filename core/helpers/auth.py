from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse

from core.database import db


def u(r):
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


def admin(r):
    return u(r) if (user := u(r)) and user["is_admin"] else RedirectResponse("/login")


def require_auth(request: Request):
    user = u(request)
    if not user:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user


def require_admin(request: Request):
    user = u(request)
    if not user:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    if not user.get("is_admin"):
        raise HTTPException(status_code=403)
    return user


def require_member(request: Request):
    user = u(request)
    if not user:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    if not user.get("member"):
        raise HTTPException(status_code=403)
    return user


def get_user_optional(request: Request):
    return u(request)
