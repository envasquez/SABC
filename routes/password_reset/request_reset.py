from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func

from core.db_schema import Angler, get_session
from core.email import create_password_reset_token, send_password_reset_email
from core.helpers.logging import get_logger
from core.helpers.response import error_redirect
from routes.dependencies import templates
from routes.password_reset.request_logging import (
    log_reset_email_failed,
    log_reset_rate_limited,
    log_reset_success,
    log_reset_user_not_found,
)

router = APIRouter()
logger = get_logger("password_reset")


@router.get("/forgot-password")
async def forgot_password_form(request: Request):
    return templates.TemplateResponse("auth/forgot_password.html", {"request": request})


@router.post("/forgot-password")
async def request_password_reset(
    request: Request, email: str = Form(..., description="Your email address")
):
    try:
        email = email.lower().strip()
        if not email:
            return error_redirect("/forgot-password", "Please enter your email address.")

        ip = request.client.host if request.client else "unknown"

        with get_session() as session:
            user = session.query(Angler).filter(func.lower(Angler.email) == email.lower()).first()

            if user:
                # Extract data while in session
                user_id = user.id
                name = user.name
                user_email = user.email

                token = create_password_reset_token(user_id, user_email)

                if token:
                    email_sent = send_password_reset_email(user_email, name, token)
                    if email_sent:
                        log_reset_success(user_id, user_email, ip)
                    else:
                        log_reset_email_failed(user_id, user_email, ip)
                else:
                    log_reset_rate_limited(user_id, user_email, ip)
            else:
                log_reset_user_not_found(email, ip)

        return RedirectResponse(
            "/forgot-password?success=If that email is in our system, we've sent you a password reset link. Please check your email (and spam folder).",
            status_code=302,
        )
    except Exception as e:
        logger.error(f"Error processing password reset request: {e}", exc_info=True)
        return error_redirect(
            "/forgot-password",
            "Sorry, something went wrong. Please try again or contact an administrator.",
        )


@router.get("/reset-password/help")
async def password_reset_help(request: Request):
    return templates.TemplateResponse("auth/password_reset_help.html", {"request": request})
