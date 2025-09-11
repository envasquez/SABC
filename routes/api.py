"""API routes for health checks and data access."""

from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from routes.dependencies import db, load_lakes_data

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
    lakes_data = load_lakes_data()
    lakes = []
    for lake_key, lake_info in lakes_data.items():
        lakes.append(
            {
                "key": lake_key,
                "name": lake_info.get("display_name", lake_key.replace("_", " ").title()),
            }
        )
    return JSONResponse(sorted(lakes, key=lambda x: x["name"]))


@router.get("/api/lakes/{lake_key}/ramps")
async def api_get_lake_ramps(lake_key: str):
    """Get ramps for a specific lake."""
    lakes_data = load_lakes_data()
    return (
        JSONResponse({"ramps": []})
        if lake_key not in lakes_data
        else JSONResponse({"ramps": lakes_data[lake_key].get("ramps", [])})
    )
