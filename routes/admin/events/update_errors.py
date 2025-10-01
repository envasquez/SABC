"""Error message mapping for event updates."""

from fastapi.responses import RedirectResponse


def get_error_message(error: Exception, date: str) -> str:
    """Get user-friendly error message based on exception."""
    error_msg = str(error)

    if "UNIQUE constraint failed: events.date" in error_msg:
        return f"An event already exists on {date}. Please choose a different date."
    elif "NOT NULL constraint failed" in error_msg:
        return "Required field missing. Please fill in all required fields."
    elif "FOREIGN KEY constraint failed" in error_msg:
        return "Invalid lake or ramp selection. Please refresh the page and try again."
    else:
        return f"Failed to update event. Details: {error_msg}"


def handle_update_error(e: Exception, date: str) -> RedirectResponse:
    """Handle errors during event update."""
    error_msg = get_error_message(e, date)
    return RedirectResponse(f"/admin/events?error={error_msg}", status_code=302)
