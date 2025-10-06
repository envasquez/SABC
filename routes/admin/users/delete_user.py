from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from core.db_schema import Angler, get_session
from core.helpers.auth import require_admin

router = APIRouter()


@router.delete("/admin/users/{user_id}")
async def delete_user(request: Request, user_id: int):
    user = require_admin(request)
    if user.get("id") == user_id:
        return JSONResponse({"error": "Cannot delete yourself"}, status_code=400)

    try:
        with get_session() as session:
            angler = session.query(Angler).filter(Angler.id == user_id).first()
            if angler:
                session.delete(angler)
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
