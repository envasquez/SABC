"""Account deletion logic for profile."""

from fastapi import Request
from fastapi.responses import RedirectResponse

from core.db_schema import Angler, get_session
from core.helpers.logging import SecurityEvent, get_logger, log_security_event
from routes.dependencies import u

logger = get_logger("auth.profile_update.delete")


async def delete_account(request: Request, confirm: str) -> RedirectResponse:
    """Handle account self-deletion."""
    if not (user := u(request)):
        return RedirectResponse("/login")

    if confirm != "DELETE":
        return RedirectResponse(
            "/profile?error=Confirmation text must be exactly 'DELETE'", status_code=302
        )

    try:
        user_id = user["id"]
        user_email = user.get("email", "unknown")

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

        return RedirectResponse("/?success=Account deleted successfully", status_code=302)

    except Exception as e:
        logger.error(
            "Account deletion error", extra={"user_id": user["id"], "error": str(e)}, exc_info=True
        )
        return RedirectResponse("/profile?error=Failed to delete account", status_code=302)
