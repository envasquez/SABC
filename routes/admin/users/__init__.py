from fastapi import APIRouter

from .create_user import router as create_router
from .delete_user import router as delete_router
from .edit_user import router as edit_router
from .list_users import router as list_router
from .update_user import router as update_router

router = APIRouter()

router.include_router(list_router)
router.include_router(create_router)
router.include_router(edit_router)
router.include_router(update_router)
router.include_router(delete_router)
