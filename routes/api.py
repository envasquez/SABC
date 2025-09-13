"""API routes for health checks and data access."""

from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from routes.dependencies import db, get_ramps_for_lake

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint for CI/CD and monitoring."""
    try:
        result = db("SELECT COUNT(*) as count FROM anglers")
        angler_count = result[0][0] if result else 0
        return {
            "status": "healthy",
            "database": "connected",
            "angler_count": angler_count,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            },
        )


@router.get("/api/lakes")
async def api_get_lakes():
    """Get all lakes from database for dropdowns."""
    try:
        # Direct database query to get all lakes
        lakes_data = db("SELECT id, yaml_key, display_name FROM lakes ORDER BY display_name")

        lakes = []
        for lake_id, yaml_key, display_name in lakes_data:
            lakes.append(
                {
                    "key": yaml_key,
                    "name": display_name,
                    "id": lake_id,
                }
            )

        return JSONResponse(lakes)
    except Exception:
        return JSONResponse([])


@router.get("/api/lakes/{lake_key}/ramps")
async def api_get_lake_ramps(lake_key: str):
    """Get ramps for a specific lake."""
    # Find lake by yaml_key
    lake_data = db("SELECT id FROM lakes WHERE yaml_key = :key", {"key": lake_key})
    if not lake_data:
        return JSONResponse({"ramps": []})

    lake_id = lake_data[0][0]
    ramps_list = get_ramps_for_lake(lake_id)

    ramps = []
    for ramp_id, ramp_name, lake_id in ramps_list:
        ramps.append(
            {
                "id": ramp_id,
                "name": ramp_name,
            }
        )

    return JSONResponse({"ramps": ramps})
