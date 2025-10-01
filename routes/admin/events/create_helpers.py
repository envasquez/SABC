"""Helper functions for event creation."""

from fastapi.responses import RedirectResponse


def handle_create_error(e: Exception, date: str) -> RedirectResponse:
    """Handle errors during event creation."""
    error_msg = str(e)

    if "UNIQUE constraint failed: events.date" in error_msg:
        error_msg = f"An event already exists on {date}. Please choose a different date or edit the existing event."
    elif "NOT NULL constraint failed" in error_msg:
        error_msg = "Required field missing. Please fill in all required fields."
    elif "FOREIGN KEY constraint failed" in error_msg:
        error_msg = "Invalid lake or ramp selection. Please refresh the page and try again."
    else:
        error_msg = f"Failed to create event. Details: {error_msg}"

    return RedirectResponse(f"/admin/events?error={error_msg}", status_code=302)
