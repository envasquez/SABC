from fastapi import APIRouter

from routes.admin.lakes.delete_lakes import router as delete_lakes_router
from routes.admin.lakes.lake_operations import router as lake_router
from routes.admin.lakes.list_lakes import router as list_lakes_router
from routes.admin.lakes.ramp_operations import router as ramp_router

router = APIRouter()

router.include_router(list_lakes_router)
router.include_router(lake_router)
router.include_router(ramp_router)
router.include_router(delete_lakes_router)
