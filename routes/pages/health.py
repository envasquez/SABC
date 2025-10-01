from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from routes.dependencies import db

router = APIRouter()


@router.get("/health")
async def health_check():
    try:
        result = db("SELECT COUNT(*) as count FROM anglers")
        angler_count = result[0][0] if result and len(result) > 0 else 0
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
