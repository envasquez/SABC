from fastapi import APIRouter, Request

from core.helpers.auth import require_admin
from core.helpers.response import error_redirect
from routes.dependencies import db, templates

router = APIRouter()


@router.get("/admin/lakes")
async def admin_lakes(request: Request):
    user = require_admin(request)
    lakes = db(
        "SELECT id, yaml_key, display_name, google_maps_iframe FROM lakes ORDER BY display_name"
    )
    return templates.TemplateResponse(
        "admin/lakes.html", {"request": request, "user": user, "lakes": lakes}
    )


@router.get("/admin/lakes/{lake_id}/edit")
async def edit_lake_page(request: Request, lake_id: int):
    user = require_admin(request)
    lake = db(
        "SELECT id, yaml_key, display_name, google_maps_iframe FROM lakes WHERE id = :id",
        {"id": lake_id},
    )
    if not lake:
        return error_redirect("/admin/lakes", "Lake not found")
    ramps = db(
        "SELECT id, name, google_maps_iframe FROM ramps WHERE lake_id = :lake_id ORDER BY name",
        {"lake_id": lake_id},
    )
    return templates.TemplateResponse(
        "admin/edit_lake.html",
        {
            "request": request,
            "user": user,
            "lake": lake[0],
            "ramps": ramps,
        },
    )
