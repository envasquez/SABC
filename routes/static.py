"""Static routes for favicon and catch-all pages."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from .dependencies import *

router = APIRouter()


@router.get("/favicon.ico")
@router.get("/apple-touch-icon{path:path}.png")
async def icons():
    return Response(open("static/favicon.svg").read(), media_type="image/svg+xml")


