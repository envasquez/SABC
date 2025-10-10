"""Integration tests for password reset flow.

This test suite ensures that the complete password reset flow works correctly,
including CSRF exemption and token-based security.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import bcrypt
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.db_schema import Angler
from core.email import create_password_reset_token


class TestPasswordResetFlow:
    """Test suite for password reset flow integration tests."""

    def test_password_reset_without_csrf_token_succeeds(
        self, client: TestClient, db_session: Session
    ):
        """Test that password reset POST works without CSRF token.

        This is a critical test that ensures password reset is exempt from CSRF
        validation, preventing the production bug where users couldn't reset
        their passwords due to missing CSRF cookies.
        """
        # Create test user
        user = Angler(
            name="Test User",
            email="test@example.com",
            password_hash=bcrypt.hashpw(b"OldPassword4!", bcrypt.gensalt()).decode(),
            member=True,
            is_admin=False,
            created_at=datetime.now(tz=timezone.utc),
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Generate valid reset token
        token = create_password_reset_token(user.id, user.email)  # type: ignore[arg-type]

        # POST password reset WITHOUT CSRF token (simulates user from email link)
        response = client.post(
            "/reset-password",
            data={
                "token": str(token),
                "password": "NewPassword4!",
                "password_confirm": "NewPassword4!",
            },
            follow_redirects=False,
        )

        # Should succeed (redirect to login) without CSRF token
        assert response.status_code in [302, 303], (
            f"Password reset should succeed without CSRF token. "
            f"Status: {response.status_code}, Body: {response.text}"
        )
        assert "/login" in response.headers.get("location", "")

        # Verify password was actually changed in database
        db_session.refresh(user)
        assert bcrypt.checkpw(b"NewPassword4!", user.password_hash.encode())  # type: ignore[union-attr]

    def test_password_reset_get_renders_form(self, client: TestClient, db_session: Session):
        """Test that GET /reset-password renders the password reset form."""
        # Create test user
        user = Angler(
            name="Jane Doe",
            email="jane@example.com",
            password_hash=bcrypt.hashpw(b"OldPassword4!", bcrypt.gensalt()).decode(),
            member=True,
            is_admin=False,
            created_at=datetime.now(tz=timezone.utc),
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Generate valid reset token
        token = create_password_reset_token(user.id, user.email)  # type: ignore[arg-type]

        # GET password reset form
        response = client.get(f"/reset-password?token={token}")

        assert response.status_code == 200
        assert "Reset Your Password" in response.text
        assert "Jane Doe" in response.text  # Should show user's name
        if token:
            assert token in response.text  # Token should be in hidden field

    def test_password_reset_with_invalid_token_fails(self, client: TestClient, db_session: Session):
        """Test that password reset with invalid token fails."""
        response = client.post(
            "/reset-password",
            data={
                "token": "invalid-token-12345",
                "password": "NewPassword4!",
                "password_confirm": "NewPassword4!",
            },
            follow_redirects=False,
        )

        # Should redirect with error
        assert response.status_code in [302, 303]
        assert "/forgot-password" in response.headers.get("location", "")

    def test_password_reset_with_expired_token_fails(
        self, client: TestClient, db_session: Session, monkeypatch
    ):
        """Test that password reset with expired token fails."""
        # Create test user
        user = Angler(
            name="Test User",
            email="test@example.com",
            password_hash=bcrypt.hashpw(b"OldPassword4!", bcrypt.gensalt()).decode(),
            member=True,
            is_admin=False,
            created_at=datetime.now(tz=timezone.utc),
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Generate token
        token = create_password_reset_token(user.id, user.email)  # type: ignore[arg-type]

        # Mock time to be 2 hours in the future (tokens expire in 1 hour)
        future_time = datetime.now(tz=timezone.utc) + timedelta(hours=2)
        with patch("core.email.tokens.datetime") as mock_datetime:
            mock_datetime.now.return_value = future_time
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            response = client.post(
                "/reset-password",
                data={
                    "token": str(token) if token else "",
                    "password": "NewPassword4!",
                    "password_confirm": "NewPassword4!",
                },
                follow_redirects=False,
            )

            # Should redirect with error
            assert response.status_code in [302, 303]
            assert "/forgot-password" in response.headers.get("location", "")

    def test_password_reset_with_mismatched_passwords_fails(
        self, client: TestClient, db_session: Session
    ):
        """Test that password reset with mismatched passwords fails."""
        # Create test user
        user = Angler(
            name="Test User",
            email="test@example.com",
            password_hash=bcrypt.hashpw(b"OldPassword4!", bcrypt.gensalt()).decode(),
            member=True,
            is_admin=False,
            created_at=datetime.now(tz=timezone.utc),
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Generate valid reset token
        token = create_password_reset_token(user.id, user.email)  # type: ignore[arg-type]

        response = client.post(
            "/reset-password",
            data={
                "token": str(token) if token else "",
                "password": "NewPassword4!",
                "password_confirm": "DifferentPassword!",
            },
            follow_redirects=False,
        )

        # Should redirect back to reset form with error
        assert response.status_code in [302, 303]
        assert "/reset-password" in response.headers.get("location", "")

    def test_password_reset_with_short_password_fails(
        self, client: TestClient, db_session: Session
    ):
        """Test that password reset with password < 8 chars fails."""
        # Create test user
        user = Angler(
            name="Test User",
            email="test@example.com",
            password_hash=bcrypt.hashpw(b"OldPassword4!", bcrypt.gensalt()).decode(),
            member=True,
            is_admin=False,
            created_at=datetime.now(tz=timezone.utc),
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Generate valid reset token
        token = create_password_reset_token(user.id, user.email)  # type: ignore[arg-type]

        response = client.post(
            "/reset-password",
            data={
                "token": str(token) if token else "",
                "password": "Short1!",
                "password_confirm": "Short1!",
            },
            follow_redirects=False,
        )

        # Should redirect back to reset form with error
        assert response.status_code in [302, 303]
        assert "/reset-password" in response.headers.get("location", "")

    def test_password_reset_token_single_use(self, client: TestClient, db_session: Session):
        """Test that password reset token can only be used once."""
        # Create test user
        user = Angler(
            name="Test User",
            email="test@example.com",
            password_hash=bcrypt.hashpw(b"OldPassword4!", bcrypt.gensalt()).decode(),
            member=True,
            is_admin=False,
            created_at=datetime.now(tz=timezone.utc),
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Generate valid reset token
        token = create_password_reset_token(user.id, user.email)  # type: ignore[arg-type]

        # First use should succeed
        response1 = client.post(
            "/reset-password",
            data={
                "token": str(token) if token else "",
                "password": "NewPassword4!",
                "password_confirm": "NewPassword4!",
            },
            follow_redirects=False,
        )
        assert response1.status_code in [302, 303]
        assert "/login" in response1.headers.get("location", "")

        # Second use with same token should fail
        response2 = client.post(
            "/reset-password",
            data={
                "token": str(token) if token else "",
                "password": "AnotherPassword4!",
                "password_confirm": "AnotherPassword4!",
            },
            follow_redirects=False,
        )
        assert response2.status_code in [302, 303]
        assert "/forgot-password" in response2.headers.get("location", "")

    def test_complete_password_reset_flow_without_cookies(
        self, client: TestClient, db_session: Session
    ):
        """Test complete password reset flow simulating user from different device.

        This test simulates the exact scenario that caused the production bug:
        1. User requests password reset
        2. User clicks link from email (potentially on different device/browser)
        3. User fills out form and submits
        4. Should succeed without requiring CSRF cookie
        """
        # Create test user
        user = Angler(
            name="Bob Smith",
            email="bob@example.com",
            password_hash=bcrypt.hashpw(b"OldPassword4!", bcrypt.gensalt()).decode(),
            member=True,
            is_admin=False,
            created_at=datetime.now(tz=timezone.utc),
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Step 1: Request password reset (this would send email in production)
        with patch("routes.password_reset.request_reset.send_password_reset_email"):
            response = client.post(
                "/forgot-password",
                data={"email": "bob@example.com"},
                follow_redirects=False,
            )
            assert response.status_code in [302, 303]

        # Step 2: Generate token (in production, this would be in the email)
        token = create_password_reset_token(user.id, user.email)  # type: ignore[arg-type]

        # Step 3: User clicks link from email - GET the form
        # Simulate fresh browser session with no cookies by using a new client

        def mock_get_session():
            """Mock get_session for fresh client."""
            try:
                yield db_session
            finally:
                pass

        with patch("core.db_schema.session.get_session", mock_get_session):
            with patch("core.db_schema.get_session", mock_get_session):
                from app_routes import register_routes
                from app_setup import create_app

                fresh_app = create_app()
                register_routes(fresh_app)

                with TestClient(fresh_app) as fresh_client:
                    # GET form
                    get_response = fresh_client.get(f"/reset-password?token={token}")
                    assert get_response.status_code == 200

                    # Step 4: Submit form WITHOUT any CSRF token
                    post_response = fresh_client.post(
                        "/reset-password",
                        data={
                            "token": str(token) if token else "",
                            "password": "BrandNewPassword4!",
                            "password_confirm": "BrandNewPassword4!",
                        },
                        follow_redirects=False,
                    )

                    # CRITICAL: This must succeed
                    assert post_response.status_code in [302, 303], (
                        f"Password reset from email link must work without CSRF cookie. "
                        f"Status: {post_response.status_code}"
                    )
                    assert "/login" in post_response.headers.get("location", "")

        # Verify password was changed
        db_session.refresh(user)
        assert bcrypt.checkpw(b"BrandNewPassword4!", user.password_hash.encode())  # type: ignore[union-attr]

    def test_password_reset_logs_security_event(self, client: TestClient, db_session: Session):
        """Test that successful password reset logs security event."""
        # Create test user
        user = Angler(
            name="Test User",
            email="test@example.com",
            password_hash=bcrypt.hashpw(b"OldPassword4!", bcrypt.gensalt()).decode(),
            member=True,
            is_admin=False,
            created_at=datetime.now(tz=timezone.utc),
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Generate valid reset token
        token = create_password_reset_token(user.id, user.email)  # type: ignore[arg-type]

        # Mock security logging
        with patch("routes.password_reset.reset_password.log_security_event") as mock_log:
            response = client.post(
                "/reset-password",
                data={
                    "token": str(token) if token else "",
                    "password": "NewPassword4!",
                    "password_confirm": "NewPassword4!",
                },
                follow_redirects=False,
            )

            assert response.status_code in [302, 303]
            # Verify security event was logged
            assert mock_log.called
            call_kwargs = mock_log.call_args.kwargs
            assert call_kwargs["user_id"] == user.id
            assert call_kwargs["user_email"] == user.email
            assert call_kwargs["details"]["success"] is True
