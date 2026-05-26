from urllib.parse import quote

import bcrypt
from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.exc import SQLAlchemyError

from core.db_schema import Angler, get_session
from core.email import verify_reset_token
from core.email.token_queries import mark_token_used_in_session
from core.helpers.logging import SecurityEvent, get_logger, log_security_event
from core.helpers.passwords import bcrypt_gensalt
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
def reset_password_form(
    request: Request, token: str = Query(..., description="Password reset token")
) -> Response:
    try:
        token_data = verify_reset_token(token)

        if not token_data:
            return error_redirect("/forgot-password", ERROR_INVALID_TOKEN)

        # Extract query parameters for error/success messages
        error = request.query_params.get("error")
        success = request.query_params.get("success")

        return templates.TemplateResponse(
            request,
            "auth/reset_password.html",
            {
                "token": token,
                "user_name": token_data["name"],
                "expires_at": token_data["expires_at"],
                "error": error,
                "success": success,
            },
        )

    except (SQLAlchemyError, ValueError) as e:
        logger.error(f"Error showing password reset form: {e}", exc_info=True)
        return error_redirect(
            "/forgot-password",
            "Sorry, something went wrong. Please try requesting a new password reset link.",
        )


@router.post("/reset-password")
def process_password_reset(
    request: Request,
    token: str = Form(..., description="Password reset token"),
    password: str = Form(..., min_length=12, description="New password"),
    password_confirm: str = Form(..., description="Confirm new password"),
) -> RedirectResponse:
    try:
        error_msg = validate_password_reset(password, password_confirm)
        if error_msg:
            return RedirectResponse(
                f"/reset-password?token={token}&error={quote(error_msg)}", status_code=303
            )

        token_data = verify_reset_token(token)

        if not token_data:
            return error_redirect("/forgot-password", ERROR_INVALID_TOKEN)

        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt_gensalt()).decode("utf-8")

        # Mark the token used and update the password in a single transaction.
        # Either both land or neither does — a token cannot outlive its
        # password change, and concurrent requests with the same token cannot
        # both succeed (the second mark_token_used_in_session returns 0).
        with get_session() as session:
            rowcount = mark_token_used_in_session(session, token)
            if rowcount == 0:
                return error_redirect("/forgot-password", ERROR_INVALID_TOKEN)

            angler = session.query(Angler).filter(Angler.id == token_data["user_id"]).first()
            if not angler:
                return error_redirect("/forgot-password", ERROR_INVALID_TOKEN)
            angler.password_hash = password_hash
            # Bump session_version so any sessions issued before the reset
            # (e.g. an attacker's session, which is why the user is resetting)
            # are invalidated on their next request.
            angler.session_version = (angler.session_version or 1) + 1

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
            status_code=303,
        )
    except (SQLAlchemyError, ValueError) as e:
        logger.error(f"Error processing password reset: {e}", exc_info=True)
        return RedirectResponse(
            f"/reset-password?token={token}&error={quote(ERROR_RESET_FAILED)}", status_code=303
        )
