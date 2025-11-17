"""Service for merging duplicate user accounts."""

from typing import Any, Dict, Optional

from sqlalchemy import and_, or_, update
from sqlalchemy.exc import IntegrityError

from core.db_schema import get_session
from core.db_schema.models import (
    Angler,
    News,
    OfficerPosition,
    PasswordResetToken,
    Poll,
    PollVote,
    Result,
    TeamResult,
    Tournament,
)
from core.helpers.logging import get_logger

logger = get_logger(__name__)


class AccountMergeError(Exception):
    """Raised when account merge operation fails."""

    pass


def _get_angler(angler_id: int) -> Optional[Dict[str, Any]]:
    """Get angler details by ID.

    Args:
        angler_id: The angler ID to fetch

    Returns:
        Dictionary with angler details or None if not found
    """
    with get_session() as session:
        angler = session.query(Angler).filter(Angler.id == angler_id).first()
        if not angler:
            return None
        return {
            "id": angler.id,
            "name": angler.name,
            "email": angler.email,
            "member": angler.member,
            "is_admin": angler.is_admin,
        }


def preview_merge(source_angler_id: int, target_angler_id: int) -> Dict[str, Any]:
    """Preview what will be merged between two accounts.

    Args:
        source_angler_id: ID of account to merge from (will be deleted)
        target_angler_id: ID of account to merge into (will keep)

    Returns:
        Dictionary containing preview data with counts and warnings

    Raises:
        AccountMergeError: If accounts are invalid or same
    """
    if source_angler_id == target_angler_id:
        raise AccountMergeError("Source and target accounts must be different")

    source = _get_angler(source_angler_id)
    target = _get_angler(target_angler_id)

    if not source:
        raise AccountMergeError(f"Source angler ID {source_angler_id} not found")
    if not target:
        raise AccountMergeError(f"Target angler ID {target_angler_id} not found")

    with get_session() as session:
        # Count results
        results_count = session.query(Result).filter(Result.angler_id == source_angler_id).count()

        # Count team results (as angler1 or angler2)
        team_results_angler1_count = (
            session.query(TeamResult).filter(TeamResult.angler1_id == source_angler_id).count()
        )
        team_results_angler2_count = (
            session.query(TeamResult).filter(TeamResult.angler2_id == source_angler_id).count()
        )

        # Count poll votes
        poll_votes_count = (
            session.query(PollVote).filter(PollVote.angler_id == source_angler_id).count()
        )

        # Count officer positions
        officer_positions_count = (
            session.query(OfficerPosition)
            .filter(OfficerPosition.angler_id == source_angler_id)
            .count()
        )

        # Count created polls
        polls_created_count = (
            session.query(Poll).filter(Poll.created_by == source_angler_id).count()
        )

        # Count news articles
        news_authored_count = session.query(News).filter(News.author_id == source_angler_id).count()

        # Count tournaments created
        tournaments_created_count = (
            session.query(Tournament).filter(Tournament.created_by == source_angler_id).count()
        )

        # Count proxy votes cast
        proxy_votes_cast_count = (
            session.query(PollVote).filter(PollVote.cast_by_admin_id == source_angler_id).count()
        )

        # Find duplicate poll votes (both accounts voted on same poll)
        duplicate_votes = (
            session.query(PollVote.poll_id, Poll.title)
            .join(Poll, PollVote.poll_id == Poll.id)
            .filter(PollVote.angler_id == source_angler_id)
            .filter(
                PollVote.poll_id.in_(
                    session.query(PollVote.poll_id).filter(PollVote.angler_id == target_angler_id)
                )
            )
            .all()
        )

        duplicate_poll_votes = [
            {"poll_id": poll_id, "poll_title": title} for poll_id, title in duplicate_votes
        ]

    return {
        "source_angler": source,
        "target_angler": target,
        "results_count": results_count,
        "team_results_angler1_count": team_results_angler1_count,
        "team_results_angler2_count": team_results_angler2_count,
        "poll_votes_count": poll_votes_count,
        "officer_positions_count": officer_positions_count,
        "polls_created_count": polls_created_count,
        "news_authored_count": news_authored_count,
        "tournaments_created_count": tournaments_created_count,
        "proxy_votes_cast_count": proxy_votes_cast_count,
        "duplicate_poll_votes": duplicate_poll_votes,
    }


def execute_merge(
    source_angler_id: int, target_angler_id: int, admin_id: Optional[int] = None
) -> Dict[str, Any]:
    """Execute the account merge operation.

    Args:
        source_angler_id: ID of account to merge from (will be kept for audit)
        target_angler_id: ID of account to merge into
        admin_id: ID of admin performing the merge (for audit log)

    Returns:
        Dictionary with summary of migrated records

    Raises:
        AccountMergeError: If merge fails
    """
    if source_angler_id == target_angler_id:
        raise AccountMergeError("Source and target accounts must be different")

    # Verify accounts exist
    preview = preview_merge(source_angler_id, target_angler_id)

    logger.info(
        f"Starting account merge: source={source_angler_id} -> target={target_angler_id}, "
        f"admin={admin_id}"
    )

    with get_session() as session:
        try:
            # Update results
            session.execute(
                update(Result)
                .where(Result.angler_id == source_angler_id)
                .values(angler_id=target_angler_id)
            )

            # Update team results (angler1)
            session.execute(
                update(TeamResult)
                .where(TeamResult.angler1_id == source_angler_id)
                .values(angler1_id=target_angler_id)
            )

            # Update team results (angler2)
            session.execute(
                update(TeamResult)
                .where(TeamResult.angler2_id == source_angler_id)
                .values(angler2_id=target_angler_id)
            )

            # Handle poll votes with duplicates
            # First, delete duplicate votes (where both accounts voted on same poll)
            if preview["duplicate_poll_votes"]:
                duplicate_poll_ids = [dv["poll_id"] for dv in preview["duplicate_poll_votes"]]
                deleted_votes = (
                    session.query(PollVote)
                    .filter(
                        and_(
                            PollVote.angler_id == source_angler_id,
                            PollVote.poll_id.in_(duplicate_poll_ids),
                        )
                    )
                    .delete(synchronize_session=False)
                )
                logger.warning(f"Deleted {deleted_votes} duplicate poll votes for source angler")

            # Update remaining poll votes
            session.execute(
                update(PollVote)
                .where(PollVote.angler_id == source_angler_id)
                .values(angler_id=target_angler_id)
            )

            # Update officer positions
            session.execute(
                update(OfficerPosition)
                .where(OfficerPosition.angler_id == source_angler_id)
                .values(angler_id=target_angler_id)
            )

            # Update nullable foreign keys
            session.execute(
                update(PollVote)
                .where(PollVote.cast_by_admin_id == source_angler_id)
                .values(cast_by_admin_id=target_angler_id)
            )

            session.execute(
                update(Poll)
                .where(Poll.created_by == source_angler_id)
                .values(created_by=target_angler_id)
            )

            session.execute(
                update(News)
                .where(News.author_id == source_angler_id)
                .values(author_id=target_angler_id)
            )

            session.execute(
                update(Tournament)
                .where(Tournament.created_by == source_angler_id)
                .values(created_by=target_angler_id)
            )

            # Delete password reset tokens for source account
            deleted_tokens = (
                session.query(PasswordResetToken)
                .filter(PasswordResetToken.user_id == source_angler_id)
                .delete(synchronize_session=False)
            )

            session.commit()

            logger.info(
                f"Account merge completed successfully: {source_angler_id} -> {target_angler_id}"
            )

            return {
                "success": True,
                "source_angler_id": source_angler_id,
                "target_angler_id": target_angler_id,
                "migrated": {
                    "results": preview["results_count"],
                    "team_results": preview["team_results_angler1_count"]
                    + preview["team_results_angler2_count"],
                    "poll_votes": preview["poll_votes_count"]
                    - len(preview["duplicate_poll_votes"]),
                    "officer_positions": preview["officer_positions_count"],
                    "polls_created": preview["polls_created_count"],
                    "news_authored": preview["news_authored_count"],
                    "tournaments_created": preview["tournaments_created_count"],
                    "proxy_votes_cast": preview["proxy_votes_cast_count"],
                },
                "deleted_duplicate_votes": len(preview["duplicate_poll_votes"]),
                "deleted_password_tokens": deleted_tokens,
            }

        except IntegrityError as e:
            session.rollback()
            logger.error(f"Database integrity error during merge: {e}")
            raise AccountMergeError(f"Database integrity error: {str(e)}")
        except Exception as e:
            session.rollback()
            logger.error(f"Unexpected error during merge: {e}")
            raise AccountMergeError(f"Merge failed: {str(e)}")


def delete_merged_account(angler_id: int) -> bool:
    """Delete an account after verifying all data has been migrated.

    Args:
        angler_id: ID of account to delete

    Returns:
        True if deleted successfully

    Raises:
        AccountMergeError: If account still has data or cannot be deleted
    """
    with get_session() as session:
        # Verify no data remains
        results_count = session.query(Result).filter(Result.angler_id == angler_id).count()
        team_results_count = (
            session.query(TeamResult)
            .filter(or_(TeamResult.angler1_id == angler_id, TeamResult.angler2_id == angler_id))
            .count()
        )
        poll_votes_count = session.query(PollVote).filter(PollVote.angler_id == angler_id).count()
        officer_count = (
            session.query(OfficerPosition).filter(OfficerPosition.angler_id == angler_id).count()
        )

        total_records = results_count + team_results_count + poll_votes_count + officer_count

        if total_records > 0:
            raise AccountMergeError(
                f"Cannot delete account: still has {total_records} records. "
                f"Ensure merge completed successfully first."
            )

        # Delete the account
        angler = session.query(Angler).filter(Angler.id == angler_id).first()
        if not angler:
            raise AccountMergeError(f"Angler ID {angler_id} not found")

        session.delete(angler)
        session.commit()

        logger.info(f"Deleted merged account: {angler_id}")
        return True
