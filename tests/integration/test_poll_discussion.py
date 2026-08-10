"""Integration tests for the per-poll discussion board.

Covers routes/voting/discussion.py end to end: access control, posting,
threaded replies, edit, delete, reactions, the duplicate-content guard, and
pagination. Rate limiting is disabled in the test environment, so the
button-mash defense is exercised here through its server-side halves (the
duplicate guard and the idempotent reaction toggle) rather than HTTP 429s.

Everything runs against the shared in-memory SQLite session via TestClient, so
the suite stays fast (no sleeps, tiny fixtures).
"""

from datetime import date, timedelta
from typing import Any, Optional

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.db_schema import Angler, Event, Poll, PollComment, PollCommentReaction
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


def _make_tournament_poll(
    db_session: Session, event_date: date, *, voting_closed: bool = True
) -> Poll:
    """A tournament_location poll (voting closed by default) tied to an event on
    ``event_date`` — used to exercise the tournament discussion window."""
    now = now_local()
    event = Event(
        date=event_date,
        year=event_date.year,
        name="Tournament",
        event_type="sabc_tournament",
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)
    poll = Poll(
        title="Location Vote",
        poll_type="tournament_location",
        event_id=event.id,
        starts_at=now - timedelta(days=14),
        closes_at=(now - timedelta(days=3)) if voting_closed else (now + timedelta(days=3)),
        closed=voting_closed,
    )
    db_session.add(poll)
    db_session.commit()
    db_session.refresh(poll)
    return poll


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

    def test_reply_and_new_topic_are_labeled_distinctly(
        self, member_client: TestClient, db_session: Session, member_user: Angler, open_poll: Poll
    ):
        # The reply box and the new-thread composer must read differently so
        # members don't post a new thread thinking they're replying.
        _add_comment(db_session, open_poll.id, member_user.id, "root")
        resp = member_client.get(f"/polls/{open_poll.id}/discussion")
        assert "Replying to Test Member" in resp.text  # labeled, attributed reply box
        assert "Post Reply" in resp.text
        assert "Start a new topic" in resp.text  # clearly-labeled new-thread composer


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

    def test_reply_to_reply_is_flat_with_attribution(
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
        # Stored flat under the root (display stays one level deep)...
        assert grandchild.parent_comment_id == root.id
        # ...but records the actual reply target for the "Replying to X" label.
        assert grandchild.reply_to_comment_id == child.id

    def test_first_level_reply_has_no_reply_target_label(
        self, member_client: TestClient, db_session: Session, member_user: Angler, open_poll: Poll
    ):
        root = _add_comment(db_session, open_poll.id, member_user.id, "root")
        _post(
            member_client,
            f"/polls/{open_poll.id}/comments",
            {"body": "direct reply", "parent_id": root.id},
        )
        db_session.expire_all()
        reply = db_session.query(PollComment).filter(PollComment.body == "direct reply").one()
        # reply_to == parent (root), so the UI won't show a redundant label.
        assert reply.reply_to_comment_id == root.id
        assert reply.parent_comment_id == root.id

    def test_replies_are_replyable_with_attribution_rendered(
        self,
        member_client: TestClient,
        db_session: Session,
        member_user: Angler,
        admin_user: Angler,
        open_poll: Poll,
    ):
        root = _add_comment(db_session, open_poll.id, member_user.id, "root")
        # A reply authored by admin, which member will reply to.
        reply = _add_comment(
            db_session, open_poll.id, admin_user.id, "admin reply", parent_id=root.id
        )
        _post(
            member_client,
            f"/polls/{open_poll.id}/comments",
            {"body": "reply to the reply", "parent_id": reply.id},
        )
        resp = member_client.get(f"/polls/{open_poll.id}/discussion")
        # Every comment carries a Reply toggle now (id="reply-{poll}-{comment}").
        assert f'id="reply-{open_poll.id}-{reply.id}"' in resp.text
        # And the reply-to-a-reply shows attribution to the admin.
        assert "Replying to <strong>Test Admin</strong>" in resp.text

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

    def test_reactor_names_in_tooltip(
        self,
        member_client: TestClient,
        db_session: Session,
        member_user: Angler,
        admin_user: Angler,
        open_poll: Poll,
    ):
        comment = _add_comment(db_session, open_poll.id, member_user.id, "popular")
        _post(member_client, f"/polls/{open_poll.id}/comments/{comment.id}/react")
        db_session.add(PollCommentReaction(comment_id=comment.id, angler_id=admin_user.id))
        db_session.commit()
        resp = member_client.get(f"/polls/{open_poll.id}/discussion")
        # Full names of everyone who agreed, alphabetized, in the hover tooltip.
        assert 'title="Test Admin, Test Member"' in resp.text

    def test_no_tooltip_without_reactions(
        self, member_client: TestClient, db_session: Session, member_user: Angler, open_poll: Poll
    ):
        _add_comment(db_session, open_poll.id, member_user.id, "unreacted")
        resp = member_client.get(f"/polls/{open_poll.id}/discussion")
        # No name tooltip on an unreacted, open-poll comment.
        assert 'title="Test Member"' not in resp.text


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
# Tournament discussion window (open until 1 day after the tournament date)
# ---------------------------------------------------------------------------


class TestTournamentDiscussionWindow:
    def test_open_when_voting_closed_but_before_event(
        self, member_client: TestClient, db_session: Session
    ):
        # Tournament is today and voting already closed -> discussion still open.
        poll = _make_tournament_poll(db_session, now_local().date())
        resp = _post(member_client, f"/polls/{poll.id}/comments", {"body": "still talking"})
        assert resp.status_code == 200
        db_session.expire_all()
        assert db_session.query(PollComment).filter(PollComment.poll_id == poll.id).count() == 1

    def test_closed_day_after_event(self, member_client: TestClient, db_session: Session):
        # Discussion closes at midnight ending tournament day, so the day after
        # (tournament was yesterday) is read-only.
        poll = _make_tournament_poll(db_session, now_local().date() - timedelta(days=1))
        resp = _post(member_client, f"/polls/{poll.id}/comments", {"body": "too late"})
        assert resp.status_code == 403

    def test_closed_tournament_renders_read_only(
        self, member_client: TestClient, db_session: Session
    ):
        poll = _make_tournament_poll(db_session, now_local().date() - timedelta(days=5))
        resp = member_client.get(f"/polls/{poll.id}/discussion")
        assert resp.status_code == 200
        assert "Discussion is closed" in resp.text

    def test_open_tournament_shows_post_form(self, member_client: TestClient, db_session: Session):
        poll = _make_tournament_poll(db_session, now_local().date())
        resp = member_client.get(f"/polls/{poll.id}/discussion")
        assert "Post Comment" in resp.text

    def test_upcoming_poll_not_yet_open(self, member_client: TestClient, db_session: Session):
        # Poll hasn't started yet -> discussion is not open.
        now = now_local()
        event = Event(
            date=(now + timedelta(days=10)).date(),
            year=(now + timedelta(days=10)).year,
            name="Future Tournament",
            event_type="sabc_tournament",
        )
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)
        poll = Poll(
            title="Upcoming",
            poll_type="tournament_location",
            event_id=event.id,
            starts_at=now + timedelta(days=1),
            closes_at=now + timedelta(days=8),
            closed=False,
        )
        db_session.add(poll)
        db_session.commit()
        db_session.refresh(poll)
        resp = _post(member_client, f"/polls/{poll.id}/comments", {"body": "too early"})
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Reply email notifications
# ---------------------------------------------------------------------------


class TestReplyNotifications:
    def _capture(self, monkeypatch):
        calls: list = []
        monkeypatch.setattr(
            "routes.voting.discussion.send_reply_notification",
            lambda *args, **kwargs: calls.append(args) or True,
        )
        return calls

    def test_reply_notifies_parent_author(
        self,
        member_client: TestClient,
        db_session: Session,
        member_user: Angler,
        admin_user: Angler,
        open_poll: Poll,
        monkeypatch,
    ):
        calls = self._capture(monkeypatch)
        parent = _add_comment(db_session, open_poll.id, admin_user.id, "root by admin")
        _post(
            member_client,
            f"/polls/{open_poll.id}/comments",
            {"body": "my reply text", "parent_id": parent.id},
        )
        assert len(calls) == 1
        email, _recipient, replier, _title, reply_body, _url = calls[0]
        assert email == admin_user.email
        assert reply_body == "my reply text"
        assert replier == member_user.name

    def test_reply_to_reply_notifies_the_reply_author(
        self,
        member_client: TestClient,
        db_session: Session,
        member_user: Angler,
        admin_user: Angler,
        open_poll: Poll,
        monkeypatch,
    ):
        # member starts a thread; admin replies; member replies to admin's
        # reply -> the admin (the targeted reply's author) is notified.
        calls = self._capture(monkeypatch)
        root = _add_comment(db_session, open_poll.id, member_user.id, "root by member")
        reply = _add_comment(
            db_session, open_poll.id, admin_user.id, "reply by admin", parent_id=root.id
        )
        _post(
            member_client,
            f"/polls/{open_poll.id}/comments",
            {"body": "answering admin", "parent_id": reply.id},
        )
        assert len(calls) == 1
        assert calls[0][0] == admin_user.email

    def test_no_notification_on_self_reply(
        self,
        member_client: TestClient,
        db_session: Session,
        member_user: Angler,
        open_poll: Poll,
        monkeypatch,
    ):
        calls = self._capture(monkeypatch)
        parent = _add_comment(db_session, open_poll.id, member_user.id, "my own comment")
        _post(
            member_client,
            f"/polls/{open_poll.id}/comments",
            {"body": "replying to myself", "parent_id": parent.id},
        )
        assert calls == []

    def test_no_notification_when_master_off(
        self,
        member_client: TestClient,
        db_session: Session,
        admin_user: Angler,
        open_poll: Poll,
        monkeypatch,
    ):
        calls = self._capture(monkeypatch)
        admin_user.email_opt_in = False
        db_session.commit()
        parent = _add_comment(db_session, open_poll.id, admin_user.id, "root")
        _post(
            member_client, f"/polls/{open_poll.id}/comments", {"body": "hi", "parent_id": parent.id}
        )
        assert calls == []

    def test_no_notification_when_replies_disabled(
        self,
        member_client: TestClient,
        db_session: Session,
        admin_user: Angler,
        open_poll: Poll,
        monkeypatch,
    ):
        calls = self._capture(monkeypatch)
        admin_user.notify_replies = False
        db_session.commit()
        parent = _add_comment(db_session, open_poll.id, admin_user.id, "root")
        _post(
            member_client, f"/polls/{open_poll.id}/comments", {"body": "hi", "parent_id": parent.id}
        )
        assert calls == []

    def test_top_level_comment_sends_nothing(
        self, member_client: TestClient, db_session: Session, open_poll: Poll, monkeypatch
    ):
        calls = self._capture(monkeypatch)
        _post(member_client, f"/polls/{open_poll.id}/comments", {"body": "a top-level comment"})
        assert calls == []


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
