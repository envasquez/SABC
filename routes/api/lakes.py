from fastapi import APIRouter
from fastapi.responses import JSONResponse

from core.db_schema import Lake, Ramp, get_session

router = APIRouter()


@router.get("/api/lakes")
async def api_get_lakes():
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
    except Exception:
        return JSONResponse([])


@router.get("/api/lakes/{lake_key}/ramps")
async def api_get_lake_ramps(lake_key: str):
    with get_session() as session:
        lake = session.query(Lake).filter(Lake.yaml_key == lake_key).first()
        if not lake:
            return JSONResponse({"ramps": []})

        ramps_query = session.query(Ramp.id, Ramp.name).filter(Ramp.lake_id == lake.id).all()
        ramps = [{"id": ramp_id, "name": ramp_name} for ramp_id, ramp_name in ramps_query]

    return JSONResponse({"ramps": ramps})
