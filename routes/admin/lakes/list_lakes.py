from typing import Any, Dict, List

from fastapi import APIRouter, Request

from core.db_schema import Lake, Ramp, get_session
from core.helpers.auth import require_admin
from core.helpers.response import error_redirect
from routes.dependencies import templates

router = APIRouter()


@router.get("/admin/lakes")
async def admin_lakes(request: Request):
    user = require_admin(request)
    with get_session() as session:
        lake_objs = session.query(Lake).order_by(Lake.display_name).all()
        lakes = [
            {
                "id": lake.id,
                "yaml_key": lake.yaml_key,
                "display_name": lake.display_name,
                "google_maps_iframe": lake.google_maps_iframe,
            }
            for lake in lake_objs
        ]
    return templates.TemplateResponse(
        "admin/lakes.html", {"request": request, "user": user, "lakes": lakes}
    )


@router.get("/admin/lakes/{lake_id}/edit")
async def edit_lake_page(request: Request, lake_id: int):
    user = require_admin(request)
    with get_session() as session:
        lake_obj = session.query(Lake).filter(Lake.id == lake_id).first()
        if not lake_obj:
            return error_redirect("/admin/lakes", "Lake not found")

        ramp_objs = session.query(Ramp).filter(Ramp.lake_id == lake_id).order_by(Ramp.name).all()

        lake: Dict[str, Any] = {
            "id": lake_obj.id,
            "yaml_key": lake_obj.yaml_key,
            "display_name": lake_obj.display_name,
            "google_maps_iframe": lake_obj.google_maps_iframe,
        }

        ramps: List[Dict[str, Any]] = [
            {
                "id": ramp.id,
                "name": ramp.name,
                "google_maps_iframe": ramp.google_maps_iframe,
            }
            for ramp in ramp_objs
        ]

    return templates.TemplateResponse(
        "admin/edit_lake.html",
        {
            "request": request,
            "user": user,
            "lake": lake,
            "ramps": ramps,
        },
    )
