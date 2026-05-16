from typing import Any, Dict, Union

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from core.db_schema import Angler, get_session, utc_now

router = APIRouter()


@router.get("/health", response_model=None)
def health_check() -> Union[Dict[str, Any], JSONResponse]:
    try:
        with get_session() as session:
            angler_count = session.query(Angler).count()
        return {
            "status": "healthy",
            "database": "connected",
            "angler_count": angler_count,
            "timestamp": utc_now().isoformat(),
        }
    except SQLAlchemyError:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "timestamp": utc_now().isoformat(),
            },
        )
