from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from core.db_schema import Lake, Ramp, get_session
from core.helpers.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/api/lakes")
def api_get_lakes() -> JSONResponse:
    try:
        with get_session() as session:
            lakes_query = (
                session.query(Lake.id, Lake.yaml_key, Lake.display_name)
                .order_by(Lake.display_name)
                .all()
            )
            lakes = [
                {
                    "key": yaml_key,
                    "name": display_name,
                    "id": lake_id,
                }
                for lake_id, yaml_key, display_name in lakes_query
            ]
        return JSONResponse(lakes)
    except SQLAlchemyError as exc:
        # Log and surface a real error rather than silently returning an empty
        # list — admins would otherwise see "no lakes" instead of "DB down".
        logger.error("api_get_lakes: database error", exc_info=exc)
        return JSONResponse(
            {"error": "Failed to load lakes"},
            status_code=500,
        )


@router.get("/api/lakes/{lake_key}/ramps")
def api_get_lake_ramps(lake_key: str) -> JSONResponse:
    with get_session() as session:
        lake = session.query(Lake).filter(Lake.yaml_key == lake_key).first()
        if not lake:
            return JSONResponse({"ramps": []})

        ramps_query = session.query(Ramp.id, Ramp.name).filter(Ramp.lake_id == lake.id).all()
        ramps = [{"id": ramp_id, "name": ramp_name} for ramp_id, ramp_name in ramps_query]

    return JSONResponse({"ramps": ramps})
