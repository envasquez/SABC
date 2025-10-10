from urllib.parse import quote

import bcrypt
from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import RedirectResponse

from core.db_schema import Angler, get_session
from core.email import use_reset_token, verify_reset_token
from core.helpers.logging import SecurityEvent, get_logger, log_security_event
from core.helpers.response import error_redirect
from routes.dependencies import templates
from routes.password_reset.reset_validation import (
    ERROR_INVALID_TOKEN,
    ERROR_RESET_FAILED,
    validate_password_reset,
)

router = APIRouter()
logger = get_logger("password_reset")


@router.get("/reset-password")
async def reset_password_form(
    request: Request, token: str = Query(..., description="Password reset token")
):
    try:
        token_data = verify_reset_token(token)

        if not token_data:
            return error_redirect("/forgot-password", ERROR_INVALID_TOKEN)

        return templates.TemplateResponse(
            "auth/reset_password.html",
            {
                "request": request,
                "token": token,
                "user_name": token_data["name"],
                "expires_at": token_data["expires_at"],
            },
        )

    except Exception as e:
        logger.error(f"Error showing password reset form: {e}", exc_info=True)
        return error_redirect(
            "/forgot-password",
            "Sorry, something went wrong. Please try requesting a new password reset link.",
        )


@router.post("/reset-password")
async def process_password_reset(
    request: Request,
    token: str = Form(..., description="Password reset token"),
    password: str = Form(..., min_length=8, description="New password"),
    password_confirm: str = Form(..., description="Confirm new password"),
):
    try:
        error_msg = validate_password_reset(password, password_confirm)
        if error_msg:
            return RedirectResponse(
                f"/reset-password?token={token}&error={quote(error_msg)}", status_code=303
            )

        token_data = verify_reset_token(token)

        if not token_data:
            return error_redirect("/forgot-password", ERROR_INVALID_TOKEN)

        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        with get_session() as session:
            angler = session.query(Angler).filter(Angler.id == token_data["user_id"]).first()
            if angler:
                angler.password_hash = password_hash

        use_reset_token(token)

        logger.info(
            f"Password successfully reset for user {token_data['user_id']} ({token_data['email']})",
            extra={
                "user_id": token_data["user_id"],
                "email": token_data["email"],
                "ip": request.client.host if request.client else "unknown",
            },
        )
        log_security_event(
            SecurityEvent.PASSWORD_RESET_COMPLETED,
            user_id=token_data["user_id"],
            user_email=token_data["email"],
            ip_address=request.client.host if request.client else "unknown",
            details={"success": True},
        )
        return RedirectResponse(
            "/login?success=Your password has been successfully reset. You can now log in with your new password.",
            status_code=302,
        )
    except Exception as e:
        logger.error(f"Error processing password reset: {e}", exc_info=True)
        return RedirectResponse(
            f"/reset-password?token={token}&error={quote(ERROR_RESET_FAILED)}", status_code=303
        )
