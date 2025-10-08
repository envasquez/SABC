"""Unit tests for password validation."""

from core.helpers.password_validator import (
    get_password_requirements_text,
    validate_password_strength,
)


class TestPasswordValidator:
    """Test suite for password validation functions."""

    def test_password_too_short(self):
        """Test that passwords under 12 characters are rejected."""
        is_valid, error = validate_password_strength("Short1!")
        assert is_valid is False
        assert "12 characters" in error

    def test_password_missing_uppercase(self):
        """Test that passwords without uppercase letters are rejected."""
        is_valid, error = validate_password_strength("nouppercase123!")
        assert is_valid is False
        assert "uppercase" in error.lower()

    def test_password_missing_lowercase(self):
        """Test that passwords without lowercase letters are rejected."""
        is_valid, error = validate_password_strength("NOLOWERCASE123!")
        assert is_valid is False
        assert "lowercase" in error.lower()

    def test_password_missing_number(self):
        """Test that passwords without numbers are rejected."""
        is_valid, error = validate_password_strength("NoNumbersHere!")
        assert is_valid is False
        assert "number" in error.lower()

    def test_password_missing_special_char(self):
        """Test that passwords without special characters are rejected."""
        is_valid, error = validate_password_strength("NoSpecialChars123")
        assert is_valid is False
        assert "special character" in error.lower()

    def test_common_password_rejected(self):
        """Test that common passwords are rejected."""
        is_valid, error = validate_password_strength("Password123!")
        # "password123" is in the common passwords list
        assert is_valid is False
        assert "common" in error.lower()

    def test_sequential_numbers_rejected(self):
        """Test that passwords with sequential numbers are rejected."""
        is_valid, error = validate_password_strength("Test1234567!Aa")
        assert is_valid is False
        assert "sequential" in error.lower()

    def test_sequential_letters_rejected(self):
        """Test that passwords with sequential letters are rejected."""
        is_valid, error = validate_password_strength("Abcdefgh123!")
        assert is_valid is False
        assert "sequential" in error.lower()

    def test_valid_strong_password(self):
        """Test that a strong password is accepted."""
        is_valid, error = validate_password_strength("MySecureP@ssw0rd2025")
        assert is_valid is True
        assert error == ""

    def test_valid_password_with_various_special_chars(self):
        """Test that passwords with various special characters are accepted."""
        special_chars = "!@#$%^&*(),.?\":{}|<>_-+=[]\\/'~`"
        for char in special_chars:
            password = f"ValidPass123{char}word"
            is_valid, error = validate_password_strength(password)
            assert is_valid is True, f"Password with '{char}' should be valid"

    def test_valid_password_minimum_length(self):
        """Test that exactly 12 character passwords are accepted if otherwise valid."""
        is_valid, error = validate_password_strength("ValidPass1!")
        assert is_valid is True
        assert error == ""

    def test_get_password_requirements_text(self):
        """Test that requirements text is returned."""
        requirements = get_password_requirements_text()
        assert isinstance(requirements, str)
        assert "12 characters" in requirements
        assert "uppercase" in requirements.lower()
        assert "lowercase" in requirements.lower()
        assert "number" in requirements.lower()
        assert "special character" in requirements.lower()


class TestPasswordValidatorEdgeCases:
    """Edge case tests for password validation."""

    def test_empty_password(self):
        """Test that empty passwords are rejected."""
        is_valid, error = validate_password_strength("")
        assert is_valid is False

    def test_whitespace_password(self):
        """Test that whitespace-only passwords are rejected."""
        is_valid, error = validate_password_strength("            ")
        assert is_valid is False

    def test_password_with_unicode_characters(self):
        """Test passwords with unicode characters."""
        is_valid, error = validate_password_strength("ValidPass123!Café")
        # Should be valid - unicode doesn't break validation
        assert is_valid is True

    def test_very_long_password(self):
        """Test that very long passwords are accepted."""
        long_password = "A" * 50 + "a" * 50 + "1" * 50 + "!" * 50
        is_valid, error = validate_password_strength(long_password)
        assert is_valid is True

    def test_password_case_insensitive_common_check(self):
        """Test that common password check is case-insensitive."""
        is_valid, error = validate_password_strength("PASSWORD123!")
        assert is_valid is False
        assert "common" in error.lower()

    def test_sequential_uppercase_letters(self):
        """Test that sequential uppercase letters are rejected."""
        is_valid, error = validate_password_strength("ABCDEFGH123!")
        assert is_valid is False
        assert "sequential" in error.lower()

    def test_reversed_sequential_numbers(self):
        """Test that passwords with reversed sequential numbers are accepted."""
        # "987" is not in the sequential check (which only checks ascending)
        is_valid, error = validate_password_strength("ValidPass987!Aa")
        assert is_valid is True

    def test_non_sequential_numbers(self):
        """Test that non-sequential numbers are accepted."""
        is_valid, error = validate_password_strength("ValidPass135!Aa")
        assert is_valid is True

    def test_password_with_spaces(self):
        """Test that passwords with spaces are accepted."""
        is_valid, error = validate_password_strength("Valid Pass Word 123!")
        assert is_valid is True
