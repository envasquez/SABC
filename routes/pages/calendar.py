import json
from datetime import date, datetime

from fastapi import APIRouter, Request
from fastapi.responses import Response

from core.helpers.auth import get_user_optional
from core.helpers.timezone import now_local
from routes.dependencies import templates
from routes.pages.calendar_data import get_year_calendar_data

router = APIRouter()


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime objects."""

    def default(self, obj: object) -> str:
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)  # type: ignore[return-value]


@router.get("/calendar")
async def calendar_page(request: Request) -> Response:
    """Display calendar page with current and next year events."""
    user = get_user_optional(request)
    current_year = now_local().year
    next_year = current_year + 1

    # Get calendar data for both years
    current_calendar_data, current_event_details, current_event_types = get_year_calendar_data(
        current_year
    )
    next_calendar_data, next_event_details, next_event_types = get_year_calendar_data(next_year)

    # Combine event types from both years
    all_event_types = current_event_types | next_event_types

    return templates.TemplateResponse(
        "calendar.html",
        {
            "request": request,
            "user": user,
            "current_year": current_year,
            "next_year": next_year,
            "current_calendar_data": current_calendar_data,
            "current_event_details_json": json.dumps(current_event_details, cls=DateTimeEncoder),
            "next_calendar_data": next_calendar_data,
            "next_event_details_json": json.dumps(next_event_details, cls=DateTimeEncoder),
            "event_types_present": all_event_types,
        },
    )
