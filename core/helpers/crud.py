"""
CRUD helper functions for common database operations.

This module provides reusable patterns for DELETE operations and other
CRUD functions to eliminate duplication across route handlers.
"""

from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union

from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.db_schema import get_session
from core.helpers.auth import require_admin
from core.helpers.response import error_redirect, json_error, json_success, success_redirect

# Type variable for SQLAlchemy models
T = TypeVar("T")


def delete_entity(
    request: Request,
    entity_id: int,
    model_class: Type[T],
    redirect_url: Optional[str] = None,
    success_message: str = "Item deleted successfully",
    error_message: str = "Failed to delete item",
    validation_check: Optional[Callable[[Session, int], Optional[str]]] = None,
    pre_delete_hook: Optional[Callable[[Session, int], None]] = None,
    self_delete_check: Optional[Callable[[Dict[str, Any], int], bool]] = None,
) -> Union[JSONResponse, RedirectResponse]:
    """
    Generic DELETE endpoint handler for database entities.

    Args:
        request: FastAPI request object
        entity_id: ID of entity to delete
        model_class: SQLAlchemy model class (e.g., User, News, Poll)
        redirect_url: If provided, redirects after deletion (POST-style)
                     If None, returns JSON (DELETE-style)
        success_message: Message to return on successful deletion
        error_message: Generic error message for failures
        validation_check: Optional function to validate if deletion is allowed
                         Returns error message if validation fails, None if OK
        pre_delete_hook: Optional function to run before deletion (e.g., cascade deletes)
        self_delete_check: Optional function to check if user is trying to delete themselves
                          Returns True if self-delete attempt detected

    Returns:
        JSONResponse if redirect_url is None
        RedirectResponse if redirect_url is provided

    Example:
        Simple delete:
            return delete_entity(
                request, poll_id, Poll,
                redirect_url="/admin/polls",
                success_message="Poll deleted successfully"
            )

        With validation:
            def check_ramp_usage(session: Session, ramp_id: int) -> Optional[str]:
                count = session.query(func.count(Tournament.id)) \\
                    .filter(Tournament.ramp_id == ramp_id).scalar()
                if count > 0:
                    return "Cannot delete ramp referenced by tournaments"
                return None

            return delete_entity(
                request, ramp_id, Ramp,
                validation_check=check_ramp_usage
            )

        With cascade delete:
            def delete_poll_cascade(session: Session, poll_id: int) -> None:
                session.query(PollVote).filter(PollVote.poll_id == poll_id).delete()
                session.query(PollOption).filter(PollOption.poll_id == poll_id).delete()

            return delete_entity(
                request, poll_id, Poll,
                pre_delete_hook=delete_poll_cascade
            )

        With self-delete check:
            def check_self_delete(user: Dict[str, Any], user_id: int) -> bool:
                return user.get("id") == user_id

            return delete_entity(
                request, user_id, Angler,
                self_delete_check=check_self_delete,
                error_message="Cannot delete yourself"
            )
    """
    user = require_admin(request)

    # Check if user is trying to delete themselves
    if self_delete_check and self_delete_check(user, entity_id):
        error_msg = "Cannot delete yourself"
        if redirect_url:
            return error_redirect(redirect_url, error_msg)
        return json_error(error_msg, status_code=400)

    try:
        with get_session() as session:
            # Run validation check if provided
            if validation_check:
                validation_error = validation_check(session, entity_id)
                if validation_error:
                    if redirect_url:
                        return error_redirect(redirect_url, validation_error)
                    return json_error(validation_error, status_code=400)

            # Run pre-delete hook if provided (for cascade deletes)
            if pre_delete_hook:
                pre_delete_hook(session, entity_id)

            # Delete the entity
            entity = session.query(model_class).filter(model_class.id == entity_id).first()  # type: ignore[attr-defined]
            if entity:
                session.delete(entity)
            # Context manager commits automatically

        # Return success response
        if redirect_url:
            return success_redirect(redirect_url, success_message)
        return json_success(message=success_message)

    except Exception as e:
        error_msg = f"{error_message}: {str(e)}"
        if redirect_url:
            return error_redirect(redirect_url, error_msg)
        return json_error(error_msg, status_code=500)


def check_foreign_key_usage(
    session: Session,
    model_class: Type[T],
    foreign_key_field: Any,
    entity_id: int,
    error_message: str,
) -> Optional[str]:
    """
    Check if an entity is referenced by foreign keys before deletion.

    Args:
        session: Database session
        model_class: Model class to check (e.g., Tournament)
        foreign_key_field: Foreign key field to check (e.g., Tournament.ramp_id)
        entity_id: ID to check for references
        error_message: Error message to return if references found

    Returns:
        Error message if references exist, None otherwise

    Example:
        error = check_foreign_key_usage(
            session,
            Tournament,
            Tournament.ramp_id,
            ramp_id,
            "Cannot delete ramp referenced by tournaments"
        )
    """
    count = (
        session.query(func.count(model_class.id)).filter(foreign_key_field == entity_id).scalar()  # type: ignore[attr-defined]
    )
    if count and count > 0:
        return error_message
    return None


def bulk_delete(session: Session, model_class: Type[T], filter_conditions: List[Any]) -> int:
    """
    Delete multiple records matching filter conditions.

    Args:
        session: Database session
        model_class: Model class to delete from
        filter_conditions: List of SQLAlchemy filter conditions

    Returns:
        Number of records deleted

    Example:
        # Delete all votes for a poll
        deleted = bulk_delete(
            session,
            PollVote,
            [PollVote.poll_id == poll_id]
        )
    """
    query = session.query(model_class)
    for condition in filter_conditions:
        query = query.filter(condition)
    count = query.delete(synchronize_session=False)
    return count if isinstance(count, int) else 0
