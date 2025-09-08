from fastapi.responses import RedirectResponse

from core.database import db


def u(r):
    if uid := r.session.get("user_id"):
        res = db(
            "SELECT id, name, email, member, is_admin, year_joined, phone FROM anglers WHERE id=:id AND active=1",
            {"id": uid},
        )
        return (
            dict(zip(["id", "name", "email", "member", "is_admin", "year_joined", "phone"], res[0]))
            if res
            else None
        )


def admin(r):
    return u(r) if (user := u(r)) and user["is_admin"] else RedirectResponse("/login")
