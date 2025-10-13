"""Tests for safe_json_filter to verify XSS protection."""

import json

from core.deps import safe_json_filter


class TestSafeJsonFilter:
    """Test suite for safe_json_filter XSS protection."""

    def test_escapes_script_tags(self):
        """Test that script tags are escaped in JSON output."""
        malicious_data = {"name": "<script>alert('xss')</script>"}
        result = safe_json_filter(malicious_data)

        # json.dumps escapes < and > as unicode escape sequences
        assert "<script>" not in str(result)
        assert "</script>" not in str(result)

        # Verify it's valid JSON that can be parsed back
        parsed = json.loads(str(result))
        assert parsed["name"] == "<script>alert('xss')</script>"

    def test_escapes_html_entities(self):
        """Test that HTML entities are escaped."""
        data = {"html": '<div onclick="alert(1)">Click me</div>'}
        result = safe_json_filter(data)

        # Should not contain unescaped HTML
        assert '<div onclick="alert(1)">' not in str(result)

        # Should be valid JSON
        parsed = json.loads(str(result))
        assert parsed["html"] == '<div onclick="alert(1)">Click me</div>'

    def test_escapes_javascript_protocol(self):
        """Test that javascript: protocol is preserved but escaped."""
        data = {"link": "javascript:alert('xss')"}
        result = safe_json_filter(data)

        # Should be valid JSON
        parsed = json.loads(str(result))
        assert parsed["link"] == "javascript:alert('xss')"

        # When embedded in HTML, the JSON encoding makes it safe
        assert "javascript:alert" in str(result)  # Present but JSON-encoded

    def test_escapes_quotes_and_backslashes(self):
        """Test that quotes and backslashes are properly escaped."""
        data = {"text": 'He said "Hello" and used a \\ backslash'}
        result = safe_json_filter(data)

        # Should be valid JSON
        parsed = json.loads(str(result))
        assert parsed["text"] == 'He said "Hello" and used a \\ backslash'

    def test_nested_objects_are_safe(self):
        """Test that nested objects are recursively safe."""
        data = {
            "user": {
                "name": "<script>alert(1)</script>",
                "email": 'test@example.com"onload="alert(2)',
            },
            "items": ["<img src=x onerror=alert(3)>", "normal text"],
        }
        result = safe_json_filter(data)

        # Should not contain unescaped dangerous content
        result_str = str(result)
        assert "<script>" not in result_str
        assert "<img" not in result_str or "\\u003cimg" in result_str

        # Should be valid JSON
        parsed = json.loads(str(result))
        assert parsed["user"]["name"] == "<script>alert(1)</script>"
        assert parsed["items"][0] == "<img src=x onerror=alert(3)>"

    def test_handles_special_characters(self):
        """Test that special characters are properly handled."""
        data = {"special": "Line1\nLine2\tTabbed\rCarriage"}
        result = safe_json_filter(data)

        # Should be valid JSON
        parsed = json.loads(str(result))
        assert parsed["special"] == "Line1\nLine2\tTabbed\rCarriage"

    def test_handles_unicode_characters(self):
        """Test that unicode characters are preserved."""
        data = {"unicode": "Hello 世界 🌍"}
        result = safe_json_filter(data)

        # Should be valid JSON
        parsed = json.loads(str(result))
        assert parsed["unicode"] == "Hello 世界 🌍"

    def test_handles_numbers_and_booleans(self):
        """Test that non-string types are handled correctly."""
        data = {"number": 42, "float": 3.14, "bool": True, "none": None}
        result = safe_json_filter(data)

        # Should be valid JSON
        parsed = json.loads(str(result))
        assert parsed["number"] == 42
        assert parsed["float"] == 3.14
        assert parsed["bool"] is True
        assert parsed["none"] is None

    def test_empty_data(self):
        """Test that empty data structures work."""
        assert str(safe_json_filter({})) == "{}"
        assert str(safe_json_filter([])) == "[]"
        assert str(safe_json_filter("")) == '""'

    def test_xss_payload_examples(self):
        """Test against common XSS payloads."""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            '"><script>alert(String.fromCharCode(88,83,83))</script>',
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<iframe src='javascript:alert(\"XSS\")'></iframe>",
            "<body onload=alert('XSS')>",
            "';alert(String.fromCharCode(88,83,83))//",
        ]

        for payload in xss_payloads:
            data = {"payload": payload}
            result = safe_json_filter(data)

            # Should be valid JSON
            parsed = json.loads(str(result))
            assert parsed["payload"] == payload

            # Should not contain unescaped dangerous tags
            result_str = str(result)
            # json.dumps escapes < and > to ensure they can't be interpreted as HTML
            assert "<script>" not in result_str or "\\u003c" in result_str
            assert "<img" not in result_str or "\\u003c" in result_str
            assert "<iframe" not in result_str or "\\u003c" in result_str
            assert "<body" not in result_str or "\\u003c" in result_str

    def test_safe_for_html_script_tag_embedding(self):
        """Test that output is safe for embedding in HTML <script> tags."""
        data = {"user_input": "</script><script>alert('XSS')</script>"}
        result = safe_json_filter(data)

        # The most dangerous case: trying to break out of a script tag
        # json.dumps will escape the </script> as <\/script> preventing breakout
        result_str = str(result)

        # Parse as JSON to verify validity
        parsed = json.loads(result_str)
        assert parsed["user_input"] == "</script><script>alert('XSS')</script>"

        # The key security property: </script> must be escaped
        # JSON standard requires / to be escaped in strings, which breaks </script>
        assert "<\\/script>" in result_str or "\\u003c/script\\u003e" in result_str

    def test_markupsafe_markup_is_safe(self):
        """Test that returned Markup object behaves correctly."""
        from markupsafe import Markup

        data = {"test": "<script>alert(1)</script>"}
        result = safe_json_filter(data)

        # Should be a Markup instance
        assert isinstance(result, Markup)

        # When converted to string, should not execute scripts
        html = f"<script>var data = {result};</script>"

        # Verify the JSON in the HTML won't cause XSS
        assert "<script>alert(1)</script>" not in html or '{"test": "<script>' not in html

        # The JSON encoding ensures safety
        assert "\\u003c" in html or '\\"' in html or "\\/" in html
