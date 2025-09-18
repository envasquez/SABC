from fastapi import APIRouter, Depends, Request

from core.deps import render
from core.providers import get_tournament_data
from routes.dependencies import templates

router = APIRouter()


@router.get("/tournaments/{tournament_id}")
async def tournament_results(request: Request, data=Depends(get_tournament_data)):
    if not data:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

    return render("tournament_results.html", request, **data)
