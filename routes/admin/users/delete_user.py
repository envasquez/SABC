from typing import Any, Dict

from fastapi import APIRouter, Request, Response

from core.db_schema import Angler
from core.helpers.crud import delete_entity

router = APIRouter()


def _check_self_delete(user: Dict[str, Any], user_id: int) -> bool:
    """Check if user is trying to delete themselves."""
    return user.get("id") == user_id


@router.delete("/admin/users/{user_id}")
async def delete_user(request: Request, user_id: int) -> Response:
    """Delete a user account (cannot delete yourself)."""
    return delete_entity(
        request,
        user_id,
        Angler,
        success_message="User deleted successfully",
        error_message="Failed to delete user",
        self_delete_check=_check_self_delete,
    )
