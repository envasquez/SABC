from typing import TYPE_CHECKING

from fastapi.responses import JSONResponse, RedirectResponse

if TYPE_CHECKING:
    pass


def error_redirect(path, message, status_code=302):
    return RedirectResponse(f"{path}?error={message}", status_code=status_code)


def success_redirect(path, message, status_code=302):
    return RedirectResponse(f"{path}?success={message}", status_code=status_code)


def json_error(message, status_code=400):
    return JSONResponse({"error": message}, status_code=status_code)


def json_success(data=None, message=None, status_code=200):
    response = {"success": True}
    if data is not None:
        response["data"] = data
    if message:
        response["message"] = message
    return JSONResponse(response, status_code=status_code)


def render_template(templates, name, request, user, **context):
    return templates.TemplateResponse(name, {"request": request, "user": user, **context})
