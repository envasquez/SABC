"""
Password reset routes for SABC.
Simple, user-friendly password reset flow for non-tech-savvy members.
"""

import bcrypt
from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import RedirectResponse

from core.database import db
from core.email_service import (
    create_password_reset_token,
    send_password_reset_email,
    use_reset_token,
    verify_reset_token,
)
from core.helpers.logging_config import SecurityEvent, get_logger, log_security_event
from core.helpers.response import error_redirect
from routes.dependencies import templates

router = APIRouter()
logger = get_logger("password_reset")


@router.get("/forgot-password")
async def forgot_password_form(request: Request):
    """Show the forgot password form - simple and clear for older users."""
    return templates.TemplateResponse("auth/forgot_password.html", {"request": request})


@router.post("/forgot-password")
async def request_password_reset(
    request: Request, email: str = Form(..., description="Your email address")
):
    """
    Process password reset request.
    Always shows success message to prevent email enumeration attacks.
    """
    try:
        email = email.lower().strip()
        if not email:
            return error_redirect("/forgot-password", "Please enter your email address.")

        # Look up user by email
        user = db(
            "SELECT id, name, email FROM anglers WHERE LOWER(email) = LOWER(:email)",
            {"email": email},
        )

        if user:
            user_data = user[0]
            user_id = user_data[0]
            name = user_data[1]
            user_email = user_data[2]

            # Create reset token
            token = create_password_reset_token(user_id, user_email)

            if token:
                # Send email
                email_sent = send_password_reset_email(user_email, name, token)

                if email_sent:
                    logger.info(
                        f"Password reset requested and email sent to {user_email}",
                        extra={
                            "user_id": user_id,
                            "email": user_email,
                            "ip": request.client.host if request.client else "unknown",
                        },
                    )
                    log_security_event(
                        SecurityEvent.PASSWORD_RESET_REQUESTED,
                        user_id=user_id,
                        user_email=user_email,
                        ip_address=request.client.host if request.client else "unknown",
                        details={"success": True},
                    )
                else:
                    logger.error(f"Failed to send password reset email to {user_email}")
                    log_security_event(
                        SecurityEvent.PASSWORD_RESET_REQUESTED,
                        user_id=user_id,
                        user_email=user_email,
                        ip_address=request.client.host if request.client else "unknown",
                        details={"success": False, "error": "email_send_failed"},
                    )
            else:
                logger.warning(f"Rate limited password reset request for {user_email}")
                log_security_event(
                    SecurityEvent.PASSWORD_RESET_REQUESTED,
                    user_id=user_id,
                    user_email=user_email,
                    ip_address=request.client.host if request.client else "unknown",
                    details={"success": False, "error": "rate_limited"},
                )
        else:
            # User not found - log but don't reveal this to prevent email enumeration
            logger.info(f"Password reset requested for non-existent email: {email}")
            log_security_event(
                SecurityEvent.PASSWORD_RESET_REQUESTED,
                user_id=None,
                user_email=email,
                ip_address=request.client.host if request.client else "unknown",
                details={"success": False, "error": "user_not_found"},
            )

        # Always show success message (security best practice)
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


@router.get("/reset-password")
async def reset_password_form(
    request: Request, token: str = Query(..., description="Password reset token")
):
    """Show the password reset form if token is valid."""
    try:
        # Verify the token
        token_data = verify_reset_token(token)

        if not token_data:
            return error_redirect(
                "/forgot-password",
                "This password reset link is invalid or has expired. Please request a new one.",
            )

        # Show the reset form
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
    """Process the new password and complete the reset."""
    try:
        # Basic validation
        if not password or len(password) < 8:
            return error_redirect(
                f"/reset-password?token={token}", "Password must be at least 8 characters long."
            )

        if password != password_confirm:
            return error_redirect(
                f"/reset-password?token={token}", "Passwords do not match. Please try again."
            )

        # Verify the token
        token_data = verify_reset_token(token)

        if not token_data:
            return error_redirect(
                "/forgot-password",
                "This password reset link is invalid or has expired. Please request a new one.",
            )

        # Hash the new password
        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        # Update the user's password
        db(
            "UPDATE anglers SET password = :password WHERE id = :user_id",
            {"password": password_hash, "user_id": token_data["user_id"]},
        )

        # Mark the token as used
        use_reset_token(token)

        # Log the successful password reset
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

        # Redirect to login with success message
        return RedirectResponse(
            "/login?success=Your password has been successfully reset. You can now log in with your new password.",
            status_code=302,
        )

    except Exception as e:
        logger.error(f"Error processing password reset: {e}", exc_info=True)
        return error_redirect(
            f"/reset-password?token={token}",
            "Sorry, something went wrong while resetting your password. Please try again.",
        )


@router.get("/reset-password/help")
async def password_reset_help(request: Request):
    """Help page for users who need assistance with password reset."""
    return templates.TemplateResponse("auth/password_reset_help.html", {"request": request})
