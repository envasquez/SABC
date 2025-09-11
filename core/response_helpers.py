"""Response helper functions to reduce repetitive response patterns."""

from typing import TYPE_CHECKING

from fastapi.responses import JSONResponse, RedirectResponse

if TYPE_CHECKING:
    pass


def error_redirect(path, message, status_code=302):
    """Create a redirect response with error message."""
    return RedirectResponse(f"{path}?error={message}", status_code=status_code)


def success_redirect(path, message, status_code=302):
    """Create a redirect response with success message."""
    return RedirectResponse(f"{path}?success={message}", status_code=status_code)


def json_error(message, status_code=400):
    """Create a JSON error response."""
    return JSONResponse({"error": message}, status_code=status_code)


def json_success(data=None, message=None, status_code=200):
    """Create a JSON success response."""
    response = {"success": True}
    if data is not None:
        response["data"] = data
    if message:
        response["message"] = message
    return JSONResponse(response, status_code=status_code)


def render_template(templates, name, request, user, **context):
    """Render template with standard context (request, user) plus additional context."""
    return templates.TemplateResponse(name, {"request": request, "user": user, **context})
