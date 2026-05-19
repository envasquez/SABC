"""Shared error handling for event create/update operations."""

from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError


def get_error_message(error: Exception, date: str, operation: str = "update") -> str:
    """Convert database exceptions to user-friendly error messages."""
    if isinstance(error, IntegrityError):
        # IntegrityError covers unique, NOT NULL and FOREIGN KEY violations on
        # both SQLite and PostgreSQL. The events table has exactly one unique
        # constraint (events_date_key on `date`), so distinguish the three
        # cases using dialect-tolerant keywords from the underlying driver.
        orig_msg = str(error.orig).lower()
        if "null" in orig_msg:
            return "Required field missing. Please fill in all required fields."
        if "foreign key" in orig_msg:
            return "Invalid lake or ramp selection. Please refresh the page and try again."
        # Any remaining IntegrityError is a unique-constraint violation, which
        # for the events table can only be a duplicate date.
        return f"An event already exists on {date}. Please choose a different date."
    return f"Failed to {operation} event. Please try again."


def handle_event_error(e: Exception, date: str, operation: str = "update") -> RedirectResponse:
    """Handle errors during event create/update and redirect with error message."""
    error_msg = get_error_message(e, date, operation)
    return RedirectResponse(f"/admin/events?error={error_msg}", status_code=303)
