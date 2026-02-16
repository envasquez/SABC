from typing import Optional

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from core.db_schema import Event, get_session
from core.helpers.auth import require_admin
from core.helpers.timezone import now_local
from routes.admin.events.error_handlers import handle_event_error
from routes.admin.events.param_builders import prepare_event_params
from routes.admin.events.update_helpers import (
    update_event_record,
    update_poll_closing_date,
    update_tournament_poll_id,
    update_tournament_record,
)
from routes.dependencies import templates, validate_event_data

router = APIRouter()


def _do_event_update(
    event_id: int,
    date: str,
    name: str,
    event_type: str,
    description: str,
    start_time: str,
    weigh_in_time: str,
    lake_name: str,
    ramp_name: str,
    entry_fee: float,
    fish_limit: int,
    aoy_points: str,
    poll_closes_date: str,
    is_cancelled: str,
    poll_id: Optional[str] = None,
) -> RedirectResponse:
    """Shared logic for updating an event."""
    validation = validate_event_data(
        date, name, event_type, start_time, weigh_in_time, entry_fee, lake_name
    )
    if validation["errors"]:
        error_msg = "; ".join(validation["errors"])
        return RedirectResponse(
            f"/admin/events?error=Validation failed: {error_msg}", status_code=302
        )

    event_params, tournament_params = prepare_event_params(
        date=date,
        name=name,
        event_type=event_type,
        description=description,
        start_time=start_time,
        weigh_in_time=weigh_in_time,
        lake_name=lake_name,
        ramp_name=ramp_name,
        entry_fee=entry_fee,
        fish_limit=fish_limit,
        aoy_points=aoy_points,
        event_id=event_id,
    )
    event_params["is_cancelled"] = is_cancelled.lower() == "true"

    with get_session() as session:
        rowcount = update_event_record(session, event_params)
        if rowcount == 0:
            return RedirectResponse(
                f"/admin/events?error=Event with ID {event_id} not found", status_code=302
            )

        if event_type in ["sabc_tournament", "other_tournament"]:
            tournament_rowcount = update_tournament_record(session, tournament_params)
            if tournament_rowcount == 0:
                return RedirectResponse(
                    f"/admin/events?error=Tournament record for event ID {event_id} not found",
                    status_code=302,
                )

    if event_type == "sabc_tournament":
        update_poll_closing_date(event_id, poll_closes_date)
        if poll_id:
            update_tournament_poll_id(event_id, int(poll_id))

    return RedirectResponse("/admin/events?success=Event updated successfully", status_code=302)


@router.get("/admin/events/{event_id}/edit")
async def get_edit_event(request: Request, event_id: int):
    """GET endpoint for editing an event - returns the edit form."""
    user = require_admin(request)

    with get_session() as session:
        event = session.query(Event).filter(Event.id == event_id).first()
        if not event:
            return RedirectResponse(
                f"/admin/events?error=Event with ID {event_id} not found", status_code=302
            )

    return templates.TemplateResponse(
        "admin/events.html",
        {
            "request": request,
            "user": user,
            "edit_event_id": event_id,
            "current_year": now_local().year,
        },
    )


@router.post("/admin/events/{event_id}/update")
async def update_event_by_id(
    request: Request,
    event_id: int,
    date: str = Form(),
    name: str = Form(),
    event_type: str = Form(),
    description: str = Form(default=""),
    start_time: str = Form(default=""),
    weigh_in_time: str = Form(default=""),
    lake_name: str = Form(default=""),
    ramp_name: str = Form(default=""),
    entry_fee: float = Form(default=25.00),
    fish_limit: int = Form(default=5),
    aoy_points: str = Form(default="true"),
    poll_closes_date: str = Form(default=""),
    is_cancelled: str = Form(default=""),
):
    """POST endpoint for updating an event by ID."""
    _user = require_admin(request)
    try:
        return _do_event_update(
            event_id, date, name, event_type, description, start_time,
            weigh_in_time, lake_name, ramp_name, entry_fee, fish_limit,
            aoy_points, poll_closes_date, is_cancelled
        )
    except Exception as e:
        return handle_event_error(e, date)


@router.post("/admin/events/edit")
async def edit_event(
    request: Request,
    event_id: int = Form(),
    date: str = Form(),
    name: str = Form(),
    event_type: str = Form(),
    description: str = Form(default=""),
    start_time: str = Form(default=""),
    weigh_in_time: str = Form(default=""),
    lake_name: str = Form(default=""),
    ramp_name: str = Form(default=""),
    entry_fee: float = Form(default=25.00),
    fish_limit: int = Form(default=5),
    aoy_points: str = Form(default="true"),
    poll_closes_date: str = Form(default=""),
    poll_id: str = Form(default=""),
    is_cancelled: str = Form(default=""),
):
    """POST endpoint for updating an event via form submission."""
    _user = require_admin(request)
    try:
        return _do_event_update(
            event_id, date, name, event_type, description, start_time,
            weigh_in_time, lake_name, ramp_name, entry_fee, fish_limit,
            aoy_points, poll_closes_date, is_cancelled, poll_id
        )
    except Exception as e:
        return handle_event_error(e, date)
