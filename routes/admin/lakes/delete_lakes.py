from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from core.helpers.auth import require_admin
from routes.dependencies import db

router = APIRouter()


@router.delete("/admin/ramps/{ramp_id}")
async def delete_ramp(request: Request, ramp_id: int):
    _user = require_admin(request)
    try:
        usage_count = db("SELECT COUNT(*) FROM tournaments WHERE ramp_id = :id", {"id": ramp_id})[
            0
        ][0]
        if usage_count > 0:
            return JSONResponse(
                {"error": "Cannot delete ramp that is referenced by tournaments"}, status_code=400
            )
        db("DELETE FROM ramps WHERE id = :id", {"id": ramp_id})
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/admin/lakes/{lake_id}")
async def delete_lake(request: Request, lake_id: int):
    _user = require_admin(request)
    try:
        usage_count = db(
            "SELECT COUNT(*) FROM tournaments t JOIN ramps r ON t.ramp_id = r.id WHERE r.lake_id = :id",
            {"id": lake_id},
        )[0][0]
        if usage_count > 0:
            return JSONResponse(
                {"error": "Cannot delete lake that is referenced by tournaments or ramps"},
                status_code=400,
            )
        db("DELETE FROM lakes WHERE id = :id", {"id": lake_id})
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
