from fastapi import APIRouter

from routes.admin.polls.create_poll import router as create_router
from routes.admin.polls.delete_poll import router as delete_router
from routes.admin.polls.edit_poll_form import router as edit_form_router
from routes.admin.polls.edit_poll_save import router as edit_save_router

router = APIRouter()

router.include_router(create_router)
router.include_router(edit_form_router)
router.include_router(edit_save_router)
router.include_router(delete_router)
