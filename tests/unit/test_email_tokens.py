"""Unit tests for email token generation and verification."""

from datetime import timedelta
from unittest.mock import Mock, patch

from core.email.tokens import (
    cleanup_expired_tokens,
    create_password_reset_token,
    generate_reset_token,
    use_reset_token,
    verify_reset_token,
)
from core.helpers.timezone import now_utc


class TestGenerateResetToken:
    """Tests for generate_reset_token function."""

    def test_generates_url_safe_token(self):
        """Test that generated token is URL-safe."""
        token = generate_reset_token()
        assert isinstance(token, str)
        assert len(token) > 0
        # URL-safe characters only
        assert all(c.isalnum() or c in "-_" for c in token)

    def test_generates_unique_tokens(self):
        """Test that multiple calls generate different tokens."""
        tokens = {generate_reset_token() for _ in range(100)}
        assert len(tokens) == 100  # All unique

    def test_token_length_is_sufficient(self):
        """Test that token has sufficient entropy (min 32 bytes)."""
        token = generate_reset_token()
        # URL-safe encoding is ~4/3 of input length
        assert len(token) >= 32


class TestCreatePasswordResetToken:
    """Tests for create_password_reset_token function."""

    @patch("core.email.tokens.check_rate_limit")
    @patch("core.email.tokens.insert_token")
    @patch("core.email.tokens.generate_reset_token")
    def test_creates_token_for_valid_user(
        self, mock_generate: Mock, mock_insert: Mock, mock_check: Mock
    ):
        """Test successful token creation."""
        mock_check.return_value = 0  # No recent requests
        mock_generate.return_value = "test_token_123"
        mock_insert.return_value = True

        token = create_password_reset_token(1, "user@example.com")

        assert token == "test_token_123"
        mock_check.assert_called_once()
        mock_generate.assert_called_once()
        mock_insert.assert_called_once()

    @patch("core.email.tokens.check_rate_limit")
    def test_rate_limit_blocks_excessive_requests(self, mock_check: Mock):
        """Test that rate limiting prevents token spam."""
        mock_check.return_value = 5  # Exceeds limit

        token = create_password_reset_token(1, "user@example.com")

        assert token is None
        mock_check.assert_called_once()

    @patch("core.email.tokens.check_rate_limit")
    @patch("core.email.tokens.insert_token")
    @patch("core.email.tokens.generate_reset_token")
    def test_returns_none_on_insert_failure(
        self, mock_generate: Mock, mock_insert: Mock, mock_check: Mock
    ):
        """Test returns None if database insert fails."""
        mock_check.return_value = 0
        mock_generate.return_value = "test_token"
        mock_insert.return_value = False  # Insert failed

        token = create_password_reset_token(1, "user@example.com")

        assert token is None

    @patch("core.email.tokens.check_rate_limit")
    def test_handles_database_exception(self, mock_check: Mock):
        """Test handles database errors gracefully."""
        mock_check.side_effect = Exception("Database error")

        token = create_password_reset_token(1, "user@example.com")

        assert token is None

    @patch("core.email.tokens.check_rate_limit")
    @patch("core.email.tokens.insert_token")
    @patch("core.email.tokens.generate_reset_token")
    def test_token_expiry_is_set_correctly(
        self, mock_generate: Mock, mock_insert: Mock, mock_check: Mock
    ):
        """Test that expiry time is calculated correctly."""
        from core.email.config import TOKEN_EXPIRY_MINUTES

        mock_check.return_value = 0
        mock_generate.return_value = "token"
        mock_insert.return_value = True

        create_password_reset_token(1, "user@example.com")

        # Verify expiry time was passed correctly
        call_args = mock_insert.call_args[0]
        expires_at = call_args[2]
        expected_expiry = now_utc() + timedelta(minutes=TOKEN_EXPIRY_MINUTES)
        # Allow 1 second tolerance for test execution time
        assert abs((expires_at - expected_expiry).total_seconds()) < 1


class TestVerifyResetToken:
    """Tests for verify_reset_token function."""

    @patch("core.email.tokens.fetch_token_data")
    def test_verifies_valid_token(self, mock_fetch: Mock):
        """Test verification of valid, unused, non-expired token."""
        future_time = now_utc() + timedelta(hours=1)
        mock_fetch.return_value = (1, future_time, False, "user@test.com", "Test User")

        result = verify_reset_token("valid_token")

        assert result is not None
        assert result["user_id"] == 1
        assert result["email"] == "user@test.com"
        assert result["name"] == "Test User"
        assert result["expires_at"] == future_time

    @patch("core.email.tokens.fetch_token_data")
    def test_rejects_invalid_token(self, mock_fetch: Mock):
        """Test rejection of non-existent token."""
        mock_fetch.return_value = None

        result = verify_reset_token("invalid_token")

        assert result is None

    @patch("core.email.tokens.fetch_token_data")
    def test_rejects_used_token(self, mock_fetch: Mock):
        """Test rejection of already-used token."""
        future_time = now_utc() + timedelta(hours=1)
        mock_fetch.return_value = (1, future_time, True, "user@test.com", "Test User")  # used=True

        result = verify_reset_token("used_token")

        assert result is None

    @patch("core.email.tokens.fetch_token_data")
    def test_rejects_expired_token(self, mock_fetch: Mock):
        """Test rejection of expired token."""
        past_time = now_utc() - timedelta(hours=1)
        mock_fetch.return_value = (1, past_time, False, "user@test.com", "Test User")

        result = verify_reset_token("expired_token")

        assert result is None

    @patch("core.email.tokens.fetch_token_data")
    def test_handles_database_exception(self, mock_fetch: Mock):
        """Test handles database errors gracefully."""
        mock_fetch.side_effect = Exception("Database error")

        result = verify_reset_token("token")

        assert result is None


class TestUseResetToken:
    """Tests for use_reset_token function."""

    @patch("core.email.tokens.mark_token_used")
    def test_marks_token_as_used_successfully(self, mock_mark: Mock):
        """Test successful token marking."""
        mock_mark.return_value = 1  # One row updated

        result = use_reset_token("valid_token")

        assert result is True
        mock_mark.assert_called_once_with("valid_token")

    @patch("core.email.tokens.mark_token_used")
    def test_returns_false_when_no_token_found(self, mock_mark: Mock):
        """Test returns False when token doesn't exist."""
        mock_mark.return_value = 0  # No rows updated

        result = use_reset_token("invalid_token")

        assert result is False

    @patch("core.email.tokens.mark_token_used")
    def test_handles_database_exception(self, mock_mark: Mock):
        """Test handles database errors gracefully."""
        mock_mark.side_effect = Exception("Database error")

        result = use_reset_token("token")

        assert result is False


class TestCleanupExpiredTokens:
    """Tests for cleanup_expired_tokens function."""

    @patch("core.email.tokens.delete_expired_tokens")
    def test_cleanup_returns_deleted_count(self, mock_delete: Mock):
        """Test returns number of deleted tokens."""
        mock_delete.return_value = 5

        count = cleanup_expired_tokens()

        assert count == 5
        mock_delete.assert_called_once()

    @patch("core.email.tokens.delete_expired_tokens")
    def test_cleanup_handles_no_expired_tokens(self, mock_delete: Mock):
        """Test handles case with no expired tokens."""
        mock_delete.return_value = 0

        count = cleanup_expired_tokens()

        assert count == 0

    @patch("core.email.tokens.delete_expired_tokens")
    def test_cleanup_handles_database_exception(self, mock_delete: Mock):
        """Test handles database errors gracefully."""
        mock_delete.side_effect = Exception("Database error")

        count = cleanup_expired_tokens()

        assert count == 0


class TestTokenIntegration:
    """Integration tests for token lifecycle."""

    @patch("core.email.tokens.check_rate_limit")
    @patch("core.email.tokens.insert_token")
    @patch("core.email.tokens.fetch_token_data")
    @patch("core.email.tokens.mark_token_used")
    @patch("core.email.tokens.generate_reset_token")
    def test_complete_token_lifecycle(
        self,
        mock_generate: Mock,
        mock_mark: Mock,
        mock_fetch: Mock,
        mock_insert: Mock,
        mock_check: Mock,
    ):
        """Test complete flow: create -> verify -> use."""
        # Setup
        mock_check.return_value = 0
        mock_generate.return_value = "test_token_123"
        mock_insert.return_value = True
        future_time = now_utc() + timedelta(hours=1)
        mock_fetch.return_value = (1, future_time, False, "user@test.com", "User")
        mock_mark.return_value = 1

        # Create token
        token = create_password_reset_token(1, "user@test.com")
        assert token == "test_token_123"

        # Verify token
        data = verify_reset_token(token)
        assert data is not None
        assert data["user_id"] == 1

        # Use token
        used = use_reset_token(token)
        assert used is True

    @patch("core.email.tokens.check_rate_limit")
    @patch("core.email.tokens.insert_token")
    @patch("core.email.tokens.generate_reset_token")
    def test_rate_limit_enforced_across_attempts(
        self, mock_generate: Mock, mock_insert: Mock, mock_check: Mock
    ):
        """Test that rate limit is enforced on multiple attempts."""
        # First attempt succeeds
        mock_check.return_value = 0
        mock_generate.return_value = "token1"
        mock_insert.return_value = True
        token1 = create_password_reset_token(1, "user@test.com")
        assert token1 is not None

        # Subsequent attempts exceed limit
        mock_check.return_value = 5  # At limit
        token2 = create_password_reset_token(1, "user@test.com")
        assert token2 is None
