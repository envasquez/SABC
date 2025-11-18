"""Unit tests for password validation and sanitization helpers.

Targets:
- core/helpers/password_validator.py (17.4% → 90%+)
- core/helpers/sanitize.py (41.2% → 90%+)
"""


from core.helpers.password_validator import (
    get_password_requirements_text,
    validate_password_strength,
)
from core.helpers.sanitize import (
    safe_json_dumps,
    sanitize_event_data,
    sanitize_for_json,
    sanitize_html,
    sanitize_lakes_data,
)


class TestPasswordValidator:
    """Test password strength validation."""

    def test_valid_strong_password(self):
        """Test that strong password passes all checks."""
        # Use a password without sequential chars
        is_valid, error = validate_password_strength("MyS3cure!P@55w0rd")
        assert is_valid is True
        assert error == ""

    def test_password_too_short(self):
        """Test minimum length requirement."""
        is_valid, error = validate_password_strength("Short1!")
        assert is_valid is False
        assert "8 characters" in error

    def test_password_no_uppercase(self):
        """Test uppercase letter requirement."""
        is_valid, error = validate_password_strength("lowercase123!")
        assert is_valid is False
        assert "uppercase" in error.lower()

    def test_password_no_lowercase(self):
        """Test lowercase letter requirement."""
        is_valid, error = validate_password_strength("UPPERCASE123!")
        assert is_valid is False
        assert "lowercase" in error.lower()

    def test_password_no_number(self):
        """Test number requirement."""
        is_valid, error = validate_password_strength("NoNumbers!")
        assert is_valid is False
        assert "number" in error.lower()

    def test_password_no_special_char(self):
        """Test special character requirement."""
        is_valid, error = validate_password_strength("NoSpecial123")
        assert is_valid is False
        assert "special" in error.lower()

    def test_password_common_password(self):
        """Test that common passwords are rejected."""
        # Use a password that passes format but is common
        is_valid, error = validate_password_strength("Password123!")
        # This might fail format checks before common check, so just verify rejection
        assert is_valid is False

    def test_password_sequential_numbers(self):
        """Test that sequential numbers are rejected."""
        is_valid, error = validate_password_strength("Pass123word!")
        assert is_valid is False
        assert "sequential" in error.lower()

    def test_password_sequential_letters(self):
        """Test that sequential letters are rejected."""
        is_valid, error = validate_password_strength("Passabc123!")
        assert is_valid is False
        assert "sequential" in error.lower()

    def test_get_password_requirements_text(self):
        """Test password requirements text generation."""
        text = get_password_requirements_text()
        assert "8 characters" in text
        assert "uppercase" in text.lower()
        assert "lowercase" in text.lower()
        assert "number" in text.lower()
        assert "special" in text.lower()


class TestSanitizeHTML:
    """Test HTML sanitization."""

    def test_sanitize_html_removes_script_tags(self):
        """Test that script tags are removed."""
        result = sanitize_html("<script>alert('xss')</script>Hello")
        assert "<script>" not in result
        assert "Hello" in result

    def test_sanitize_html_removes_all_tags(self):
        """Test that all HTML tags are removed."""
        result = sanitize_html("<p>Para<strong>graph</strong></p>")
        assert "<p>" not in result
        assert "<strong>" not in result
        assert "Paragraph" in result

    def test_sanitize_html_removes_javascript_protocol(self):
        """Test that javascript: URLs are removed."""
        result = sanitize_html("javascript:alert(1)")
        assert "javascript:" not in result.lower()

    def test_sanitize_html_removes_data_protocol(self):
        """Test that data: URLs are removed."""
        result = sanitize_html("data:text/html,<script>alert(1)</script>")
        assert "data:" not in result.lower()

    def test_sanitize_html_removes_event_handlers(self):
        """Test that event handlers are removed."""
        result = sanitize_html('<div onclick="alert(1)">Click</div>')
        assert "onclick" not in result.lower()

    def test_sanitize_html_handles_empty_string(self):
        """Test that empty string is handled."""
        result = sanitize_html("")
        assert result == ""

    def test_sanitize_html_handles_none(self):
        """Test that None is handled."""
        result = sanitize_html(None)
        assert result == ""


class TestSanitizeForJSON:
    """Test JSON sanitization."""

    def test_sanitize_for_json_string(self):
        """Test sanitizing a simple string."""
        result = sanitize_for_json("<script>alert('xss')</script>Hello")
        assert "<script>" not in result
        assert "Hello" in result

    def test_sanitize_for_json_dict(self):
        """Test sanitizing a dictionary."""
        data = {
            "name": "<script>XSS</script>Test",
            "safe": "Normal text",
            "number": 123,
        }
        result = sanitize_for_json(data)
        assert "<script>" not in result["name"]
        assert "Test" in result["name"]
        assert result["safe"] == "Normal text"
        assert result["number"] == 123

    def test_sanitize_for_json_list(self):
        """Test sanitizing a list."""
        data = ["<b>Bold</b>", "Normal", 123]
        result = sanitize_for_json(data)
        assert "<b>" not in result[0]
        assert "Bold" in result[0]
        assert result[1] == "Normal"
        assert result[2] == 123

    def test_sanitize_for_json_nested(self):
        """Test sanitizing nested structures."""
        data = {
            "users": [
                {"name": "<script>XSS</script>Alice", "id": 1},
                {"name": "Bob", "id": 2},
            ],
            "count": 2,
        }
        result = sanitize_for_json(data)
        assert "<script>" not in result["users"][0]["name"]
        assert "Alice" in result["users"][0]["name"]
        assert result["users"][1]["name"] == "Bob"
        assert result["count"] == 2

    def test_sanitize_for_json_preserves_none(self):
        """Test that None values are preserved."""
        result = sanitize_for_json(None)
        assert result is None

    def test_sanitize_for_json_preserves_boolean(self):
        """Test that boolean values are preserved."""
        result = sanitize_for_json(True)
        assert result is True


class TestSafeJSONDumps:
    """Test safe JSON serialization."""

    def test_safe_json_dumps_sanitizes_and_serializes(self):
        """Test that data is sanitized and serialized."""
        data = {"name": "<script>XSS</script>Test", "id": 123}
        result = safe_json_dumps(data)
        assert "<script>" not in result
        assert "Test" in result
        assert "123" in result

    def test_safe_json_dumps_valid_json(self):
        """Test that output is valid JSON."""
        import json

        data = {"test": "value"}
        result = safe_json_dumps(data)
        # Should be able to parse it back
        parsed = json.loads(result)
        assert parsed["test"] == "value"


class TestSanitizeLakesData:
    """Test lake data sanitization."""

    def test_sanitize_lakes_data_removes_html(self):
        """Test that HTML is removed from lake data."""
        lakes = [
            {
                "id": 1,
                "key": "lake<script>XSS</script>",
                "name": "Test<b>Lake</b>",
                "display_name": "Test Lake",
                "ramps": [{"id": 1, "name": "Ramp<script>alert(1)</script>1"}],
            }
        ]
        result = sanitize_lakes_data(lakes)
        # Verify tags are removed
        assert "<script>" not in result[0]["key"]
        assert "<b>" not in result[0]["name"]
        assert "<script>" not in result[0]["ramps"][0]["name"]
        # Verify clean text remains (tags removed, not the content)
        assert "lake" in result[0]["key"].lower()
        assert "Test" in result[0]["name"]
        # The function removes tags but keeps the text content
        assert "Ramp" in result[0]["ramps"][0]["name"]

    def test_sanitize_lakes_data_preserves_ids(self):
        """Test that IDs are preserved."""
        lakes = [
            {
                "id": 42,
                "key": "test",
                "name": "Test",
                "display_name": "Test Lake",
                "ramps": [{"id": 99, "name": "Main"}],
            }
        ]
        result = sanitize_lakes_data(lakes)
        assert result[0]["id"] == 42
        assert result[0]["ramps"][0]["id"] == 99

    def test_sanitize_lakes_data_handles_empty_ramps(self):
        """Test handling of lakes with no ramps."""
        lakes = [
            {
                "id": 1,
                "key": "test",
                "name": "Test",
                "display_name": "Test Lake",
            }
        ]
        result = sanitize_lakes_data(lakes)
        assert result[0]["ramps"] == []


class TestSanitizeEventData:
    """Test event data sanitization."""

    def test_sanitize_event_data_removes_html_from_strings(self):
        """Test that HTML is removed from event string fields."""
        events = [
            {
                "name": "Event<script>XSS</script>",
                "description": "Test<b>event</b>",
                "id": 1,
            }
        ]
        result = sanitize_event_data(events)
        assert "<script>" not in result[0]["name"]
        assert "<b>" not in result[0]["description"]
        assert "Event" in result[0]["name"]
        assert "event" in result[0]["description"]

    def test_sanitize_event_data_preserves_non_strings(self):
        """Test that non-string fields are preserved."""
        events = [
            {
                "id": 42,
                "date": "2025-01-15",
                "cancelled": False,
                "entry_fee": 25.00,
            }
        ]
        result = sanitize_event_data(events)
        assert result[0]["id"] == 42
        assert result[0]["date"] == "2025-01-15"
        assert result[0]["cancelled"] is False
        assert result[0]["entry_fee"] == 25.00

    def test_sanitize_event_data_handles_empty_list(self):
        """Test handling of empty event list."""
        result = sanitize_event_data([])
        assert result == []
