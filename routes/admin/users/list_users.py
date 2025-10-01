from fastapi import APIRouter, Request

from core.helpers.auth import AdminUser
from routes.dependencies import get_admin_anglers_list, templates

router = APIRouter()


@router.get("/admin/users")
async def admin_users(request: Request, user: AdminUser):
    users = get_admin_anglers_list()

    member_count = sum(1 for u in users if u.get("member"))
    guest_count = sum(1 for u in users if not u.get("member"))
    total_count = len(users)

    return templates.TemplateResponse(
        "admin/users.html",
        {
            "request": request,
            "user": user,
            "users": users,
            "member_count": member_count,
            "guest_count": guest_count,
            "total_count": total_count,
        },
    )
