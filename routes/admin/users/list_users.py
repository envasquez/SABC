from datetime import date

from fastapi import APIRouter, Request

from core.helpers.auth import AdminUser
from routes.dependencies import get_admin_anglers_list, templates

router = APIRouter()


def _is_dues_current(dues_paid_through: object) -> bool:
    """Check if dues are current based on dues_paid_through value."""
    if dues_paid_through is None:
        return False
    if isinstance(dues_paid_through, str):
        try:
            dues_paid_through = date.fromisoformat(dues_paid_through)
        except ValueError:
            return False
    if isinstance(dues_paid_through, date):
        return dues_paid_through >= date.today()
    return False


@router.get("/admin/users")
async def admin_users(request: Request, user: AdminUser):
    users = get_admin_anglers_list()
    members = [u for u in users if u.get("member")]
    active_member_count = sum(1 for u in members if _is_dues_current(u.get("dues_paid_through")))
    overdue_member_count = len(members) - active_member_count
    guest_count = sum(1 for u in users if not u.get("member"))
    total_count = len(users)
    return templates.TemplateResponse(
        "admin/users.html",
        {
            "request": request,
            "user": user,
            "users": users,
            "active_member_count": active_member_count,
            "overdue_member_count": overdue_member_count,
            "guest_count": guest_count,
            "total_count": total_count,
        },
    )
