from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from core.helpers.auth import require_admin
from routes.admin.events.update_errors import handle_update_error
from routes.admin.events.update_helpers import (
    prepare_event_params,
    update_event_record,
    update_poll_closing_date,
    update_tournament_record,
)
from routes.dependencies import validate_event_data

router = APIRouter()


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
):
    _user = require_admin(request)
    try:
        validation = validate_event_data(
            date, name, event_type, start_time, weigh_in_time, entry_fee, lake_name
        )
        if validation["errors"]:
            error_msg = "; ".join(validation["errors"])
            return RedirectResponse(
                f"/admin/events?error=Validation failed: {error_msg}", status_code=302
            )
        event_params, tournament_params = prepare_event_params(
            event_id,
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
        from core.db_schema import get_session

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

            # Context manager will commit automatically on successful exit
        if event_type == "sabc_tournament":
            update_poll_closing_date(event_id, poll_closes_date)
        return RedirectResponse("/admin/events?success=Event updated successfully", status_code=302)
    except Exception as e:
        return handle_update_error(e, date)
