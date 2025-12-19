from fastapi import APIRouter

from .gallery import router as gallery_router

router = APIRouter()

router.include_router(gallery_router)
