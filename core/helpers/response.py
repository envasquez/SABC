from typing import Any, Dict, Optional

from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse


def sanitize_error_message(error: Exception, generic_message: str = "An error occurred") -> str:
    """
    Sanitize error messages to prevent information disclosure.
    Logs the full error but returns a generic message to users.
    """
    from core.helpers.logging import get_logger

    logger = get_logger("error_handler")
    logger.error(f"Error occurred: {str(error)}", exc_info=True)
    return generic_message


def error_redirect(path: str, message: str, status_code: int = 302) -> RedirectResponse:
    return RedirectResponse(f"{path}?error={message}", status_code=status_code)


def success_redirect(path: str, message: str, status_code: int = 302) -> RedirectResponse:
    return RedirectResponse(f"{path}?success={message}", status_code=status_code)


def json_error(message: str, status_code: int = 400) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status_code)


def json_success(
    data: Optional[Dict[str, Any]] = None, message: Optional[str] = None, status_code: int = 200
) -> JSONResponse:
    response: Dict[str, Any] = {"success": True}
    if data is not None:
        response["data"] = data
    if message:
        response["message"] = message
    return JSONResponse(response, status_code=status_code)


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request."""
    return request.client.host if request.client else "unknown"


def set_user_session(request: Request, user_id: int) -> None:
    """
    Set user session safely (clears old session first to prevent fixation).

    Args:
        request: FastAPI request object
        user_id: User ID to set in session
    """
    request.session.clear()
    request.session["user_id"] = user_id
