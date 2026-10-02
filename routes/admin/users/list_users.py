from fastapi import APIRouter, Request
from fastapi.responses import Response

from core.helpers.auth import AdminUser
from core.helpers.members import is_dues_current
from routes.dependencies import get_admin_anglers_list, templates

router = APIRouter()


@router.get("/admin/users")
def admin_users(request: Request, user: AdminUser) -> Response:
    users = get_admin_anglers_list()
    members = [u for u in users if u.get("member")]
    active_member_count = sum(1 for u in members if is_dues_current(u.get("dues_paid_through")))
    overdue_member_count = len(members) - active_member_count
    guest_count = sum(1 for u in users if not u.get("member"))
    total_count = len(users)
    return templates.TemplateResponse(
        request,
        "admin/users.html",
        {
            "user": user,
            "users": users,
            "active_member_count": active_member_count,
            "overdue_member_count": overdue_member_count,
            "guest_count": guest_count,
            "total_count": total_count,
        },
    )
