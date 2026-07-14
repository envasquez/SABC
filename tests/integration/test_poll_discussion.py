"""Integration tests for the per-poll discussion board.

Covers routes/voting/discussion.py end to end: access control, posting,
threaded replies, edit, delete, reactions, the duplicate-content guard, and
pagination. Rate limiting is disabled in the test environment, so the
button-mash defense is exercised here through its server-side halves (the
duplicate guard and the idempotent reaction toggle) rather than HTTP 429s.

Everything runs against the shared in-memory SQLite session via TestClient, so
the suite stays fast (no sleeps, tiny fixtures).
"""

from datetime import timedelta
from typing import Any, Optional

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.db_schema import Angler, Poll, PollComment, PollCommentReaction
from core.helpers.timezone import now_local

# ---------------------------------------------------------------------------
# Helpers & fixtures
# ---------------------------------------------------------------------------


def _csrf(client: TestClient) -> str:
    """Return the client's current CSRF token (double-submit cookie value)."""
    token = client.cookies.get("csrf_token")
    if not token:
        client.get("/polls")
        token = client.cookies.get("csrf_token")
    return token or ""


def _post(client: TestClient, url: str, data: Optional[dict] = None) -> Any:
    """POST with the CSRF token in the header (as the browser JS does)."""
    return client.post(url, data=data or {}, headers={"x-csrf-token": _csrf(client)})


def _make_poll(
    db_session: Session,
    *,
    title: str = "Lake Poll",
    poll_type: str = "tournament_location",
    open_now: bool = True,
) -> Poll:
    now = now_local()
    if open_now:
        starts_at, closes_at, closed = now - timedelta(days=1), now + timedelta(days=7), False
    else:
        starts_at, closes_at, closed = now - timedelta(days=10), now - timedelta(days=1), True
    poll = Poll(
        title=title,
        poll_type=poll_type,
        starts_at=starts_at,
        closes_at=closes_at,
        closed=closed,
    )
    db_session.add(poll)
    db_session.commit()
    db_session.refresh(poll)
    return poll


def _add_comment(
    db_session: Session,
    poll_id: int,
    angler_id: int,
    body: str,
    *,
    parent_id: Optional[int] = None,
    created_at: Any = None,
) -> PollComment:
    comment = PollComment(
        poll_id=poll_id,
        angler_id=angler_id,
        body=body,
        parent_comment_id=parent_id,
        created_at=created_at or now_local(),
    )
    db_session.add(comment)
    db_session.commit()
    db_session.refresh(comment)
    return comment


@pytest.fixture
def open_poll(db_session: Session) -> Poll:
    return _make_poll(db_session, open_now=True)


@pytest.fixture
def closed_poll(db_session: Session) -> Poll:
    return _make_poll(db_session, title="Closed Poll", poll_type="simple", open_now=False)


# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------


class TestDiscussionAccess:
    def test_member_sees_empty_thread(self, member_client: TestClient, open_poll: Poll):
        resp = member_client.get(f"/polls/{open_poll.id}/discussion")
        assert resp.status_code == 200
        assert "No comments yet" in resp.text
        assert "Post Comment" in resp.text  # open poll -> post form present

    def test_closed_poll_is_read_only(self, member_client: TestClient, closed_poll: Poll):
        resp = member_client.get(f"/polls/{closed_poll.id}/discussion")
        assert resp.status_code == 200
        assert "Discussion is closed" in resp.text
        assert "Post Comment" not in resp.text

    def test_non_member_forbidden(self, authenticated_client: TestClient, open_poll: Poll):
        # authenticated_client is a logged-in *non-member* (regular_user).
        resp = authenticated_client.get(f"/polls/{open_poll.id}/discussion")
        assert resp.status_code == 403

    def test_anonymous_redirected_to_login(self, client: TestClient, open_poll: Poll):
        resp = client.get(f"/polls/{open_poll.id}/discussion", follow_redirects=False)
        assert resp.status_code == 303
        assert "/login" in resp.headers.get("location", "")

    def test_discussion_on_missing_poll_404(self, member_client: TestClient):
        resp = member_client.get("/polls/999999/discussion")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Posting comments
# ---------------------------------------------------------------------------


class TestPostComment:
    def test_member_can_post(
        self, member_client: TestClient, db_session: Session, member_user: Angler, open_poll: Poll
    ):
        resp = _post(
            member_client, f"/polls/{open_poll.id}/comments", {"body": "Travis via Mansfield?"}
        )
        assert resp.status_code == 200
        assert "Travis via Mansfield?" in resp.text

        db_session.expire_all()
        rows = db_session.query(PollComment).filter(PollComment.poll_id == open_poll.id).all()
        assert len(rows) == 1
        assert rows[0].angler_id == member_user.id
        assert rows[0].parent_comment_id is None
        assert rows[0].updated_at is None

    def test_empty_body_is_noop(
        self, member_client: TestClient, db_session: Session, open_poll: Poll
    ):
        resp = _post(member_client, f"/polls/{open_poll.id}/comments", {"body": "   "})
        assert resp.status_code == 200
        db_session.expire_all()
        assert db_session.query(PollComment).count() == 0

    def test_post_to_closed_poll_forbidden(
        self, member_client: TestClient, db_session: Session, closed_poll: Poll
    ):
        resp = _post(member_client, f"/polls/{closed_poll.id}/comments", {"body": "too late"})
        assert resp.status_code == 403
        db_session.expire_all()
        assert db_session.query(PollComment).count() == 0

    def test_long_body_truncated(
        self, member_client: TestClient, db_session: Session, open_poll: Poll
    ):
        _post(member_client, f"/polls/{open_poll.id}/comments", {"body": "x" * 2500})
        db_session.expire_all()
        comment = db_session.query(PollComment).one()
        assert len(comment.body) == 2000

    def test_non_member_cannot_post(
        self, authenticated_client: TestClient, db_session: Session, open_poll: Poll
    ):
        resp = _post(authenticated_client, f"/polls/{open_poll.id}/comments", {"body": "hi"})
        assert resp.status_code == 403
        db_session.expire_all()
        assert db_session.query(PollComment).count() == 0


# ---------------------------------------------------------------------------
# Threaded replies (one level)
# ---------------------------------------------------------------------------


class TestReplies:
    def test_reply_attaches_to_parent(
        self, member_client: TestClient, db_session: Session, member_user: Angler, open_poll: Poll
    ):
        parent = _add_comment(db_session, open_poll.id, member_user.id, "root")
        _post(
            member_client,
            f"/polls/{open_poll.id}/comments",
            {"body": "a reply", "parent_id": parent.id},
        )
        db_session.expire_all()
        reply = db_session.query(PollComment).filter(PollComment.body == "a reply").one()
        assert reply.parent_comment_id == parent.id

    def test_reply_to_reply_is_clamped_to_root(
        self, member_client: TestClient, db_session: Session, member_user: Angler, open_poll: Poll
    ):
        root = _add_comment(db_session, open_poll.id, member_user.id, "root")
        child = _add_comment(db_session, open_poll.id, member_user.id, "child", parent_id=root.id)
        _post(
            member_client,
            f"/polls/{open_poll.id}/comments",
            {"body": "grandchild", "parent_id": child.id},
        )
        db_session.expire_all()
        grandchild = db_session.query(PollComment).filter(PollComment.body == "grandchild").one()
        # Clamped to the top-level root, not nested under the reply.
        assert grandchild.parent_comment_id == root.id

    def test_reply_parent_from_other_poll_becomes_top_level(
        self, member_client: TestClient, db_session: Session, member_user: Angler, open_poll: Poll
    ):
        other = _make_poll(db_session, title="Other", open_now=True)
        foreign_parent = _add_comment(db_session, other.id, member_user.id, "foreign")
        _post(
            member_client,
            f"/polls/{open_poll.id}/comments",
            {"body": "orphan", "parent_id": foreign_parent.id},
        )
        db_session.expire_all()
        orphan = db_session.query(PollComment).filter(PollComment.body == "orphan").one()
        assert orphan.poll_id == open_poll.id
        assert orphan.parent_comment_id is None


# ---------------------------------------------------------------------------
# Duplicate-content guard
# ---------------------------------------------------------------------------


class TestDuplicateGuard:
    def test_identical_repost_ignored(
        self, member_client: TestClient, db_session: Session, open_poll: Poll
    ):
        for _ in range(2):
            _post(member_client, f"/polls/{open_poll.id}/comments", {"body": "same text"})
        db_session.expire_all()
        assert db_session.query(PollComment).filter(PollComment.body == "same text").count() == 1

    def test_different_bodies_both_saved(
        self, member_client: TestClient, db_session: Session, open_poll: Poll
    ):
        _post(member_client, f"/polls/{open_poll.id}/comments", {"body": "first"})
        _post(member_client, f"/polls/{open_poll.id}/comments", {"body": "second"})
        db_session.expire_all()
        assert db_session.query(PollComment).count() == 2

    def test_identical_but_old_is_allowed(
        self, member_client: TestClient, db_session: Session, member_user: Angler, open_poll: Poll
    ):
        # A prior identical comment outside the dedup window must not block a repost.
        _add_comment(
            db_session,
            open_poll.id,
            member_user.id,
            "recurring idea",
            created_at=now_local() - timedelta(minutes=5),
        )
        _post(member_client, f"/polls/{open_poll.id}/comments", {"body": "recurring idea"})
        db_session.expire_all()
        assert (
            db_session.query(PollComment).filter(PollComment.body == "recurring idea").count() == 2
        )


# ---------------------------------------------------------------------------
# Editing
# ---------------------------------------------------------------------------


class TestEditComment:
    def test_author_can_edit(
        self, member_client: TestClient, db_session: Session, member_user: Angler, open_poll: Poll
    ):
        comment = _add_comment(db_session, open_poll.id, member_user.id, "typo hre")
        resp = _post(
            member_client,
            f"/polls/{open_poll.id}/comments/{comment.id}/edit",
            {"body": "typo here"},
        )
        assert resp.status_code == 200
        db_session.expire_all()
        refreshed = db_session.query(PollComment).filter(PollComment.id == comment.id).one()
        assert refreshed.body == "typo here"
        assert refreshed.updated_at is not None

    def test_edit_form_renders_for_author(
        self, member_client: TestClient, db_session: Session, member_user: Angler, open_poll: Poll
    ):
        comment = _add_comment(db_session, open_poll.id, member_user.id, "editable")
        resp = member_client.get(f"/polls/{open_poll.id}/comments/{comment.id}/edit")
        assert resp.status_code == 200
        assert "editable" in resp.text
        assert "Save" in resp.text

    def test_empty_edit_keeps_original(
        self, member_client: TestClient, db_session: Session, member_user: Angler, open_poll: Poll
    ):
        comment = _add_comment(db_session, open_poll.id, member_user.id, "keep me")
        _post(member_client, f"/polls/{open_poll.id}/comments/{comment.id}/edit", {"body": "  "})
        db_session.expire_all()
        refreshed = db_session.query(PollComment).filter(PollComment.id == comment.id).one()
        assert refreshed.body == "keep me"
        assert refreshed.updated_at is None

    def test_non_author_cannot_edit(
        self,
        member_client: TestClient,
        db_session: Session,
        admin_user: Angler,
        open_poll: Poll,
    ):
        # Comment owned by someone else (admin_user); member tries to edit.
        comment = _add_comment(db_session, open_poll.id, admin_user.id, "not yours")
        assert (
            member_client.get(f"/polls/{open_poll.id}/comments/{comment.id}/edit").status_code
            == 403
        )
        resp = _post(
            member_client, f"/polls/{open_poll.id}/comments/{comment.id}/edit", {"body": "hijack"}
        )
        assert resp.status_code == 403

    def test_edit_after_close_forbidden(
        self, member_client: TestClient, db_session: Session, member_user: Angler, closed_poll: Poll
    ):
        comment = _add_comment(db_session, closed_poll.id, member_user.id, "old")
        resp = _post(
            member_client, f"/polls/{closed_poll.id}/comments/{comment.id}/edit", {"body": "new"}
        )
        assert resp.status_code == 403

    def test_edit_missing_comment_404(self, member_client: TestClient, open_poll: Poll):
        resp = _post(member_client, f"/polls/{open_poll.id}/comments/424242/edit", {"body": "x"})
        assert resp.status_code == 404

    def test_edit_form_missing_comment_404(self, member_client: TestClient, open_poll: Poll):
        resp = member_client.get(f"/polls/{open_poll.id}/comments/424242/edit")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Deleting
# ---------------------------------------------------------------------------


class TestDeleteComment:
    def test_author_deletes_own(
        self, member_client: TestClient, db_session: Session, member_user: Angler, open_poll: Poll
    ):
        comment = _add_comment(db_session, open_poll.id, member_user.id, "remove me")
        cid = comment.id
        resp = _post(member_client, f"/polls/{open_poll.id}/comments/{cid}/delete")
        assert resp.status_code == 200
        db_session.expire_all()
        assert db_session.query(PollComment).filter(PollComment.id == cid).count() == 0

    def test_admin_moderates_member_comment(
        self, admin_client: TestClient, db_session: Session, member_user: Angler, open_poll: Poll
    ):
        comment = _add_comment(db_session, open_poll.id, member_user.id, "spam")
        cid = comment.id
        resp = _post(admin_client, f"/polls/{open_poll.id}/comments/{cid}/delete")
        assert resp.status_code == 200
        db_session.expire_all()
        assert db_session.query(PollComment).filter(PollComment.id == cid).count() == 0

    def test_member_cannot_delete_others(
        self, member_client: TestClient, db_session: Session, admin_user: Angler, open_poll: Poll
    ):
        comment = _add_comment(db_session, open_poll.id, admin_user.id, "not yours")
        resp = _post(member_client, f"/polls/{open_poll.id}/comments/{comment.id}/delete")
        assert resp.status_code == 403
        db_session.expire_all()
        assert (
            db_session.query(PollComment).filter(PollComment.id == comment.id).first() is not None
        )

    def test_author_can_delete_after_close(
        self, member_client: TestClient, db_session: Session, member_user: Angler, closed_poll: Poll
    ):
        # Delete is moderation/cleanup, allowed even once the poll has closed.
        comment = _add_comment(db_session, closed_poll.id, member_user.id, "cleanup")
        cid = comment.id
        resp = _post(member_client, f"/polls/{closed_poll.id}/comments/{cid}/delete")
        assert resp.status_code == 200
        db_session.expire_all()
        assert db_session.query(PollComment).filter(PollComment.id == cid).count() == 0

    def test_delete_missing_comment_404(self, member_client: TestClient, open_poll: Poll):
        resp = _post(member_client, f"/polls/{open_poll.id}/comments/424242/delete")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Reactions (👍 toggle)
# ---------------------------------------------------------------------------


class TestReactions:
    def test_react_adds_row(
        self, member_client: TestClient, db_session: Session, member_user: Angler, open_poll: Poll
    ):
        comment = _add_comment(db_session, open_poll.id, member_user.id, "good idea")
        resp = _post(member_client, f"/polls/{open_poll.id}/comments/{comment.id}/react")
        assert resp.status_code == 200
        db_session.expire_all()
        assert (
            db_session.query(PollCommentReaction)
            .filter(PollCommentReaction.comment_id == comment.id)
            .count()
            == 1
        )

    def test_react_twice_toggles_off(
        self, member_client: TestClient, db_session: Session, member_user: Angler, open_poll: Poll
    ):
        comment = _add_comment(db_session, open_poll.id, member_user.id, "good idea")
        _post(member_client, f"/polls/{open_poll.id}/comments/{comment.id}/react")
        _post(member_client, f"/polls/{open_poll.id}/comments/{comment.id}/react")
        db_session.expire_all()
        assert (
            db_session.query(PollCommentReaction)
            .filter(PollCommentReaction.comment_id == comment.id)
            .count()
            == 0
        )

    def test_two_members_react(
        self,
        member_client: TestClient,
        db_session: Session,
        member_user: Angler,
        admin_user: Angler,
        open_poll: Poll,
    ):
        comment = _add_comment(db_session, open_poll.id, member_user.id, "popular")
        # member reacts via HTTP; admin reaction inserted directly (distinct angler).
        _post(member_client, f"/polls/{open_poll.id}/comments/{comment.id}/react")
        db_session.add(PollCommentReaction(comment_id=comment.id, angler_id=admin_user.id))
        db_session.commit()
        db_session.expire_all()
        assert (
            db_session.query(PollCommentReaction)
            .filter(PollCommentReaction.comment_id == comment.id)
            .count()
            == 2
        )

    def test_react_on_closed_poll_forbidden(
        self, member_client: TestClient, db_session: Session, member_user: Angler, closed_poll: Poll
    ):
        comment = _add_comment(db_session, closed_poll.id, member_user.id, "late")
        resp = _post(member_client, f"/polls/{closed_poll.id}/comments/{comment.id}/react")
        assert resp.status_code == 403

    def test_react_missing_comment_404(self, member_client: TestClient, open_poll: Poll):
        resp = _post(member_client, f"/polls/{open_poll.id}/comments/424242/react")
        assert resp.status_code == 404

    def test_liked_state_rendered(
        self, member_client: TestClient, db_session: Session, member_user: Angler, open_poll: Poll
    ):
        comment = _add_comment(db_session, open_poll.id, member_user.id, "reactable")
        _post(member_client, f"/polls/{open_poll.id}/comments/{comment.id}/react")
        resp = member_client.get(f"/polls/{open_poll.id}/discussion")
        # The reacting member's button renders in the "liked" (btn-primary) state.
        assert "btn btn-sm btn-primary" in resp.text


# ---------------------------------------------------------------------------
# Pagination / "show earlier"
# ---------------------------------------------------------------------------


class TestPagination:
    def _seed(self, db_session: Session, poll_id: int, angler_id: int, n: int) -> None:
        base = now_local() - timedelta(hours=n)
        for i in range(n):
            _add_comment(
                db_session,
                poll_id,
                angler_id,
                f"Comment {i:02d}",
                created_at=base + timedelta(minutes=i),
            )

    def test_default_page_caps_and_shows_earlier(
        self, member_client: TestClient, db_session: Session, member_user: Angler, open_poll: Poll
    ):
        self._seed(db_session, open_poll.id, member_user.id, 12)
        resp = member_client.get(f"/polls/{open_poll.id}/discussion")
        assert resp.status_code == 200
        # PAGE_SIZE (10) top-level threads rendered; oldest two hidden.
        assert resp.text.count('class="poll-comment mb-2"') == 10
        assert "Show earlier comments" in resp.text
        assert "Comment 11" in resp.text  # newest present
        assert "Comment 00" not in resp.text  # oldest hidden
        assert "Comment 01" not in resp.text

    def test_expanded_limit_shows_all(
        self, member_client: TestClient, db_session: Session, member_user: Angler, open_poll: Poll
    ):
        self._seed(db_session, open_poll.id, member_user.id, 12)
        resp = member_client.get(f"/polls/{open_poll.id}/discussion?limit=50")
        assert resp.status_code == 200
        assert resp.text.count('class="poll-comment mb-2"') == 12
        assert "Show earlier comments" not in resp.text
        assert "Comment 00" in resp.text

    def test_limit_below_pagesize_clamped(
        self, member_client: TestClient, db_session: Session, member_user: Angler, open_poll: Poll
    ):
        self._seed(db_session, open_poll.id, member_user.id, 12)
        resp = member_client.get(f"/polls/{open_poll.id}/discussion?limit=1")
        # Clamped up to PAGE_SIZE, never fewer than 10.
        assert resp.text.count('class="poll-comment mb-2"') == 10

    def test_replies_do_not_count_against_thread_cap(
        self, member_client: TestClient, db_session: Session, member_user: Angler, open_poll: Poll
    ):
        # 3 top-level threads, each with several replies -> still one page, no cap hit.
        for t in range(3):
            root = _add_comment(db_session, open_poll.id, member_user.id, f"thread {t}")
            for r in range(4):
                _add_comment(
                    db_session, open_poll.id, member_user.id, f"reply {t}.{r}", parent_id=root.id
                )
        resp = member_client.get(f"/polls/{open_poll.id}/discussion")
        assert "Show earlier comments" not in resp.text
        assert resp.text.count('class="poll-comment mb-2"') == 3  # 3 roots
        assert resp.text.count("poll-comment-reply") == 12  # 3 * 4 replies


# ---------------------------------------------------------------------------
# Poll list badge integration
# ---------------------------------------------------------------------------


class TestListBadge:
    def test_polls_page_shows_discussion_and_count(
        self, member_client: TestClient, db_session: Session, member_user: Angler, open_poll: Poll
    ):
        _add_comment(db_session, open_poll.id, member_user.id, "one")
        _add_comment(db_session, open_poll.id, member_user.id, "two")
        resp = member_client.get("/polls?tab=tournament")
        assert resp.status_code == 200
        assert f"discussion-body-{open_poll.id}" in resp.text
        # Comment-count badge shows 2 for this poll.
        assert '<span class="badge bg-primary-lt ms-2">2</span>' in resp.text
