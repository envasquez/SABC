"""Per-poll discussion board (comments, threaded replies, 👍 reactions).

All views render the same ``polls/_discussion.html`` partial into the
``#discussion-body-{poll_id}`` container, so every action (post, reply, edit,
delete, react) is a single HTMX swap. Reading is open to any member; posting,
editing and reacting are only allowed while the poll is open (its voting
window is active). Deleting is allowed for the author or an admin at any time.
"""

import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import Response
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.db_schema import (
    Angler,
    Poll,
    PollComment,
    PollCommentReaction,
    get_session,
)
from core.deps import templates
from core.helpers.auth import require_member
from core.helpers.logging import get_logger
from core.helpers.timezone import now_local
from core.types import UserDict

router = APIRouter()
logger = get_logger("discussion")

_is_test_env = os.environ.get("ENVIRONMENT") == "test"
limiter = Limiter(key_func=get_remote_address, enabled=not _is_test_env)

# Guard rails on comment length so the textarea can't be used to dump huge
# payloads into the page.
MAX_COMMENT_LENGTH = 2000

# Top-level threads rendered per "page" of the discussion. Replies always load
# with their parent thread; only the number of root comments is capped so a
# long-running debate can't push the page down forever, and so a single action
# never has to re-render hundreds of comments. "Show earlier" raises the limit.
PAGE_SIZE = 10
MAX_LIMIT = 500

# An identical repost by the same author within this window is treated as a
# double-submit / button-mash and silently ignored (defense in depth behind
# the rate limiter and the client-side button disabling).
DUPLICATE_WINDOW_SECONDS = 30


def _poll_is_open(poll: Poll) -> bool:
    """A poll accepts discussion posts only while its voting window is active."""
    now = now_local()
    return bool(poll.starts_at <= now <= poll.closes_at and not poll.closed)


def _serialize_comment(
    comment: PollComment,
    author_name: str,
    user: UserDict,
    poll_open: bool,
    like_count: int,
    liked_by_me: bool,
    editing_id: Optional[int],
) -> Dict[str, Any]:
    is_author = comment.angler_id == user.get("id")
    is_admin = bool(user.get("is_admin"))
    return {
        "id": comment.id,
        "author_id": comment.angler_id,
        "author_name": author_name,
        "body": comment.body,
        "created_at": comment.created_at,
        "updated_at": comment.updated_at,
        "edited": comment.updated_at is not None,
        # Editing own comment is only allowed while the poll is open.
        "can_edit": is_author and poll_open,
        # Authors can always tidy up their own posts; admins can moderate any.
        "can_delete": is_author or is_admin,
        "like_count": like_count,
        "liked_by_me": liked_by_me,
        "is_editing": editing_id is not None and comment.id == editing_id,
        "replies": [],
    }


def build_discussion_context(
    session: Session,
    poll: Poll,
    user: UserDict,
    editing_id: Optional[int] = None,
    limit: int = PAGE_SIZE,
) -> Dict[str, Any]:
    """Assemble the nested comment tree + reaction state for one poll.

    Only the newest ``limit`` top-level threads are rendered (their replies come
    along); older threads stay behind a "Show earlier comments" control. This
    bounds both page height and the per-action re-render cost.
    """
    poll_open = _poll_is_open(poll)
    limit = min(max(PAGE_SIZE, limit), MAX_LIMIT)

    # Total top-level threads, so we know whether older ones remain hidden.
    total_threads = (
        session.query(func.count(PollComment.id))
        .filter(
            PollComment.poll_id == poll.id,
            PollComment.parent_comment_id.is_(None),
        )
        .scalar()
        or 0
    )

    # Newest ``limit`` thread roots (we display them oldest→newest below).
    root_ids = [
        r[0]
        for r in (
            session.query(PollComment.id)
            .filter(
                PollComment.poll_id == poll.id,
                PollComment.parent_comment_id.is_(None),
            )
            .order_by(PollComment.created_at.desc(), PollComment.id.desc())
            .limit(limit)
            .all()
        )
    ]

    # Fetch those roots plus their direct replies, oldest-first for display.
    rows = []
    if root_ids:
        rows = (
            session.query(PollComment, Angler.name)
            .join(Angler, PollComment.angler_id == Angler.id)
            .filter(
                PollComment.poll_id == poll.id,
                or_(
                    PollComment.id.in_(root_ids),
                    PollComment.parent_comment_id.in_(root_ids),
                ),
            )
            .order_by(PollComment.created_at.asc(), PollComment.id.asc())
            .all()
        )

    comment_ids = [row[0].id for row in rows]

    # Reaction counts per comment, plus which ones the current user reacted to.
    like_counts: Dict[int, int] = {}
    liked_by_me: set[int] = set()
    if comment_ids:
        for comment_id, count in (
            session.query(
                PollCommentReaction.comment_id,
                func.count(PollCommentReaction.id),
            )
            .filter(PollCommentReaction.comment_id.in_(comment_ids))
            .group_by(PollCommentReaction.comment_id)
            .all()
        ):
            like_counts[comment_id] = count
        liked_by_me = {
            r[0]
            for r in session.query(PollCommentReaction.comment_id)
            .filter(
                PollCommentReaction.comment_id.in_(comment_ids),
                PollCommentReaction.angler_id == user["id"],
            )
            .all()
        }

    # First pass: serialize every comment keyed by id.
    serialized: Dict[int, Dict[str, Any]] = {}
    for comment, author_name in rows:
        serialized[comment.id] = _serialize_comment(
            comment,
            author_name,
            user,
            poll_open,
            like_counts.get(comment.id, 0),
            comment.id in liked_by_me,
            editing_id,
        )

    # Second pass: nest replies under their top-level parent (one level deep).
    top_level: List[Dict[str, Any]] = []
    for comment, _author_name in rows:
        node = serialized[comment.id]
        parent_id = comment.parent_comment_id
        if parent_id is not None and parent_id in serialized:
            serialized[parent_id]["replies"].append(node)
        else:
            top_level.append(node)

    return {
        "poll_id": poll.id,
        "poll_open": poll_open,
        "comments": top_level,
        "total_threads": total_threads,
        "shown_limit": limit,
        "has_earlier": total_threads > len(root_ids),
        "next_limit": limit + PAGE_SIZE,
        "max_comment_length": MAX_COMMENT_LENGTH,
    }


def _render_thread(
    request: Request,
    session: Session,
    poll: Poll,
    user: UserDict,
    editing_id: Optional[int] = None,
    limit: int = PAGE_SIZE,
) -> Response:
    context = build_discussion_context(session, poll, user, editing_id=editing_id, limit=limit)
    context["request"] = request
    context["user"] = user
    return templates.TemplateResponse(request, "polls/_discussion.html", context)


def _load_poll(session: Session, poll_id: int) -> Poll:
    poll = session.query(Poll).filter(Poll.id == poll_id).first()
    if poll is None:
        raise HTTPException(status_code=404, detail="Poll not found")
    return poll


@router.get("/polls/{poll_id}/discussion")
def get_discussion(
    request: Request,
    poll_id: int,
    limit: int = PAGE_SIZE,
    user: UserDict = Depends(require_member),
) -> Response:
    """Render the discussion thread for a poll (HTMX target).

    ``limit`` controls how many top-level threads are shown; the "Show earlier
    comments" control re-requests with a larger value.
    """
    with get_session() as session:
        poll = _load_poll(session, poll_id)
        return _render_thread(request, session, poll, user, limit=limit)


@router.post("/polls/{poll_id}/comments")
@limiter.limit("20/minute")
def create_comment(
    request: Request,
    poll_id: int,
    body: str = Form(),
    parent_id: Optional[int] = Form(None),
    limit: int = Form(PAGE_SIZE),
    user: UserDict = Depends(require_member),
) -> Response:
    """Post a new comment or a reply (parent_id set)."""
    text = (body or "").strip()
    with get_session() as session:
        poll = _load_poll(session, poll_id)
        if not _poll_is_open(poll):
            raise HTTPException(status_code=403, detail="Discussion is closed for this poll")
        if not text:
            return _render_thread(request, session, poll, user, limit=limit)
        text = text[:MAX_COMMENT_LENGTH]

        # Duplicate-content guard: if this author already posted an identical
        # comment on this poll moments ago, treat it as a double-submit and
        # no-op rather than inserting a second row. Catches mashes that slip
        # past the rate limiter and the client-side button disabling.
        last_identical = (
            session.query(PollComment)
            .filter(
                PollComment.poll_id == poll_id,
                PollComment.angler_id == user["id"],
                PollComment.body == text,
            )
            .order_by(PollComment.created_at.desc())
            .first()
        )
        if last_identical is not None and last_identical.created_at is not None:
            age = (now_local() - last_identical.created_at).total_seconds()
            if age < DUPLICATE_WINDOW_SECONDS:
                logger.info(
                    "Ignored duplicate poll comment",
                    extra={"poll_id": poll_id, "user_id": user["id"]},
                )
                return _render_thread(request, session, poll, user, limit=limit)

        # Clamp threading to a single level: if replying to a reply, attach to
        # the reply's top-level parent instead.
        resolved_parent_id: Optional[int] = None
        if parent_id is not None:
            parent = (
                session.query(PollComment)
                .filter(PollComment.id == parent_id, PollComment.poll_id == poll_id)
                .first()
            )
            if parent is not None:
                resolved_parent_id = parent.parent_comment_id or parent.id

        session.add(
            PollComment(
                poll_id=poll_id,
                angler_id=user["id"],
                parent_comment_id=resolved_parent_id,
                body=text,
                created_at=now_local(),
            )
        )
        session.flush()
        logger.info(
            "Poll comment posted",
            extra={
                "poll_id": poll_id,
                "user_id": user["id"],
                "is_reply": resolved_parent_id is not None,
            },
        )
        return _render_thread(request, session, poll, user, limit=limit)


@router.get("/polls/{poll_id}/comments/{comment_id}/edit")
def edit_comment_form(
    request: Request,
    poll_id: int,
    comment_id: int,
    limit: int = PAGE_SIZE,
    user: UserDict = Depends(require_member),
) -> Response:
    """Re-render the thread with one comment switched into an inline edit form."""
    with get_session() as session:
        poll = _load_poll(session, poll_id)
        comment = (
            session.query(PollComment)
            .filter(PollComment.id == comment_id, PollComment.poll_id == poll_id)
            .first()
        )
        if comment is None:
            raise HTTPException(status_code=404, detail="Comment not found")
        # Only the author may open the edit form, and only while the poll is open.
        if comment.angler_id != user.get("id") or not _poll_is_open(poll):
            raise HTTPException(status_code=403, detail="Cannot edit this comment")
        return _render_thread(request, session, poll, user, editing_id=comment_id, limit=limit)


@router.post("/polls/{poll_id}/comments/{comment_id}/edit")
@limiter.limit("20/minute")
def edit_comment_save(
    request: Request,
    poll_id: int,
    comment_id: int,
    body: str = Form(),
    limit: int = Form(PAGE_SIZE),
    user: UserDict = Depends(require_member),
) -> Response:
    """Save an edited comment (author only, poll must be open)."""
    text = (body or "").strip()
    with get_session() as session:
        poll = _load_poll(session, poll_id)
        comment = (
            session.query(PollComment)
            .filter(PollComment.id == comment_id, PollComment.poll_id == poll_id)
            .first()
        )
        if comment is None:
            raise HTTPException(status_code=404, detail="Comment not found")
        if comment.angler_id != user.get("id") or not _poll_is_open(poll):
            raise HTTPException(status_code=403, detail="Cannot edit this comment")
        if text:
            comment.body = text[:MAX_COMMENT_LENGTH]
            comment.updated_at = now_local()
            logger.info(
                "Poll comment edited",
                extra={"poll_id": poll_id, "user_id": user["id"], "comment_id": comment_id},
            )
        return _render_thread(request, session, poll, user, limit=limit)


@router.post("/polls/{poll_id}/comments/{comment_id}/delete")
@limiter.limit("30/minute")
def delete_comment(
    request: Request,
    poll_id: int,
    comment_id: int,
    limit: int = Form(PAGE_SIZE),
    user: UserDict = Depends(require_member),
) -> Response:
    """Delete a comment (author any time, or admin moderation). Replies cascade."""
    with get_session() as session:
        poll = _load_poll(session, poll_id)
        comment = (
            session.query(PollComment)
            .filter(PollComment.id == comment_id, PollComment.poll_id == poll_id)
            .first()
        )
        if comment is None:
            raise HTTPException(status_code=404, detail="Comment not found")
        if comment.angler_id != user.get("id") and not user.get("is_admin"):
            raise HTTPException(status_code=403, detail="Cannot delete this comment")
        session.delete(comment)
        session.flush()
        logger.info(
            "Poll comment deleted",
            extra={
                "poll_id": poll_id,
                "user_id": user["id"],
                "comment_id": comment_id,
                "by_admin": bool(user.get("is_admin")) and comment.angler_id != user.get("id"),
            },
        )
        return _render_thread(request, session, poll, user, limit=limit)


@router.post("/polls/{poll_id}/comments/{comment_id}/react")
@limiter.limit("40/minute")
def toggle_reaction(
    request: Request,
    poll_id: int,
    comment_id: int,
    limit: int = Form(PAGE_SIZE),
    user: UserDict = Depends(require_member),
) -> Response:
    """Toggle the current member's 👍 on a comment (poll must be open)."""
    with get_session() as session:
        poll = _load_poll(session, poll_id)
        if not _poll_is_open(poll):
            raise HTTPException(status_code=403, detail="Discussion is closed for this poll")
        comment = (
            session.query(PollComment)
            .filter(PollComment.id == comment_id, PollComment.poll_id == poll_id)
            .first()
        )
        if comment is None:
            raise HTTPException(status_code=404, detail="Comment not found")

        existing = (
            session.query(PollCommentReaction)
            .filter(
                PollCommentReaction.comment_id == comment_id,
                PollCommentReaction.angler_id == user["id"],
            )
            .first()
        )
        if existing is not None:
            session.delete(existing)
        else:
            # Two fast clicks can both read "no reaction" and both insert; the
            # unique constraint makes the loser raise IntegrityError. Swallow it
            # in a savepoint (already-reacted is the desired end state) so the
            # race surfaces as a no-op instead of an HTTP 500.
            try:
                with session.begin_nested():
                    session.add(
                        PollCommentReaction(
                            comment_id=comment_id,
                            angler_id=user["id"],
                            created_at=now_local(),
                        )
                    )
            except IntegrityError:
                logger.info(
                    "Concurrent reaction insert ignored",
                    extra={"poll_id": poll_id, "user_id": user["id"], "comment_id": comment_id},
                )
        session.flush()
        return _render_thread(request, session, poll, user, limit=limit)
