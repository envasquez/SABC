from fastapi import APIRouter

from .lakes import router as lakes_router

router = APIRouter()
router.include_router(lakes_router)
