from fastapi import APIRouter
from fastapi.responses import Response

router = APIRouter()


@router.get("/favicon.ico")
@router.get("/apple-touch-icon{path:path}.png")
def icons() -> Response:
    return Response(open("static/favicon.svg").read(), media_type="image/svg+xml")
