from fastapi import APIRouter

from .login import router as login_router
from .profile import router as profile_router
from .profile_update import router as profile_update_router
from .register import router as register_router

router = APIRouter()
router.include_router(login_router)
router.include_router(register_router)
router.include_router(profile_router)
router.include_router(profile_update_router)
