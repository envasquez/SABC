"""Account deletion logic for profile."""

from fastapi import Request
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from core.db_schema import Angler, get_session
from core.helpers.logging import SecurityEvent, get_logger, log_security_event
from routes.dependencies import bcrypt, get_current_user

logger = get_logger("auth.profile_update.delete")


def delete_account(request: Request, confirm: str, current_password: str) -> RedirectResponse:
    """Handle account self-deletion.

    Requires both the literal confirmation text "DELETE" and re-entry of
    the user's current password. Re-auth defends against a CSRF bypass or
    an unlocked-machine attacker turning the form into a single-click wipe.
    """
    if not (user := get_current_user(request)):
        return RedirectResponse("/login")

    if confirm != "DELETE":
        return RedirectResponse(
            "/profile?error=Confirmation text must be exactly 'DELETE'", status_code=303
        )

    if not current_password:
        return RedirectResponse(
            "/profile?error=Current password is required to delete your account",
            status_code=303,
        )

    try:
        user_id = user["id"]
        user_email = user.get("email", "unknown")

        # Verify current password before any destructive action.
        with get_session() as session:
            angler = session.query(Angler).filter(Angler.id == user_id).first()
            if not angler or not angler.password_hash:
                logger.warning(
                    "Self-delete attempted by user without password hash",
                    extra={"user_id": user_id, "user_email": user_email},
                )
                return RedirectResponse(
                    "/profile?error=Account cannot be deleted via self-service. "
                    "Please contact an administrator.",
                    status_code=303,
                )
            if not bcrypt.checkpw(
                current_password.encode("utf-8"), angler.password_hash.encode("utf-8")
            ):
                logger.warning(
                    "Self-delete failed: wrong password",
                    extra={"user_id": user_id, "user_email": user_email},
                )
                log_security_event(
                    SecurityEvent.AUTH_LOGIN_FAILURE,
                    user_id=user_id,  # type: ignore[arg-type]
                    user_email=user_email,  # type: ignore[arg-type]
                    ip_address=request.client.host if request.client else "unknown",
                    details={"context": "self_delete_reauth", "success": False},
                )
                return RedirectResponse(
                    "/profile?error=Current password is incorrect", status_code=303
                )

        logger.warning(
            "User account self-deletion", extra={"user_id": user_id, "user_email": user_email}
        )
        log_security_event(
            SecurityEvent.AUTH_ACCOUNT_DELETED,
            user_id=user_id,  # type: ignore[arg-type]
            user_email=user_email,  # type: ignore[arg-type]
            ip_address=request.client.host if request.client else "unknown",
            details={"method": "self_delete"},
        )

        with get_session() as session:
            angler = session.query(Angler).filter(Angler.id == user_id).first()
            if angler:
                session.delete(angler)
                # Context manager will commit automatically on successful exit

        request.session.clear()

        return RedirectResponse("/?success=Account deleted successfully", status_code=303)

    except IntegrityError as e:
        # Foreign key constraint error - user has related data (results, votes, etc.)
        logger.warning(
            "Account deletion failed due to existing data",
            extra={"user_id": user["id"], "error": str(e)},
        )
        return RedirectResponse(
            "/profile?error=Cannot delete account. You have tournament results, votes, or other "
            "associated data. Please contact an administrator for assistance.",
            status_code=303,
        )
    except SQLAlchemyError as e:
        logger.error(
            "Account deletion error", extra={"user_id": user["id"], "error": str(e)}, exc_info=True
        )
        return RedirectResponse("/profile?error=Failed to delete account", status_code=303)
