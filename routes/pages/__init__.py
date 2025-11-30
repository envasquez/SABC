from fastapi import APIRouter

from .awards import router as awards_router
from .calendar import router as calendar_router
from .data import router as data_router
from .health import router as health_router
from .home import router as home_router
from .roster import router as roster_router

router = APIRouter()

router.include_router(health_router)
router.include_router(roster_router)
router.include_router(calendar_router)
router.include_router(awards_router)
router.include_router(data_router)
router.include_router(home_router)
