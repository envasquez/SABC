from typing import Any, Dict, Optional

from fastapi import APIRouter, Request, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.db_schema import (
    Angler,
    OfficerPosition,
    PasswordResetToken,
    PollVote,
    Result,
    TeamResult,
)
from core.helpers.crud import delete_entity

router = APIRouter()


def _check_self_delete(user: Dict[str, Any], user_id: int) -> bool:
    """Check if user is trying to delete themselves."""
    return user.get("id") == user_id


def _check_tournament_history(session: Session, user_id: int) -> Optional[str]:
    """Check if user has tournament results that would prevent deletion."""
    # Check individual results
    result_count = session.query(func.count(Result.id)).filter(Result.angler_id == user_id).scalar()
    if result_count and result_count > 0:
        return f"Cannot delete user with tournament history ({result_count} results). Consider deactivating instead."

    # Check team results
    team_count = (
        session.query(func.count(TeamResult.id))
        .filter((TeamResult.angler1_id == user_id) | (TeamResult.angler2_id == user_id))
        .scalar()
    )
    if team_count and team_count > 0:
        return f"Cannot delete user with team tournament history ({team_count} team results)."

    return None


def _cleanup_user_references(session: Session, user_id: int) -> None:
    """Delete user references that can be safely removed before deletion."""
    # Delete password reset tokens
    session.query(PasswordResetToken).filter(PasswordResetToken.user_id == user_id).delete()

    # Delete poll votes (votes are ephemeral)
    session.query(PollVote).filter(PollVote.angler_id == user_id).delete()

    # Delete officer positions
    session.query(OfficerPosition).filter(OfficerPosition.angler_id == user_id).delete()


@router.delete("/admin/users/{user_id}")
async def delete_user(request: Request, user_id: int) -> Response:
    """Delete a user account (cannot delete yourself or users with tournament history)."""
    return delete_entity(
        request,
        user_id,
        Angler,
        success_message="User deleted successfully",
        error_message="Failed to delete user",
        self_delete_check=_check_self_delete,
        validation_check=_check_tournament_history,
        pre_delete_hook=_cleanup_user_references,
    )
