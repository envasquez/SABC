from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import SQLAlchemyError

from core.db_schema import Ramp, get_session
from core.helpers.auth import require_admin
from core.helpers.response import error_redirect
from core.helpers.sanitize import sanitize_iframe

router = APIRouter()


@router.post("/admin/lakes/{lake_id}/ramps")
async def create_ramp(
    request: Request,
    lake_id: int,
    name: str = Form(...),
    google_maps_iframe: str = Form(""),
) -> RedirectResponse:
    _user = require_admin(request)
    try:
        with get_session() as session:
            ramp = Ramp(
                lake_id=lake_id,
                name=name.strip(),
                google_maps_iframe=sanitize_iframe(google_maps_iframe),
            )
            session.add(ramp)
        return RedirectResponse(
            f"/admin/lakes/{lake_id}/edit?success=Ramp added successfully", status_code=303
        )
    except SQLAlchemyError:
        return error_redirect(f"/admin/lakes/{lake_id}/edit", "Failed to add ramp")


@router.post("/admin/ramps/{ramp_id}/update")
async def update_ramp(
    request: Request,
    ramp_id: int,
    name: str = Form(...),
    google_maps_iframe: str = Form(""),
) -> RedirectResponse:
    _user = require_admin(request)
    lake_id: int | None = None
    try:
        with get_session() as session:
            ramp = session.query(Ramp).filter(Ramp.id == ramp_id).first()
            if not ramp:
                return error_redirect("/admin/lakes", "Ramp not found")

            lake_id = ramp.lake_id
            ramp.name = name.strip()
            ramp.google_maps_iframe = sanitize_iframe(google_maps_iframe)

        return RedirectResponse(
            f"/admin/lakes/{lake_id}/edit?success=Ramp updated successfully", status_code=303
        )
    except SQLAlchemyError:
        redirect_path = f"/admin/lakes/{lake_id}/edit" if lake_id else "/admin/lakes"
        return error_redirect(redirect_path, "Failed to update ramp")
