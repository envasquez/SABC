from fastapi import APIRouter, Depends, HTTPException, Request

from core.deps import render
from core.providers import get_tournament_data

router = APIRouter()


@router.get("/tournaments/{tournament_id}")
async def tournament_results(request: Request, data=Depends(get_tournament_data)):
    if not data:
        raise HTTPException(status_code=404, detail="Tournament not found")

    return render("tournament_results.html", request, **data)
