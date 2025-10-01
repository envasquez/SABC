from typing import Tuple

from core.helpers.logging import SecurityEvent, get_logger, log_security_event

logger = get_logger("admin.users.update")


def log_update_initiated(admin_user: dict, user_id: int, update_params: dict, before: Tuple):
    logger.info(
        "Admin user update initiated",
        extra={
            "admin_user_id": admin_user.get("id"),
            "target_user_id": user_id,
            "changes": update_params,
            "before": dict(zip(["name", "email", "phone", "member", "is_admin"], before)),
        },
    )


def log_update_completed(
    request, admin_user: dict, user_id: int, update_params: dict, before: Tuple, after: Tuple
):
    log_security_event(
        SecurityEvent.ADMIN_USER_UPDATE,
        user_id=admin_user.get("id"),
        user_email=admin_user.get("email"),
        ip_address=request.client.host if request.client else "unknown",
        details={
            "target_user_id": user_id,
            "changes": update_params,
            "before": dict(zip(["name", "email", "phone", "member", "is_admin"], before)),
            "after": dict(zip(["name", "email", "phone", "member", "is_admin"], after)),
        },
    )
    logger.info(
        "User updated successfully",
        extra={
            "admin_user_id": admin_user.get("id"),
            "target_user_id": user_id,
            "after": dict(zip(["name", "email", "phone", "member", "is_admin"], after)),
        },
    )


def log_update_failed(admin_user: dict, user_id: int, update_params: dict):
    logger.warning(
        "User update failed - no changes detected",
        extra={
            "admin_user_id": admin_user.get("id"),
            "target_user_id": user_id,
            "update_params": update_params,
        },
    )


def log_update_exception(admin_user: dict, user_id: int, error: Exception, update_params: dict):
    logger.error(
        "User update exception",
        extra={
            "admin_user_id": admin_user.get("id"),
            "target_user_id": user_id,
            "error": str(error),
            "update_params": update_params,
        },
        exc_info=True,
    )
