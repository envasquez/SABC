"""Comprehensive password validator tests."""

from core.helpers.password_validator import validate_password_strength


class TestPasswordValidator:
    """Test password validation."""

    def test_password_too_short(self):
        """Test password minimum length."""
        is_valid, error = validate_password_strength("Short1!")
        assert is_valid is False
        assert "8 characters" in error

    def test_password_no_uppercase(self):
        """Test password requires uppercase."""
        is_valid, error = validate_password_strength("lowercase123!")
        assert is_valid is False
        assert "uppercase" in error.lower()

    def test_password_no_lowercase(self):
        """Test password requires lowercase."""
        is_valid, error = validate_password_strength("UPPERCASE123!")
        assert is_valid is False
        assert "lowercase" in error.lower()

    def test_password_no_digit(self):
        """Test password requires digit."""
        is_valid, error = validate_password_strength("NoDigits!!")
        assert is_valid is False
        assert "digit" in error.lower()

    def test_password_no_special(self):
        """Test password requires special character."""
        is_valid, error = validate_password_strength("NoSpecial123")
        assert is_valid is False
        assert "special" in error.lower()

    def test_password_common_word(self):
        """Test password rejects common words."""
        is_valid, error = validate_password_strength("Password123!")
        assert is_valid is False

    def test_password_sequential_numbers(self):
        """Test password rejects sequential numbers."""
        is_valid, error = validate_password_strength("Test1234!")
        assert is_valid is False

    def test_password_valid(self):
        """Test valid password passes."""
        is_valid, error = validate_password_strength("V@lidP@55w0rd")
        assert is_valid is True
        assert error == ""
