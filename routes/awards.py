from fastapi import APIRouter, Depends, Request

from core.deps import render
from core.providers import get_awards_data

router = APIRouter()


@router.get("/awards")
@router.get("/awards/{year}")
async def awards(request: Request, data=Depends(get_awards_data)):
    data["heavy_stringer"] = data["heavy_stringer"][0] if data["heavy_stringer"] else None
    data["big_bass"] = data["big_bass"][0] if data["big_bass"] else None
    return render("awards.html", request, **data)
