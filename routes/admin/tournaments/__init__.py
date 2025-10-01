from fastapi import APIRouter

from .enter_results import router as enter_results_router
from .individual_results import router as individual_results_router
from .list_tournaments import router as list_router
from .manage_results import router as manage_router
from .team_results import router as team_results_router

router = APIRouter()
router.include_router(list_router)
router.include_router(enter_results_router)
router.include_router(individual_results_router)
router.include_router(team_results_router)
router.include_router(manage_router)
