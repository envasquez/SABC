from fastapi import APIRouter

from routes.voting.list_polls import router as list_polls_router
from routes.voting.vote_poll import router as vote_poll_router

router = APIRouter()

router.include_router(list_polls_router)
router.include_router(vote_poll_router)
