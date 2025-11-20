"""Phase 10: Event Deletion and Password Reset Tests

Tests for event deletion workflows, password reset flow, and public endpoints.
Focuses on low-coverage areas in event management and authentication flows.
"""

from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import bcrypt
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.db_schema import (
    Angler,
    Event,
    Poll,
    PollOption,
    PollVote,
    Result,
    Tournament,
)
from core.helpers.timezone import now_local
from tests.conftest import post_with_csrf


class TestEventDeletion:
    """Tests for event deletion endpoints."""

    def test_admin_can_delete_event_without_results(
        self,
        admin_client: TestClient,
        db_session: Session,
    ):
        """Test that admins can delete events without tournament results."""
        # Create event without tournament
        future_date = now_local().date() + timedelta(days=60)
        event = Event(
            date=future_date,
            name="Deletable Event",
            event_type="sabc_tournament",
            year=future_date.year,
        )
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)
        event_id = event.id

        response = admin_client.delete(f"/admin/events/{event_id}")

        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True

        # Verify event was deleted
        db_session.expire_all()
        deleted_event = db_session.query(Event).filter(Event.id == event_id).first()
        assert deleted_event is None

    def test_cannot_delete_event_with_results(
        self,
        admin_client: TestClient,
        test_event: Event,
        test_tournament: Tournament,
        member_user: Angler,
        db_session: Session,
    ):
        """Test that events with tournament results cannot be deleted."""
        # Add a result
        result = Result(
            tournament_id=test_tournament.id,
            angler_id=member_user.id,
            num_fish=3,
            total_weight=Decimal("10.5"),
        )
        db_session.add(result)
        db_session.commit()

        response = admin_client.delete(f"/admin/events/{test_event.id}")

        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "results" in data["error"].lower()

    def test_delete_event_removes_polls_and_votes(
        self,
        admin_client: TestClient,
        test_event: Event,
        test_poll: Poll,
        test_poll_option: PollOption,
        member_user: Angler,
        db_session: Session,
    ):
        """Test that deleting event also deletes associated polls and votes."""
        # Add a vote
        vote = PollVote(
            poll_id=test_poll.id,
            option_id=test_poll_option.id,
            angler_id=member_user.id,
            voted_at=now_local(),
        )
        db_session.add(vote)
        db_session.commit()
        vote_id = vote.id
        poll_id = test_poll.id
        option_id = test_poll_option.id

        response = admin_client.delete(f"/admin/events/{test_event.id}")

        assert response.status_code == 200

        # Verify poll, options, and votes were deleted
        db_session.expire_all()
        assert db_session.query(PollVote).filter(PollVote.id == vote_id).first() is None
        assert db_session.query(PollOption).filter(PollOption.id == option_id).first() is None
        assert db_session.query(Poll).filter(Poll.id == poll_id).first() is None

    def test_delete_event_removes_tournament_without_results(
        self,
        admin_client: TestClient,
        test_event: Event,
        test_tournament: Tournament,
        db_session: Session,
    ):
        """Test that deleting event removes tournament when no results exist."""
        tournament_id = test_tournament.id

        response = admin_client.delete(f"/admin/events/{test_event.id}")

        assert response.status_code == 200

        # Verify tournament was deleted
        db_session.expire_all()
        deleted_tournament = (
            db_session.query(Tournament).filter(Tournament.id == tournament_id).first()
        )
        assert deleted_tournament is None

    def test_delete_event_post_method(
        self,
        admin_client: TestClient,
        db_session: Session,
    ):
        """Test event deletion via POST (for form submissions)."""
        future_date = now_local().date() + timedelta(days=70)
        event = Event(
            date=future_date,
            name="Delete via POST",
            event_type="holiday",
            year=future_date.year,
        )
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)
        event_id = event.id

        response = post_with_csrf(
            admin_client,
            f"/admin/events/{event_id}/delete",
            data={},
            follow_redirects=False,
        )

        assert response.status_code in [302, 303]
        assert "success" in response.headers.get("location", "").lower()

        # Verify deletion
        db_session.expire_all()
        assert db_session.query(Event).filter(Event.id == event_id).first() is None

    def test_delete_nonexistent_event_succeeds(
        self,
        admin_client: TestClient,
        db_session: Session,
    ):
        """Test that deleting nonexistent event returns success (idempotent)."""
        response = admin_client.delete("/admin/events/99999")

        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True

    def test_non_admin_cannot_delete_event(
        self,
        member_client: TestClient,
        test_event: Event,
        db_session: Session,
    ):
        """Test that non-admins cannot delete events."""
        response = member_client.delete(
            f"/admin/events/{test_event.id}",
            follow_redirects=False,
        )

        assert response.status_code in [302, 303, 403]


class TestPasswordResetRequest:
    """Tests for password reset request flow."""

    def test_forgot_password_page_loads(
        self,
        client: TestClient,
    ):
        """Test that forgot password page loads successfully."""
        response = client.get("/forgot-password")

        assert response.status_code == 200
        assert b"password" in response.content.lower()

    @patch("routes.password_reset.request_reset.send_password_reset_email")
    @patch("routes.password_reset.request_reset.create_password_reset_token")
    def test_request_password_reset_for_valid_email(
        self,
        mock_create_token: MagicMock,
        mock_send_email: MagicMock,
        client: TestClient,
        member_user: Angler,
        db_session: Session,
    ):
        """Test requesting password reset for valid email."""
        mock_create_token.return_value = "test-token-123"
        mock_send_email.return_value = True

        response = post_with_csrf(
            client,
            "/forgot-password",
            data={"email": member_user.email},
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert "success" in response.headers.get("location", "").lower()

        # Verify email was sent
        mock_create_token.assert_called_once_with(member_user.id, member_user.email)
        mock_send_email.assert_called_once()

    @patch("routes.password_reset.request_reset.send_password_reset_email")
    @patch("routes.password_reset.request_reset.create_password_reset_token")
    def test_request_password_reset_for_nonexistent_email(
        self,
        mock_create_token: MagicMock,
        mock_send_email: MagicMock,
        client: TestClient,
        db_session: Session,
    ):
        """Test requesting password reset for nonexistent email (should not reveal)."""
        response = post_with_csrf(
            client,
            "/forgot-password",
            data={"email": "nonexistent@example.com"},
            follow_redirects=False,
        )

        # Should still show success to prevent email enumeration
        assert response.status_code == 302
        assert "success" in response.headers.get("location", "").lower()

        # But should not send email
        mock_create_token.assert_not_called()
        mock_send_email.assert_not_called()

    def test_request_password_reset_with_empty_email(
        self,
        client: TestClient,
    ):
        """Test requesting password reset with empty email."""
        response = post_with_csrf(
            client,
            "/forgot-password",
            data={"email": ""},
            follow_redirects=False,
        )

        assert response.status_code in [302, 303]
        assert "error" in response.headers.get("location", "").lower()

    @patch("routes.password_reset.request_reset.send_password_reset_email")
    @patch("routes.password_reset.request_reset.create_password_reset_token")
    def test_request_password_reset_normalizes_email(
        self,
        mock_create_token: MagicMock,
        mock_send_email: MagicMock,
        client: TestClient,
        member_user: Angler,
        db_session: Session,
    ):
        """Test that email is normalized (lowercase, stripped)."""
        mock_create_token.return_value = "test-token-456"
        mock_send_email.return_value = True

        # Send with uppercase and whitespace
        email_upper = member_user.email.upper() if member_user.email else ""
        response = post_with_csrf(
            client,
            "/forgot-password",
            data={"email": f"  {email_upper}  "},
            follow_redirects=False,
        )

        assert response.status_code == 302
        mock_create_token.assert_called_once_with(member_user.id, member_user.email)


class TestPasswordResetCompletion:
    """Tests for password reset completion flow."""

    @patch("routes.password_reset.reset_password.verify_reset_token")
    def test_reset_password_page_loads_with_valid_token(
        self,
        mock_verify: MagicMock,
        client: TestClient,
    ):
        """Test that reset password page loads with valid token."""
        mock_verify.return_value = {
            "user_id": 1,
            "email": "test@example.com",
            "name": "Test User",
            "expires_at": now_local() + timedelta(hours=1),
        }

        response = client.get("/reset-password?token=valid-token")

        assert response.status_code == 200
        assert b"password" in response.content.lower()
        mock_verify.assert_called_once_with("valid-token")

    @patch("routes.password_reset.reset_password.verify_reset_token")
    def test_reset_password_page_rejects_invalid_token(
        self,
        mock_verify: MagicMock,
        client: TestClient,
    ):
        """Test that invalid token redirects to forgot password."""
        mock_verify.return_value = None

        response = client.get("/reset-password?token=invalid-token", follow_redirects=False)

        assert response.status_code in [302, 303]
        assert "forgot-password" in response.headers.get("location", "")

    @patch("routes.password_reset.reset_password.use_reset_token")
    @patch("routes.password_reset.reset_password.verify_reset_token")
    def test_reset_password_successfully(
        self,
        mock_verify: MagicMock,
        mock_use: MagicMock,
        client: TestClient,
        member_user: Angler,
        db_session: Session,
    ):
        """Test successfully resetting password."""
        mock_verify.return_value = {
            "user_id": member_user.id,
            "email": member_user.email,
            "name": member_user.name,
            "expires_at": now_local() + timedelta(hours=1),
        }

        new_password = "NewSecureP@ssw0rd!"  # Avoid sequential numbers

        response = post_with_csrf(
            client,
            "/reset-password",
            data={
                "token": "valid-token",
                "password": new_password,
                "password_confirm": new_password,
            },
            follow_redirects=False,
        )

        assert response.status_code in [302, 303]
        assert "login" in response.headers.get("location", "")
        assert "success" in response.headers.get("location", "").lower()

        # Verify password was changed
        db_session.refresh(member_user)
        assert member_user.password_hash is not None
        assert bcrypt.checkpw(new_password.encode(), member_user.password_hash.encode())

        # Verify token was marked as used
        mock_use.assert_called_once_with("valid-token")

    @patch("routes.password_reset.reset_password.verify_reset_token")
    def test_reset_password_fails_with_mismatched_passwords(
        self,
        mock_verify: MagicMock,
        client: TestClient,
    ):
        """Test that mismatched passwords are rejected."""
        mock_verify.return_value = {
            "user_id": 1,
            "email": "test@example.com",
            "name": "Test",
            "expires_at": now_local() + timedelta(hours=1),
        }

        response = post_with_csrf(
            client,
            "/reset-password",
            data={
                "token": "valid-token",
                "password": "Password123!",
                "password_confirm": "DifferentPassword123!",
            },
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert "error" in response.headers.get("location", "").lower()
        assert "reset-password" in response.headers.get("location", "")

    @patch("routes.password_reset.reset_password.verify_reset_token")
    def test_reset_password_fails_with_short_password(
        self,
        mock_verify: MagicMock,
        client: TestClient,
    ):
        """Test that short passwords are rejected."""
        mock_verify.return_value = {
            "user_id": 1,
            "email": "test@example.com",
            "name": "Test",
            "expires_at": now_local() + timedelta(hours=1),
        }

        short_password = "Short1!"

        response = post_with_csrf(
            client,
            "/reset-password",
            data={
                "token": "valid-token",
                "password": short_password,
                "password_confirm": short_password,
            },
            follow_redirects=False,
        )

        # FastAPI validation may return 422, or route may return 303 with error
        assert response.status_code in [303, 422]
        if response.status_code == 303:
            assert "error" in response.headers.get("location", "").lower()

    @patch("routes.password_reset.reset_password.verify_reset_token")
    def test_reset_password_fails_with_expired_token(
        self,
        mock_verify: MagicMock,
        client: TestClient,
    ):
        """Test that expired token is rejected."""
        mock_verify.return_value = None  # Expired tokens return None

        # Use a password that passes basic validation
        response = post_with_csrf(
            client,
            "/reset-password",
            data={
                "token": "expired-token",
                "password": "ValidPassword2024!",
                "password_confirm": "ValidPassword2024!",
            },
            follow_redirects=False,
        )

        # Should redirect with error (may go to forgot-password or reset-password with error)
        assert response.status_code in [302, 303]
        location = response.headers.get("location", "")
        # Either redirects to forgot-password or back to reset-password with error
        assert "forgot-password" in location or (
            "reset-password" in location and "error" in location
        )

    def test_password_reset_help_page_loads(
        self,
        client: TestClient,
    ):
        """Test that password reset help page loads."""
        response = client.get("/reset-password/help")

        assert response.status_code == 200


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check_returns_healthy_status(
        self,
        client: TestClient,
        db_session: Session,
    ):
        """Test that health check returns healthy status when database is connected."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        assert "angler_count" in data
        assert "timestamp" in data

    @patch("routes.pages.health.get_session")
    def test_health_check_returns_unhealthy_on_db_error(
        self,
        mock_get_session: MagicMock,
        client: TestClient,
    ):
        """Test that health check returns unhealthy status on database error."""
        # Simulate database error
        mock_get_session.side_effect = Exception("Database connection failed")

        response = client.get("/health")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["database"] == "disconnected"
        assert "error" in data
        assert "timestamp" in data
