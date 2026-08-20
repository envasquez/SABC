"""Regression tests for views that must render already-expanded.

Members were having to click twice to reach the two most useful things on the
polls page — the month's tournament history and an active discussion thread.
Both are still <details>, so they stay collapsible; they just no longer start
closed. The discussion additionally has to switch its HTMX trigger, because a
lazy "click once" fetch never fires on a panel that is already open.
"""

import re
from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.db_schema import Angler, Poll, PollComment
from core.helpers.timezone import now_local


def _make_poll(db_session: Session, *, title: str = "Lake Poll") -> Poll:
    now = now_local()
    poll = Poll(
        title=title,
        poll_type="tournament_location",
        starts_at=now - timedelta(days=1),
        closes_at=now + timedelta(days=7),
        closed=False,
    )
    db_session.add(poll)
    db_session.commit()
    db_session.refresh(poll)
    return poll


def _discussion_details(html: str, poll_id: int) -> str:
    """One poll's discussion <details> through the end of its <summary>.

    Anchored on the poll id in hx-get so a page with several polls still yields
    the right block, and extended to </summary> so hx-trigger is inside it.
    """
    match = re.search(
        r"<details class=\"poll-discussion\"[^>]*>.*?hx-get=\"/polls/%d/discussion\".*?</summary>"
        % poll_id,
        html,
        re.DOTALL,
    )
    assert match, f"discussion block for poll {poll_id} not found"
    return match.group(0)


class TestDiscussionDefaultsExpanded:
    def test_poll_with_comments_opens_and_fetches_on_load(
        self, member_client: TestClient, db_session: Session, member_user: Angler
    ):
        poll = _make_poll(db_session)
        db_session.add(
            PollComment(poll_id=poll.id, angler_id=member_user.id, body="Lets fish Travis")
        )
        db_session.commit()

        block = _discussion_details(member_client.get("/polls").text, poll.id)

        assert " open>" in block, "discussion with comments should render expanded"
        assert 'hx-trigger="load once"' in block, (
            "an already-open panel must fetch on load — 'click once' would never fire"
        )

    def test_poll_without_comments_stays_collapsed_and_lazy(
        self, member_client: TestClient, db_session: Session
    ):
        poll = _make_poll(db_session, title="Quiet Poll")

        block = _discussion_details(member_client.get("/polls").text, poll.id)

        assert " open>" not in block, "empty discussion should stay collapsed"
        assert 'hx-trigger="click once"' in block, (
            "empty discussion should stay lazy — no request per poll to render nothing"
        )


class TestSeasonalHistoryDefaultsExpanded:
    def test_history_card_renders_open(self, client: TestClient):
        """Render the macro directly — the card's markup is the contract here,
        and building enough tournament history through the DB to make it appear
        would test the query, not the default-expanded behaviour.

        Takes ``client`` only for its side effect: create_app() is where the
        Jinja filters used by this macro get registered onto the environment.
        """
        from core.deps import templates

        env = templates.env
        template = env.from_string(
            "{% from 'macros.html' import seasonal_history_card %}"
            "{{ seasonal_history_card(history) }}"
        )
        html = template.render(
            history=[
                {
                    "month_name": "August",
                    "year": 2025,
                    "tournament_id": 1,
                    "date": date(2025, 8, 16),
                    "lake_name": "Travis",
                    "ramp_name": "Mansfield",
                    "num_anglers": 20,
                    "num_limits": 4,
                    "num_zeros": 1,
                    "top_3_weights": [12.5, 11.0, 9.75],
                }
            ]
        )

        assert "<details open>" in html, "seasonal history card should render expanded"
        assert "August Tournament History" in html
