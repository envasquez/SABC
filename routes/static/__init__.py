from fastapi import APIRouter

from .icons import router as icons_router

router = APIRouter()
router.include_router(icons_router)
