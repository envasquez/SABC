from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func

from core.db_schema import Lake, Ramp, Tournament, get_session
from core.helpers.auth import require_admin

router = APIRouter()


@router.delete("/admin/ramps/{ramp_id}")
async def delete_ramp(request: Request, ramp_id: int):
    _user = require_admin(request)
    try:
        with get_session() as session:
            usage_count = (
                session.query(func.count(Tournament.id))
                .filter(Tournament.ramp_id == ramp_id)
                .scalar()
            )
            if usage_count > 0:
                return JSONResponse(
                    {"error": "Cannot delete ramp that is referenced by tournaments"},
                    status_code=400,
                )
            session.query(Ramp).filter(Ramp.id == ramp_id).delete()
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/admin/lakes/{lake_id}")
async def delete_lake(request: Request, lake_id: int):
    _user = require_admin(request)
    try:
        with get_session() as session:
            usage_count = (
                session.query(func.count(Tournament.id))
                .join(Ramp, Tournament.ramp_id == Ramp.id)
                .filter(Ramp.lake_id == lake_id)
                .scalar()
            )
            if usage_count > 0:
                return JSONResponse(
                    {"error": "Cannot delete lake that is referenced by tournaments or ramps"},
                    status_code=400,
                )
            session.query(Lake).filter(Lake.id == lake_id).delete()
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
