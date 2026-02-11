from datetime import datetime

from fastapi import Request
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from core.db_schema import Poll, get_session
from core.helpers.auth import require_admin
from core.helpers.forms import get_form_string
from core.helpers.logging import get_logger
from core.helpers.response import error_redirect
from core.helpers.timezone import make_aware
from routes.admin.polls.create_poll.helpers import (
    generate_description,
    generate_poll_title,
    generate_starts_at,
    validate_and_get_event,
)
from routes.admin.polls.create_poll.options import (
    create_generic_poll_options,
    create_other_poll_options,
    create_tournament_location_options,
)

logger = get_logger("admin.polls.create")


async def create_poll(request: Request) -> RedirectResponse:
    user = require_admin(request)

    # Initialize variables for error logging
    event_id = None
    poll_type = None
    poll_id = None

    try:
        form_data = await request.form()

        event_id_raw = get_form_string(form_data, "event_id")
        event_id = int(event_id_raw) if event_id_raw else None
        poll_type = get_form_string(form_data, "poll_type")
        title = get_form_string(form_data, "title")
        description = get_form_string(form_data, "description")
        closes_at = get_form_string(form_data, "closes_at")
        starts_at = get_form_string(form_data, "starts_at")

        # Validate input
        if not poll_type:
            return error_redirect("/admin/events", "Poll type is required")

        if not closes_at or not starts_at:
            return error_redirect("/admin/events", "Poll start and end times are required")

        event, error_response = validate_and_get_event(poll_type, event_id)
        if error_response:
            return error_response

        title = generate_poll_title(poll_type, title, event)
        starts_at_str = generate_starts_at(starts_at, event)
        description = generate_description(description, event)

        # Parse datetime strings to datetime objects - interpret as Central Time (club timezone)
        starts_at_dt = make_aware(datetime.fromisoformat(starts_at_str))
        closes_at_dt = make_aware(datetime.fromisoformat(closes_at))

        # Create poll in database
        with get_session() as session:
            new_poll = Poll(
                title=title,
                description=description,
                poll_type=poll_type,
                event_id=event_id if event_id else None,
                created_by=user["id"],
                starts_at=starts_at_dt,
                closes_at=closes_at_dt,
            )
            session.add(new_poll)
            session.flush()  # Get the poll_id before committing
            poll_id = new_poll.id

        # Create poll options based on type
        try:
            if poll_type == "tournament_location":
                create_tournament_location_options(poll_id, form_data, event)  # type: ignore[arg-type]
            elif poll_type == "generic":
                create_generic_poll_options(poll_id, form_data)
            else:
                create_other_poll_options(poll_id, form_data)
        except ValueError as e:
            logger.warning(
                "Invalid poll options",
                extra={
                    "admin_user_id": user.get("id"),
                    "poll_id": poll_id,
                    "error": str(e),
                },
            )
            return error_redirect("/admin/events", f"Invalid poll options: {str(e)}")

        logger.info(
            "Poll created successfully",
            extra={
                "admin_user_id": user.get("id"),
                "poll_id": poll_id,
                "event_id": event_id,
                "poll_type": poll_type,
            },
        )

        return RedirectResponse(
            f"/admin/polls/{poll_id}/edit?success=Poll created successfully", status_code=302
        )

    except IntegrityError as e:
        logger.error(
            "Database integrity error creating poll",
            extra={
                "admin_user_id": user.get("id"),
                "event_id": event_id,
                "poll_type": poll_type,
                "error": str(e),
            },
            exc_info=True,
        )
        return error_redirect(
            "/admin/events", "A poll already exists for this event or invalid data provided"
        )

    except SQLAlchemyError as e:
        logger.error(
            "Database error creating poll",
            extra={
                "admin_user_id": user.get("id"),
                "event_id": event_id,
                "poll_type": poll_type,
                "error": str(e),
            },
            exc_info=True,
        )
        return error_redirect("/admin/events", "Database error occurred. Please try again.")

    except ValueError as e:
        logger.warning(
            "Invalid input data for poll creation",
            extra={
                "admin_user_id": user.get("id"),
                "event_id": event_id,
                "poll_type": poll_type,
                "error": str(e),
            },
        )
        return error_redirect("/admin/events", f"Invalid data: {str(e)}")

    except Exception as e:
        logger.critical(
            "Unexpected error creating poll",
            extra={
                "admin_user_id": user.get("id"),
                "event_id": event_id,
                "poll_type": poll_type,
                "poll_id": poll_id,
                "error": str(e),
            },
            exc_info=True,
        )
        return error_redirect(
            "/admin/events", "An unexpected error occurred. Please contact support."
        )
