from fastapi import APIRouter

from routes.password_reset.request_reset import router as request_reset_router
from routes.password_reset.reset_password import router as reset_password_router

router = APIRouter()

router.include_router(request_reset_router)
router.include_router(reset_password_router)
