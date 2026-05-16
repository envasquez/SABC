from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from core.helpers.auth import require_admin
from routes.dependencies import validate_event_data

router = APIRouter()


@router.post("/admin/events/validate")
async def validate_event(request: Request) -> JSONResponse:
    _user = require_admin(request)
    try:
        data = await request.json()
        validation = validate_event_data(
            data.get("date", ""),
            data.get("name", ""),
            data.get("event_type", ""),
            data.get("start_time", ""),
            data.get("weigh_in_time", ""),
            data.get("entry_fee", 0),
            data.get("lake_name", ""),
        )
        return JSONResponse(validation)
    except (ValueError, KeyError, TypeError):
        return JSONResponse({"error": "Validation failed"}, status_code=500)
