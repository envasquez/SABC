from fastapi import APIRouter

from .create_event import router as create_router
from .delete_event import router as delete_router
from .get_event_info import router as get_info_router
from .update_event import router as update_router
from .validate_event import router as validate_router

router = APIRouter()
router.include_router(create_router)
router.include_router(update_router)
router.include_router(get_info_router)
router.include_router(validate_router)
router.include_router(delete_router)
