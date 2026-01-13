from datetime import datetime

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from core.helpers.auth import require_admin
from core.helpers.timezone import now_local
from routes.admin.events.create_db_ops import (
    create_event_record,
    create_poll_options,
    create_tournament_poll,
    create_tournament_record,
    link_tournament_to_poll,
)
from routes.admin.events.create_helpers import handle_create_error
from routes.admin.events.create_params import prepare_create_event_params
from routes.dependencies import validate_event_data

router = APIRouter()


@router.get("/admin/events/create")
async def create_event_page(request: Request):
    """Display event creation form."""
    from routes.dependencies import templates

    user = require_admin(request)
    if isinstance(user, RedirectResponse):
        return user

    # Reuse the events list template which has inline creation capability
    return templates.TemplateResponse(
        "admin/events.html",
        {
            "request": request,
            "user": user,
            "events": [],  # Empty list for create mode
            "create_mode": True,
            "current_year": now_local().year,
        },
    )


@router.post("/admin/events/create")
async def create_event(
    request: Request,
    date: str = Form(),
    name: str = Form(),
    event_type: str = Form(default="sabc_tournament"),
    description: str = Form(default=""),
    start_time: str = Form(default=""),
    weigh_in_time: str = Form(default=""),
    lake_name: str = Form(default=""),
    ramp_name: str = Form(default=""),
    entry_fee: float = Form(default=25.00),
    fish_limit: int = Form(default=5),
    aoy_points: str = Form(default="true"),
    create_poll: str = Form(default="true"),
):
    user = require_admin(request)
    try:
        validation = validate_event_data(
            date, name, event_type, start_time, weigh_in_time, entry_fee, lake_name
        )
        if validation["errors"]:
            error_msg = "; ".join(validation["errors"])
            return RedirectResponse(
                f"/admin/events?error=Validation failed: {error_msg}", status_code=302
            )
        warning_msg = ""
        if validation["warnings"]:
            warning_msg = f"&warnings={'; '.join(validation['warnings'])}"
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        event_params, tournament_params = prepare_create_event_params(
            date,
            name,
            event_type,
            description,
            start_time,
            weigh_in_time,
            lake_name,
            ramp_name,
            entry_fee,
            fish_limit,
            aoy_points,
        )
        event_id = create_event_record(event_params)
        if event_type in ["sabc_tournament", "other_tournament"]:
            create_tournament_record(event_id, tournament_params)
        if event_type == "sabc_tournament" and create_poll.lower() == "true":
            poll_id = create_tournament_poll(event_id, name, description, date_obj, user["id"])  # type: ignore[arg-type]
            create_poll_options(poll_id)
            link_tournament_to_poll(event_id, poll_id)
        return RedirectResponse(
            f"/admin/events?success=Event created successfully{warning_msg}", status_code=302
        )
    except Exception as e:
        return handle_create_error(e, date)
