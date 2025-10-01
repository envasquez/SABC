from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse

from core.helpers.auth import require_admin
from routes.dependencies import db

router = APIRouter()


@router.delete("/admin/users/{user_id}")
async def delete_user(request: Request, user_id: int):
    user = require_admin(request)

    if isinstance(user, RedirectResponse):
        return user

    if user.get("id") == user_id:
        return JSONResponse({"error": "Cannot delete yourself"}, status_code=400)

    try:
        db("DELETE FROM anglers WHERE id = :id", {"id": user_id})
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
