from fastapi import APIRouter

from .dashboard import router as dashboard_router
from .news import router as news_router

router = APIRouter()

router.include_router(news_router)
router.include_router(dashboard_router)
