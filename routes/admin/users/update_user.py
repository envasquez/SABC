"""POST /admin/users/{user_id}/edit — admin user update.

Collapsed from the former `update_user/` subpackage (5 files: __init__.py,
save.py, prepare.py, validation.py, logging.py) so this route lives next to
its siblings (create_user.py, delete_user.py, edit_user.py). The audit
flagged the multi-file split as premature decomposition: prepare.py was
18 lines for one helper, logging.py was 4 thin functions used once each,
and following the request flow required opening 5 tabs.
"""

from datetime import date
from typing import Any, Dict, Optional, Tuple

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from core.db_schema import Angler, OfficerPosition, get_session
from core.helpers.auth import require_admin
from core.helpers.logging import SecurityEvent, get_logger, log_security_event
from core.helpers.response import error_redirect
from core.helpers.timezone import now_local
from routes.admin.users.email_helpers import generate_guest_email
from routes.auth.validation import validate_phone_number

router = APIRouter()
logger = get_logger("admin.users.update")

# Fields captured for before/after diffs in security logs.
_TRACKED_FIELDS = ("name", "email", "phone", "member", "is_admin")


# ----------------------------- helpers --------------------------------------


def validate_and_prepare_email(email: str, name: str, member: bool, user_id: int) -> Optional[str]:
    """Lowercase the supplied email; if empty for a non-member, auto-generate
    a placeholder guest email so admin lookups still resolve. Returns None
    only when the caller is a member and supplied no email (an invalid state
    that the caller should reject upstream)."""
    email_cleaned = email.strip() if email else ""
    if email_cleaned:
        return email_cleaned.lower()
    if not member:
        generated = generate_guest_email(name.strip(), user_id)
        if generated:
            logger.info(
                "Auto-generated email for guest user",
                extra={
                    "user_id": user_id,
                    "user_name": name,
                    "generated_email": generated,
                },
            )
        return generated
    return None


def update_officer_positions(
    session: Session, user_id: int, officer_positions: list[str], current_year: int
) -> None:
    """Replace this user's officer positions for ``current_year`` within the
    caller's session. Caller manages commit/rollback."""
    session.query(OfficerPosition).filter(
        OfficerPosition.angler_id == user_id,
        OfficerPosition.year == current_year,
    ).delete()
    for position in officer_positions or []:
        position_cleaned = position.strip()
        if position_cleaned:
            session.add(
                OfficerPosition(angler_id=user_id, position=position_cleaned, year=current_year)
            )


def _prepare_update_data(
    user_id: int, name: str, email: str, phone: str, member: bool, is_admin: bool
) -> Dict[str, Any]:
    """Normalize form fields into a single dict and resolve the final email."""
    return {
        "id": user_id,
        "name": name.strip(),
        "email": validate_and_prepare_email(email, name, member, user_id),
        "phone": phone.strip() if phone else None,
        "member": member,
        "is_admin": is_admin,
    }


def _before_after_dict(values: Tuple[Any, ...]) -> Dict[str, Any]:
    return dict(zip(_TRACKED_FIELDS, values))


# ----------------------------- route ----------------------------------------


@router.post("/admin/users/{user_id}/edit")
async def update_user(
    request: Request,
    user_id: int,
    name: str = Form(...),
    email: str = Form(""),
    phone: str = Form(""),
    member: bool = Form(False),
    is_admin: bool = Form(False),
    officer_positions: list[str] = Form([]),
    dues_paid_through: Optional[str] = Form(None),
) -> RedirectResponse:
    """Handle user update form submission."""
    admin_user = require_admin(request)
    update_params: Dict[str, Any] = {}
    try:
        with get_session() as session:
            angler = session.query(Angler).filter(Angler.id == user_id).first()
            if not angler:
                return error_redirect("/admin/users", f"User {user_id} not found")

            before = (angler.name, angler.email, angler.phone, angler.member, angler.is_admin)

            # Validate and format phone number
            formatted_phone = None
            if phone:
                is_valid, formatted_phone, error_msg = validate_phone_number(phone)
                if not is_valid:
                    return error_redirect(
                        f"/admin/users/{user_id}/edit", error_msg or "Invalid phone number"
                    )

            update_params = _prepare_update_data(
                user_id, name, email, formatted_phone or "", member, is_admin
            )
            logger.info(
                "Admin user update initiated",
                extra={
                    "admin_user_id": admin_user.get("id"),
                    "target_user_id": user_id,
                    "changes": update_params,
                    "before": _before_after_dict(before),
                },
            )

            angler.name = update_params["name"]
            angler.email = update_params["email"]
            angler.phone = update_params["phone"]
            angler.member = update_params["member"]
            angler.is_admin = update_params["is_admin"]

            # dues_paid_through tri-state semantics:
            #   None         → field absent from form, keep existing value
            #   ""           → user cleared the field, set to NULL
            #   "YYYY-MM-DD" → parse and assign
            if dues_paid_through is not None:
                if dues_paid_through:
                    try:
                        angler.dues_paid_through = date.fromisoformat(dues_paid_through)
                    except ValueError:
                        pass  # Invalid date format, keep existing value
                else:
                    angler.dues_paid_through = None

            update_officer_positions(session, user_id, officer_positions, now_local().year)

            try:
                session.flush()
                session.refresh(angler)
                after = (angler.name, angler.email, angler.phone, angler.member, angler.is_admin)
            except SQLAlchemyError as flush_error:
                logger.error(
                    "User update exception",
                    extra={
                        "admin_user_id": admin_user.get("id"),
                        "target_user_id": user_id,
                        "error": str(flush_error),
                        "update_params": update_params,
                    },
                    exc_info=True,
                )
                session.rollback()
                raise

        if after != before:
            log_security_event(
                SecurityEvent.ADMIN_USER_UPDATE,
                user_id=admin_user.get("id"),
                user_email=admin_user.get("email"),
                ip_address=request.client.host if request.client else "unknown",
                details={
                    "target_user_id": user_id,
                    "changes": update_params,
                    "before": _before_after_dict(before),
                    "after": _before_after_dict(after),
                },
            )
            logger.info(
                "User updated successfully",
                extra={
                    "admin_user_id": admin_user.get("id"),
                    "target_user_id": user_id,
                    "after": _before_after_dict(after),
                },
            )
            return RedirectResponse(
                "/admin/users?success=User updated and verified", status_code=303
            )
        logger.warning(
            "User update failed - no changes detected",
            extra={
                "admin_user_id": admin_user.get("id"),
                "target_user_id": user_id,
                "update_params": update_params,
            },
        )
        return RedirectResponse(
            "/admin/users?error=Update failed - no changes saved", status_code=303
        )

    except IntegrityError as e:
        # The anglers table has exactly one unique constraint (anglers_email_key),
        # so an IntegrityError while updating a user means a duplicate email.
        # IntegrityError is raised on both SQLite and PostgreSQL.
        logger.error(
            "User update IntegrityError",
            extra={
                "admin_user_id": admin_user.get("id"),
                "target_user_id": user_id,
                "error": str(e),
                "update_params": update_params,
            },
            exc_info=True,
        )
        return error_redirect("/admin/users", "This email address is already in use.")
    except (SQLAlchemyError, ValueError) as e:
        logger.error(
            "User update exception",
            extra={
                "admin_user_id": admin_user.get("id"),
                "target_user_id": user_id,
                "error": str(e),
                "update_params": update_params,
            },
            exc_info=True,
        )
        return error_redirect("/admin/users", "Failed to update user")


__all__ = ["router", "update_user", "validate_and_prepare_email", "update_officer_positions"]
