from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from core.db_schema import Angler, get_session

router = APIRouter()


@router.get("/health")
async def health_check():
    try:
        with get_session() as session:
            angler_count = session.query(Angler).count()
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
