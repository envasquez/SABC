from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from core.db_schema import Ramp, get_session
from core.helpers.auth import require_admin
from core.helpers.response import error_redirect

router = APIRouter()


@router.post("/admin/lakes/{lake_id}/ramps")
async def create_ramp(
    request: Request,
    lake_id: int,
    name: str = Form(...),
    google_maps_iframe: str = Form(""),
):
    _user = require_admin(request)
    try:
        with get_session() as session:
            ramp = Ramp(
                lake_id=lake_id,
                name=name.strip(),
                google_maps_iframe=google_maps_iframe.strip(),
            )
            session.add(ramp)
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
    _user = require_admin(request)
    try:
        with get_session() as session:
            ramp = session.query(Ramp).filter(Ramp.id == ramp_id).first()
            if not ramp:
                return error_redirect("/admin/lakes", "Ramp not found")

            lake_id = ramp.lake_id
            ramp.name = name.strip()
            ramp.google_maps_iframe = google_maps_iframe.strip()

        return RedirectResponse(
            f"/admin/lakes/{lake_id}/edit?success=Ramp updated successfully", status_code=302
        )
    except Exception as e:
        return error_redirect(f"/admin/lakes/{lake_id}/edit", str(e))
