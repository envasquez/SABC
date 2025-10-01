from fastapi import APIRouter

from .view import router as view_router

router = APIRouter()
router.include_router(view_router)
