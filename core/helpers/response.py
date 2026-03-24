from typing import Any, Dict, Optional
from urllib.parse import quote

from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse


def is_safe_redirect_url(url: str) -> bool:
    """
    Validate that a URL is safe for redirection.

    Prevents open redirect attacks by ensuring the URL is a relative path
    that won't redirect to an external site.

    Args:
        url: The URL to validate

    Returns:
        True if the URL is safe for redirection, False otherwise

    Safe URLs:
        - Must start with "/"
        - Must not start with "//" (protocol-relative URLs)
        - Must not contain "://" (absolute URLs with schemes)

    Examples:
        >>> is_safe_redirect_url("/admin/events")
        True
        >>> is_safe_redirect_url("/profile?tab=settings")
        True
        >>> is_safe_redirect_url("//evil.com/path")
        False
        >>> is_safe_redirect_url("https://evil.com/path")
        False
        >>> is_safe_redirect_url("javascript:alert(1)")
        False
    """
    if not url or not isinstance(url, str):
        return False

    url = url.strip()

    # Must start with /
    if not url.startswith("/"):
        return False

    # Must not be a protocol-relative URL (//example.com)
    if url.startswith("//"):
        return False

    # Must not contain a scheme (http://, https://, javascript:, etc.)
    if "://" in url:
        return False

    return True


def get_safe_redirect_url(url: str, default: str = "/") -> str:
    """
    Get a safe redirect URL, falling back to default if the URL is unsafe.

    Args:
        url: The URL to validate
        default: The fallback URL if validation fails (must be a safe URL)

    Returns:
        The original URL if safe, otherwise the default URL
    """
    if is_safe_redirect_url(url):
        return url
    return default


def sanitize_error_message(error: Exception, generic_message: str = "An error occurred") -> str:
    """
    Sanitize error messages to prevent information disclosure.
    Logs the full error but returns a generic message to users.
    """
    from core.helpers.logging import get_logger

    logger = get_logger("error_handler")
    logger.error(f"Error occurred: {str(error)}", exc_info=True)
    return generic_message


def error_redirect(path: str, message: str, status_code: int = 303) -> RedirectResponse:
    """
    Redirect with error message (typically after failed form submission).

    Uses 303 See Other by default (POST-Redirect-GET pattern).
    Use 302 for GET-to-GET redirects if needed.

    Args:
        path: Path to redirect to
        message: Error message to display (will be URL-encoded)
        status_code: HTTP status code for redirect

    Returns:
        RedirectResponse with encoded error message
    """
    encoded_message = quote(message)
    return RedirectResponse(f"{path}?error={encoded_message}", status_code=status_code)


def success_redirect(path: str, message: str, status_code: int = 303) -> RedirectResponse:
    """
    Redirect with success message (typically after successful form submission).

    Uses 303 See Other by default (POST-Redirect-GET pattern).
    Use 302 for GET-to-GET redirects if needed.

    Args:
        path: Path to redirect to
        message: Success message to display (will be URL-encoded)
        status_code: HTTP status code for redirect

    Returns:
        RedirectResponse with encoded success message
    """
    encoded_message = quote(message)
    return RedirectResponse(f"{path}?success={encoded_message}", status_code=status_code)


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
