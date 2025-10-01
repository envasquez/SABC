from fastapi import APIRouter, Query, Request
from fastapi.responses import RedirectResponse

from routes.admin.polls.create_poll.form import create_poll_form
from routes.admin.polls.create_poll.handler import create_poll

router = APIRouter()


@router.get("/admin/polls/create")
async def get_create_poll_form(request: Request, event_id: int = Query(None)):
    return await create_poll_form(request, event_id)


@router.post("/admin/polls/create")
async def post_create_poll(request: Request) -> RedirectResponse:
    return await create_poll(request)


__all__ = ["router", "create_poll_form", "create_poll"]
