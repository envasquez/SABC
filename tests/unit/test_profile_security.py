"""Unit tests for profile security functions (password change, account deletion)."""

from unittest.mock import MagicMock, Mock, patch

from routes.auth.profile_update.password import handle_password_change


class TestHandlePasswordChange:
    """Tests for handle_password_change function."""

    @patch("routes.auth.profile_update.password.get_session")
    @patch("routes.auth.profile_update.password.log_security_event")
    @patch("routes.auth.profile_update.password.bcrypt")
    @patch("routes.auth.profile_update.password.validate_password_strength")
    def test_successful_password_change(
        self,
        mock_validate: Mock,
        mock_bcrypt: Mock,
        mock_log: Mock,
        mock_get_session: Mock,
    ):
        """Test successful password change with valid credentials."""
        # Mock password validation
        mock_validate.return_value = (True, None)

        # Mock bcrypt
        mock_bcrypt.checkpw.return_value = True
        mock_bcrypt.gensalt.return_value = b"$2b$12$fakesalt"
        mock_bcrypt.hashpw.return_value = b"$2b$12$fakehash"

        # Mock database
        mock_session = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.password_hash = "$2b$12$oldhash"
        mock_session.query().filter().first.return_value = mock_user
        mock_get_session.return_value.__enter__.return_value = mock_session

        user = {"id": 1, "email": "test@example.com"}
        success, error = handle_password_change(
            user, "current123", "NewPass123!", "NewPass123!", "192.168.1.1"
        )

        assert success is True
        assert error is None
        mock_bcrypt.checkpw.assert_called_once()
        mock_log.assert_called_once()

    @patch("routes.auth.profile_update.password.validate_password_strength")
    def test_returns_error_for_missing_fields(self, mock_validate: Mock):
        """Test returns error when required fields are missing."""
        user = {"id": 1, "email": "test@example.com"}

        # Missing current password
        success, error = handle_password_change(user, "", "NewPass123!", "NewPass123!", "1.1.1.1")
        assert success is False
        assert error is not None
        assert "All password fields are required" in error

        # Missing new password
        success, error = handle_password_change(user, "current123", "", "NewPass123!", "1.1.1.1")
        assert success is False
        assert error is not None
        assert "All password fields are required" in error

        # Missing confirm password
        success, error = handle_password_change(user, "current123", "NewPass123!", "", "1.1.1.1")
        assert success is False
        assert error is not None
        assert "All password fields are required" in error

    @patch("routes.auth.profile_update.password.validate_password_strength")
    def test_returns_error_for_weak_password(self, mock_validate: Mock):
        """Test returns error when new password is weak."""
        mock_validate.return_value = (False, "Password must be at least 8 characters")

        user = {"id": 1, "email": "test@example.com"}
        success, error = handle_password_change(user, "current123", "weak", "weak", "1.1.1.1")

        assert success is False
        assert error == "Password must be at least 8 characters"
        mock_validate.assert_called_once_with("weak")

    @patch("routes.auth.profile_update.password.validate_password_strength")
    def test_returns_error_for_password_mismatch(self, mock_validate: Mock):
        """Test returns error when new password and confirmation don't match."""
        mock_validate.return_value = (True, None)

        user = {"id": 1, "email": "test@example.com"}
        success, error = handle_password_change(
            user, "current123", "NewPass123!", "Different123!", "1.1.1.1"
        )

        assert success is False
        assert error == "New passwords do not match"

    @patch("routes.auth.profile_update.password.get_session")
    @patch("routes.auth.profile_update.password.validate_password_strength")
    def test_returns_error_for_user_not_found(self, mock_validate: Mock, mock_get_session: Mock):
        """Test returns error when user doesn't exist in database."""
        mock_validate.return_value = (True, None)

        # Mock database - user not found
        mock_session = MagicMock()
        mock_session.query().filter().first.return_value = None
        mock_get_session.return_value.__enter__.return_value = mock_session

        user = {"id": 999, "email": "test@example.com"}
        success, error = handle_password_change(
            user, "current123", "NewPass123!", "NewPass123!", "1.1.1.1"
        )

        assert success is False
        assert error == "User not found"

    @patch("routes.auth.profile_update.password.get_session")
    @patch("routes.auth.profile_update.password.validate_password_strength")
    def test_returns_error_for_user_without_password(
        self, mock_validate: Mock, mock_get_session: Mock
    ):
        """Test returns error when user has no password hash."""
        mock_validate.return_value = (True, None)

        # Mock database - user exists but has no password
        mock_session = MagicMock()
        mock_user = MagicMock()
        mock_user.password_hash = None
        mock_session.query().filter().first.return_value = mock_user
        mock_get_session.return_value.__enter__.return_value = mock_session

        user = {"id": 1, "email": "test@example.com"}
        success, error = handle_password_change(
            user, "current123", "NewPass123!", "NewPass123!", "1.1.1.1"
        )

        assert success is False
        assert error == "User not found"

    @patch("routes.auth.profile_update.password.get_session")
    @patch("routes.auth.profile_update.password.bcrypt")
    @patch("routes.auth.profile_update.password.validate_password_strength")
    def test_returns_error_for_incorrect_current_password(
        self, mock_validate: Mock, mock_bcrypt: Mock, mock_get_session: Mock
    ):
        """Test returns error when current password is incorrect."""
        mock_validate.return_value = (True, None)
        mock_bcrypt.checkpw.return_value = False  # Current password wrong

        # Mock database
        mock_session = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.password_hash = "$2b$12$oldhash"
        mock_session.query().filter().first.return_value = mock_user
        mock_get_session.return_value.__enter__.return_value = mock_session

        user = {"id": 1, "email": "test@example.com"}
        success, error = handle_password_change(
            user, "wrongpassword", "NewPass123!", "NewPass123!", "1.1.1.1"
        )

        assert success is False
        assert error == "Current password is incorrect"

    @patch("routes.auth.profile_update.password.get_session")
    @patch("routes.auth.profile_update.password.log_security_event")
    @patch("routes.auth.profile_update.password.bcrypt")
    @patch("routes.auth.profile_update.password.validate_password_strength")
    def test_logs_security_event_on_success(
        self,
        mock_validate: Mock,
        mock_bcrypt: Mock,
        mock_log: Mock,
        mock_get_session: Mock,
    ):
        """Test logs security event when password change succeeds."""
        from core.helpers.logging import SecurityEvent

        mock_validate.return_value = (True, None)
        mock_bcrypt.checkpw.return_value = True
        mock_bcrypt.gensalt.return_value = b"$2b$12$fakesalt"
        mock_bcrypt.hashpw.return_value = b"$2b$12$fakehash"

        mock_session = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.password_hash = "$2b$12$oldhash"
        mock_session.query().filter().first.return_value = mock_user
        mock_get_session.return_value.__enter__.return_value = mock_session

        user = {"id": 1, "email": "test@example.com"}
        handle_password_change(user, "current123", "NewPass123!", "NewPass123!", "1.2.3.4")

        mock_log.assert_called_once_with(
            SecurityEvent.PASSWORD_RESET_COMPLETED,
            user_id=1,
            user_email="test@example.com",
            ip_address="1.2.3.4",
            details={"method": "profile_edit", "success": True},
        )

    @patch("routes.auth.profile_update.password.get_session")
    @patch("routes.auth.profile_update.password.log_security_event")
    @patch("routes.auth.profile_update.password.bcrypt")
    @patch("routes.auth.profile_update.password.validate_password_strength")
    def test_updates_password_hash_in_database(
        self,
        mock_validate: Mock,
        mock_bcrypt: Mock,
        mock_log: Mock,
        mock_get_session: Mock,
    ):
        """Test updates user's password hash in database."""
        mock_validate.return_value = (True, None)
        mock_bcrypt.checkpw.return_value = True
        mock_bcrypt.gensalt.return_value = b"$2b$12$fakesalt"
        new_hash = b"$2b$12$newhash"
        mock_bcrypt.hashpw.return_value = new_hash

        mock_session = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.password_hash = "$2b$12$oldhash"
        mock_session.query().filter().first.return_value = mock_user
        mock_get_session.return_value.__enter__.return_value = mock_session

        user = {"id": 1, "email": "test@example.com"}
        success, error = handle_password_change(
            user, "current123", "NewPass123!", "NewPass123!", "1.1.1.1"
        )

        assert success is True
        # Verify new hash was set
        assert mock_user.password_hash == new_hash.decode("utf-8")
        # Verify bcrypt was called with new password
        mock_bcrypt.hashpw.assert_called_once_with(b"NewPass123!", mock_bcrypt.gensalt.return_value)
