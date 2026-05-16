"""Tests for session_version-based session invalidation.

Session cookies are signed but not server-validated. To allow a user to
revoke other sessions (e.g. after a suspected compromise), every angler
carries a ``session_version`` integer. It is embedded in the session at
login and checked on every authenticated request; bumping it on the
server invalidates older cookies.

These tests cover the contract:
* A fresh login embeds the current ``session_version``.
* Changing the password via the profile endpoint:
  - bumps ``anglers.session_version`` in the DB,
  - keeps the *current* request's session valid (the session cookie is
    refreshed in place), and
  - logs out *other* clients holding the previous version.
* Changing the password via the reset-token flow also bumps the version
  so any in-flight attacker session is revoked.
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.db_schema import Angler
from tests.conftest import login_user, post_with_csrf


def _new_client_for(app_client: TestClient) -> TestClient:
    """Return a TestClient that shares the same app but has its own cookie jar.

    We deliberately use the same ASGI app (and therefore the same in-memory
    test database) so that two clients can represent two browsers logged in
    as the same user. The first ``client`` fixture already drove the
    lifespan startup, so we don't need a context manager here -- we just
    want an independent cookie jar against the same app.
    """
    return TestClient(app_client.app)


class TestSessionVersionInvalidation:
    """Verify password-change revokes other sessions but keeps the current one."""

    def test_login_embeds_session_version(
        self,
        client: TestClient,
        member_user: Angler,
        test_password: str,
        db_session: Session,
    ):
        """A successful login must store the angler's current session_version."""
        assert member_user.email is not None
        assert login_user(client, member_user.email, test_password)

        # The current angler defaults to session_version=1; reading /profile
        # must succeed (i.e. get_current_user accepted the cookie).
        response = client.get("/profile", follow_redirects=False)
        assert response.status_code == 200

    def test_password_change_bumps_db_session_version(
        self,
        client: TestClient,
        member_user: Angler,
        test_password: str,
        db_session: Session,
    ):
        """Changing the password must increment anglers.session_version."""
        assert member_user.email is not None
        starting_version = member_user.session_version
        assert login_user(client, member_user.email, test_password)

        new_password = "BrandNewPassword9!@#$"
        response = post_with_csrf(
            client,
            "/profile/update",
            data={
                "email": member_user.email,
                "phone": member_user.phone or "",
                "year_joined": member_user.year_joined or 2023,
                "current_password": test_password,
                "new_password": new_password,
                "confirm_password": new_password,
            },
            follow_redirects=False,
        )
        assert response.status_code in (302, 303, 307)

        db_session.expire_all()
        refreshed = db_session.query(Angler).filter(Angler.id == member_user.id).first()
        assert refreshed is not None
        assert refreshed.session_version == starting_version + 1

    def test_password_change_keeps_current_session_alive(
        self,
        client: TestClient,
        member_user: Angler,
        test_password: str,
    ):
        """The browser that changes its own password must stay logged in."""
        assert member_user.email is not None
        assert login_user(client, member_user.email, test_password)

        new_password = "BrandNewPassword9!@#$"
        post_with_csrf(
            client,
            "/profile/update",
            data={
                "email": member_user.email,
                "phone": member_user.phone or "",
                "year_joined": member_user.year_joined or 2023,
                "current_password": test_password,
                "new_password": new_password,
                "confirm_password": new_password,
            },
            follow_redirects=False,
        )

        # Same client should still be authenticated on subsequent requests.
        response = client.get("/profile", follow_redirects=False)
        assert response.status_code == 200

    def test_password_change_logs_out_other_sessions(
        self,
        client: TestClient,
        member_user: Angler,
        test_password: str,
    ):
        """A *different* browser logged in as the same user gets logged out."""
        assert member_user.email is not None

        # Browser A (the user changing the password).
        assert login_user(client, member_user.email, test_password)

        # Browser B (the "other device") -- independent cookie jar.
        other_client = _new_client_for(client)
        assert login_user(other_client, member_user.email, test_password)

        # Confirm Browser B is initially authenticated.
        before = other_client.get("/profile", follow_redirects=False)
        assert before.status_code == 200

        # Browser A changes the password.
        new_password = "BrandNewPassword9!@#$"
        response = post_with_csrf(
            client,
            "/profile/update",
            data={
                "email": member_user.email,
                "phone": member_user.phone or "",
                "year_joined": member_user.year_joined or 2023,
                "current_password": test_password,
                "new_password": new_password,
                "confirm_password": new_password,
            },
            follow_redirects=False,
        )
        assert response.status_code in (302, 303, 307)

        # Browser B's next request should be treated as anonymous: the
        # session_version it carries is now stale.
        after = other_client.get("/profile", follow_redirects=False)
        assert after.status_code in (302, 303, 307)
        location = after.headers.get("location", "")
        assert "/login" in location

    def test_stale_session_version_is_rejected(
        self,
        client: TestClient,
        member_user: Angler,
        test_password: str,
        db_session: Session,
    ):
        """Bumping session_version out-of-band invalidates the cookie."""
        assert member_user.email is not None
        assert login_user(client, member_user.email, test_password)

        # Out-of-band: bump session_version on the DB row (simulating another
        # process). Existing cookie now references the stale version.
        refreshed = db_session.query(Angler).filter(Angler.id == member_user.id).first()
        assert refreshed is not None
        refreshed.session_version = (refreshed.session_version or 1) + 1
        db_session.commit()

        # Next authenticated request from the same client should be rejected.
        response = client.get("/profile", follow_redirects=False)
        assert response.status_code in (302, 303, 307)
        assert "/login" in response.headers.get("location", "")

    def test_reset_token_flow_bumps_session_version(
        self,
        client: TestClient,
        member_user: Angler,
        db_session: Session,
    ):
        """The forgot-password reset flow must also bump session_version."""
        from core.email import create_password_reset_token

        assert member_user.email is not None
        starting_version = member_user.session_version

        # Issue a real reset token via the production helper.
        token = create_password_reset_token(member_user.id, member_user.email)
        assert token is not None

        new_password = "ResetPasswordViaToken9!@#"
        response = post_with_csrf(
            client,
            "/reset-password",
            data={
                "token": token,
                "password": new_password,
                "password_confirm": new_password,
            },
            follow_redirects=False,
        )
        # The route redirects either way; what matters is the DB effect.
        assert response.status_code in (302, 303, 307)

        db_session.expire_all()
        refreshed = db_session.query(Angler).filter(Angler.id == member_user.id).first()
        assert refreshed is not None
        assert refreshed.session_version == starting_version + 1
