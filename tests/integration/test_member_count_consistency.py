"""Regression tests for the "active member" count.

The home page, the roster and /admin/users each used to compute this
independently and disagreed in production: the home page counted the seed
admin account as a member, and the roster applied no dues check at all. See
``core.helpers.members`` for the single shared definition they now share.
"""

import re
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.db_schema import Angler
from core.helpers.members import SEED_ADMIN_EMAIL, is_dues_current


def _stat_card_value(html: str, label: str) -> int:
    """Pull the number out of the roster stat card carrying ``label``."""
    match = re.search(
        r'<div class="h1 mb-0">(\d+)</div>\s*<div class="text-secondary">' + re.escape(label),
        html,
    )
    assert match is not None, f"no stat card labelled {label!r} in the rendered roster"
    return int(match.group(1))


def _add_angler(db_session: Session, **kwargs: object) -> Angler:
    angler = Angler(**kwargs)  # type: ignore[arg-type]
    db_session.add(angler)
    db_session.commit()
    db_session.refresh(angler)
    return angler


class TestDuesPredicate:
    """``is_dues_current`` accepts the shapes the different query paths yield."""

    def test_future_date_is_current(self) -> None:
        assert is_dues_current(date.today() + timedelta(days=1)) is True

    def test_today_is_current(self) -> None:
        assert is_dues_current(date.today()) is True

    def test_past_date_is_not_current(self) -> None:
        assert is_dues_current(date.today() - timedelta(days=1)) is False

    def test_none_is_not_current(self) -> None:
        """A member whose dues date was never filled in does not count."""
        assert is_dues_current(None) is False

    def test_iso_string_is_parsed(self) -> None:
        """Raw SQL rows hand back strings on some drivers."""
        assert is_dues_current((date.today() + timedelta(days=1)).isoformat()) is True
        assert is_dues_current((date.today() - timedelta(days=1)).isoformat()) is False

    def test_unparseable_string_is_not_current(self) -> None:
        assert is_dues_current("not-a-date") is False


class TestHomePageMemberCount:
    def test_seed_admin_is_not_counted_as_a_member(
        self, client: TestClient, db_session: Session, member_user: Angler
    ) -> None:
        """The seed admin is flagged member=True but is not a club member.

        Production's seed account is named "SABC Admin", so the historical
        ``name != 'Admin User'`` filters never matched it.
        """
        _add_angler(
            db_session,
            name="SABC Admin",
            email=SEED_ADMIN_EMAIL,
            member=True,
            is_admin=True,
            dues_paid_through=date(2030, 1, 1),
        )
        response = client.get("/")
        assert response.status_code == 200

        from core.helpers.members import active_member_criteria

        count = db_session.query(Angler).filter(*active_member_criteria()).count()
        assert count == 1, "only member_user should count, not the seed admin"

    def test_member_without_dues_date_is_not_counted(
        self, db_session: Session, member_user: Angler
    ) -> None:
        from core.helpers.members import active_member_criteria

        _add_angler(
            db_session,
            name="No Dues Date",
            email="nodues@example.com",
            member=True,
            dues_paid_through=None,
        )
        count = db_session.query(Angler).filter(*active_member_criteria()).count()
        assert count == 1

    def test_member_with_expired_dues_is_not_counted(
        self, db_session: Session, member_user: Angler
    ) -> None:
        from core.helpers.members import active_member_criteria

        _add_angler(
            db_session,
            name="Lapsed Member",
            email="lapsed@example.com",
            member=True,
            dues_paid_through=date.today() - timedelta(days=1),
        )
        count = db_session.query(Angler).filter(*active_member_criteria()).count()
        assert count == 1

    def test_angler_with_null_email_still_counts(
        self, db_session: Session, member_user: Angler
    ) -> None:
        """``email != 'admin@sabc.com'`` is NULL for NULL emails, dropping them."""
        from core.helpers.members import active_member_criteria

        _add_angler(
            db_session,
            name="No Email",
            email=None,
            member=True,
            dues_paid_through=date.today() + timedelta(days=30),
        )
        count = db_session.query(Angler).filter(*active_member_criteria()).count()
        assert count == 2


class TestRosterMemberCount:
    @pytest.fixture
    def roster_population(self, db_session: Session) -> None:
        """Two dues-current members, one lapsed, one guest, plus the seed admin."""
        _add_angler(
            db_session,
            name="Current One",
            email="c1@example.com",
            member=True,
            dues_paid_through=date.today() + timedelta(days=30),
        )
        _add_angler(
            db_session,
            name="Current Two",
            email="c2@example.com",
            member=True,
            dues_paid_through=date.today() + timedelta(days=30),
        )
        _add_angler(
            db_session,
            name="Missing Dues Date",
            email="m1@example.com",
            member=True,
            dues_paid_through=None,
        )
        _add_angler(db_session, name="A Guest", email="g1@example.com", member=False)
        _add_angler(
            db_session,
            name="SABC Admin",
            email=SEED_ADMIN_EMAIL,
            member=True,
            is_admin=True,
            dues_paid_through=date(2030, 1, 1),
        )

    def test_headline_counts_only_dues_current_members(
        self, client: TestClient, roster_population: None
    ) -> None:
        """Two of the three flagged members have current dues."""
        response = client.get("/roster")
        assert response.status_code == 200
        assert _stat_card_value(response.text, "Active Members") == 2
        assert _stat_card_value(response.text, "Dues Overdue") == 1
        assert _stat_card_value(response.text, "Guests") == 1

    def test_lapsed_member_is_reported_as_overdue_not_as_a_guest(
        self, client: TestClient, roster_population: None
    ) -> None:
        """The member/guest table split stays on the flag, so the member with no
        dues date is still listed under Members -- just counted as overdue."""
        response = client.get("/roster")
        assert response.status_code == 200
        assert "Dues Overdue" in response.text
        assert "Missing Dues Date" in response.text

    def test_seed_admin_is_absent_from_the_roster(
        self, client: TestClient, roster_population: None
    ) -> None:
        response = client.get("/roster")
        assert response.status_code == 200
        assert SEED_ADMIN_EMAIL not in response.text

    def test_angler_with_null_email_is_not_dropped(
        self, client: TestClient, db_session: Session
    ) -> None:
        _add_angler(
            db_session,
            name="Nullmail Member",
            email=None,
            member=True,
            dues_paid_through=date.today() + timedelta(days=30),
        )
        response = client.get("/roster")
        assert response.status_code == 200
        assert "Nullmail Member" in response.text
