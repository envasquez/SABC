"""Auth registration and profile tests."""

from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.db_schema import Angler
from tests.conftest import post_with_csrf

VALID_PASSWORD = "TestPassword!@#$Secure9"


class TestRegistration:
    """Test user registration."""

    def test_registration_page_loads(self, client: TestClient):
        """Test registration page loads."""
        response = client.get("/auth/register")
        assert response.status_code == 200


class TestDuplicateEmailRegistration:
    """Registering an address that already exists must fail gracefully.

    Regression coverage for a production IntegrityError: a duplicate signup
    reached the database and surfaced to the user as a generic "Registration
    failed", with no indication that they already had an account.
    """

    def test_duplicate_email_is_rejected_gracefully(
        self, client: TestClient, db_session: Session, regular_user: Angler
    ):
        """The pre-check path explains the situation and points at sign-in."""
        response = post_with_csrf(
            client,
            "/register",
            data={
                "first_name": "Test",
                "last_name": "User",
                "email": regular_user.email,
                "password": VALID_PASSWORD,
            },
        )

        assert response.status_code == 200
        assert "already registered" in response.text
        assert 'href="/login"' in response.text
        # No duplicate row was created.
        assert db_session.query(Angler).filter(Angler.email == regular_user.email).count() == 1

    def test_duplicate_email_is_matched_case_insensitively(
        self, client: TestClient, db_session: Session, regular_user: Angler
    ):
        """Emails are normalised before lookup, so casing cannot bypass the check."""
        assert regular_user.email is not None
        response = post_with_csrf(
            client,
            "/register",
            data={
                "first_name": "Test",
                "last_name": "User",
                "email": regular_user.email.upper(),
                "password": VALID_PASSWORD,
            },
        )

        assert response.status_code == 200
        assert "already registered" in response.text
        assert db_session.query(Angler).count() == 1

    def test_duplicate_email_form_does_not_echo_the_address(
        self, client: TestClient, regular_user: Angler
    ):
        """The rejected address is not pre-filled, to discourage a blind resubmit."""
        response = post_with_csrf(
            client,
            "/register",
            data={
                "first_name": "Test",
                "last_name": "User",
                "email": regular_user.email,
                "password": VALID_PASSWORD,
            },
        )

        assert response.status_code == 200
        assert f'value="{regular_user.email}"' not in response.text

    def test_concurrent_duplicate_registration_is_handled(
        self, client: TestClient, db_session: Session, regular_user: Angler
    ):
        """A duplicate that slips past the pre-check is caught at the constraint.

        Two submits of the same address can both clear the existence check and
        collide on the unique index. Simulated here by making the first Angler
        lookup miss, exactly as it would if the competing transaction had not
        committed yet, while leaving the real constraint in place.
        """
        real_query = Session.query
        calls = {"count": 0}

        class _MissedLookup:
            """Stand-in for a query that finds nothing."""

            def filter(self, *args, **kwargs):
                return self

            def first(self):
                return None

        def fake_query(self, *entities, **kwargs):
            if entities and entities[0] is Angler and calls["count"] == 0:
                calls["count"] += 1
                return _MissedLookup()
            return real_query(self, *entities, **kwargs)

        with patch.object(Session, "query", fake_query):
            response = post_with_csrf(
                client,
                "/register",
                data={
                    "first_name": "Test",
                    "last_name": "User",
                    "email": regular_user.email,
                    "password": VALID_PASSWORD,
                },
            )

        assert calls["count"] == 1, "the pre-check lookup was not exercised"
        # The collision is reported as a duplicate, not as a server failure.
        assert response.status_code == 200
        assert "already registered" in response.text
        assert "Registration failed" not in response.text
        # And no partial row survived the rolled-back transaction.
        assert db_session.query(Angler).filter(Angler.email == regular_user.email).count() == 1

    def test_unrelated_integrity_error_is_not_reported_as_duplicate(
        self, client: TestClient, regular_user: Angler
    ):
        """A non-email constraint failure must still be treated as a real error."""
        from sqlalchemy.exc import IntegrityError

        def boom(self, *args, **kwargs):
            raise IntegrityError(
                "INSERT INTO anglers ...",
                {},
                Exception('null value in column "name" violates not-null constraint'),
            )

        with patch.object(Session, "flush", boom):
            response = post_with_csrf(
                client,
                "/register",
                data={
                    "first_name": "Brand",
                    "last_name": "New",
                    "email": "brandnew@example.com",
                    "password": VALID_PASSWORD,
                },
            )

        assert response.status_code == 200
        assert "Registration failed" in response.text
        assert "already registered" not in response.text
