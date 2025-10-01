from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from core.helpers.auth import require_admin
from core.helpers.response import error_redirect
from routes.dependencies import db

router = APIRouter()


@router.post("/admin/lakes/create")
async def create_lake(
    request: Request,
    name: str = Form(...),
    display_name: str = Form(...),
    google_maps_embed: str = Form(""),
):
    _user = require_admin(request)
    try:
        db(
            """INSERT INTO lakes (yaml_key, display_name, google_maps_iframe)
               VALUES (:yaml_key, :display_name, :google_maps_iframe)""",
            {
                "yaml_key": name.strip().lower().replace(" ", "_"),
                "display_name": display_name.strip(),
                "google_maps_iframe": google_maps_embed.strip(),
            },
        )
        return RedirectResponse("/admin/lakes?success=Lake created successfully", status_code=302)
    except Exception as e:
        return error_redirect("/admin/lakes", str(e))


@router.post("/admin/lakes/{lake_id}/update")
async def update_lake(
    request: Request,
    lake_id: int,
    name: str = Form(...),
    display_name: str = Form(...),
    google_maps_embed: str = Form(""),
):
    _user = require_admin(request)
    try:
        db(
            """UPDATE lakes
               SET yaml_key = :yaml_key,
                   display_name = :display_name,
                   google_maps_iframe = :google_maps_iframe
               WHERE id = :id""",
            {
                "id": lake_id,
                "yaml_key": name.strip().lower().replace(" ", "_"),
                "display_name": display_name.strip(),
                "google_maps_iframe": google_maps_embed.strip(),
            },
        )
        return RedirectResponse("/admin/lakes?success=Lake updated successfully", status_code=302)
    except Exception as e:
        return error_redirect("/admin/lakes", str(e))
