from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from core.helpers.auth import require_admin
from core.helpers.response import error_redirect
from routes.dependencies import db

router = APIRouter()


@router.post("/admin/lakes/{lake_id}/ramps")
async def create_ramp(
    request: Request,
    lake_id: int,
    name: str = Form(...),
    google_maps_iframe: str = Form(""),
):
    """Create a new boat ramp for a lake."""
    user = require_admin(request)

    if isinstance(user, RedirectResponse):
        return user

    try:
        db(
            """INSERT INTO ramps (lake_id, name, google_maps_iframe)
               VALUES (:lake_id, :name, :google_maps_iframe)""",
            {
                "lake_id": lake_id,
                "name": name.strip(),
                "google_maps_iframe": google_maps_iframe.strip(),
            },
        )
        return RedirectResponse(
            f"/admin/lakes/{lake_id}/edit?success=Ramp added successfully", status_code=302
        )
    except Exception as e:
        return error_redirect(f"/admin/lakes/{lake_id}/edit", str(e))


@router.post("/admin/ramps/{ramp_id}/update")
async def update_ramp(
    request: Request,
    ramp_id: int,
    name: str = Form(...),
    google_maps_iframe: str = Form(""),
):
    """Update an existing boat ramp."""
    user = require_admin(request)

    if isinstance(user, RedirectResponse):
        return user

    try:
        # Get the lake_id for redirect
        lake_id_result = db("SELECT lake_id FROM ramps WHERE id = :id", {"id": ramp_id})
        if not lake_id_result:
            return error_redirect("/admin/lakes", "Ramp not found")

        lake_id = lake_id_result[0][0]

        # Update ramp
        db(
            """UPDATE ramps
               SET name = :name,
                   google_maps_iframe = :google_maps_iframe
               WHERE id = :id""",
            {
                "id": ramp_id,
                "name": name.strip(),
                "google_maps_iframe": google_maps_iframe.strip(),
            },
        )
        return RedirectResponse(
            f"/admin/lakes/{lake_id}/edit?success=Ramp updated successfully", status_code=302
        )
    except Exception as e:
        return error_redirect(f"/admin/lakes/{lake_id}/edit", str(e))
