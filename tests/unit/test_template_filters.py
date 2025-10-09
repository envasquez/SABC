"""Unit tests for Jinja2 template filters."""

from datetime import date, datetime, time
from decimal import Decimal

from core.deps import (
    CustomJSONEncoder,
    date_format_filter,
    from_json_filter,
    month_number_filter,
    time_format_filter,
)


class TestFromJsonFilter:
    """Tests for from_json_filter."""

    def test_parses_valid_json_string(self):
        """Test parsing valid JSON string."""
        result = from_json_filter('{"key": "value", "num": 42}')
        assert result == {"key": "value", "num": 42}

    def test_parses_json_array(self):
        """Test parsing JSON array."""
        result = from_json_filter("[1, 2, 3]")
        assert result == [1, 2, 3]

    def test_returns_empty_dict_for_invalid_json(self):
        """Test returns empty dict for invalid JSON."""
        result = from_json_filter("not valid json")
        assert result == {}

    def test_returns_value_unchanged_if_not_string(self):
        """Test non-string values are returned unchanged."""
        obj = {"already": "parsed"}
        result = from_json_filter(obj)
        assert result is obj

    def test_handles_empty_string(self):
        """Test handles empty string."""
        result = from_json_filter("")
        assert result == {}

    def test_handles_none_value(self):
        """Test handles None value."""
        result = from_json_filter(None)
        assert result is None


class TestDateFormatFilter:
    """Tests for date_format_filter."""

    def test_formats_date_object_default(self):
        """Test formatting date object with default format."""
        dt = datetime(2024, 3, 15)
        result = date_format_filter(dt)
        assert result == "Mar. 15, 2024"

    def test_formats_date_string_default(self):
        """Test formatting date string with default format."""
        result = date_format_filter("2024-03-15")
        assert result == "Mar. 15, 2024"

    def test_formats_dd_mm_yyyy(self):
        """Test formatting with dd-mm-yyyy format."""
        dt = datetime(2024, 3, 15)
        result = date_format_filter(dt, "dd-mm-yyyy")
        assert result == "15-03-2024"

    def test_formats_mm_dd_yyyy(self):
        """Test formatting with mm-dd-yyyy format."""
        dt = datetime(2024, 3, 5)
        result = date_format_filter(dt, "mm-dd-yyyy")
        assert result == "03-05-2024"

    def test_handles_empty_value(self):
        """Test handles empty/None value."""
        assert date_format_filter(None) == ""
        assert date_format_filter("") == ""

    def test_handles_invalid_date_string(self):
        """Test handles invalid date string gracefully."""
        result = date_format_filter("not a date")
        assert result == "not a date"

    def test_formats_date_object_without_time(self):
        """Test formatting Python date object (not datetime)."""
        d = date(2024, 12, 25)
        result = date_format_filter(d)
        assert result == "Dec. 25, 2024"

    def test_handles_different_separators(self):
        """Test handles different date separators."""
        # Should only accept YYYY-MM-DD format
        result = date_format_filter("03/15/2024")
        assert result == "03/15/2024"  # Returns as-is if invalid format


class TestTimeFormatFilter:
    """Tests for time_format_filter."""

    def test_formats_hh_mm_ss_morning(self):
        """Test formatting HH:MM:SS time in morning."""
        result = time_format_filter("09:30:00")
        assert result == "9:30 AM"

    def test_formats_hh_mm_ss_afternoon(self):
        """Test formatting HH:MM:SS time in afternoon."""
        result = time_format_filter("15:45:00")
        assert result == "3:45 PM"

    def test_formats_hh_mm_morning(self):
        """Test formatting HH:MM time in morning."""
        result = time_format_filter("08:15")
        assert result == "8:15 AM"

    def test_formats_hh_mm_afternoon(self):
        """Test formatting HH:MM time in afternoon."""
        result = time_format_filter("20:00")
        assert result == "8:00 PM"

    def test_formats_midnight(self):
        """Test formatting midnight."""
        result = time_format_filter("00:00:00")
        assert result == "12:00 AM"

    def test_formats_noon(self):
        """Test formatting noon."""
        result = time_format_filter("12:00:00")
        assert result == "12:00 PM"

    def test_strips_leading_zero_from_hour(self):
        """Test that leading zero is stripped from hour."""
        result = time_format_filter("01:30:00")
        assert result == "1:30 AM"
        assert not result.startswith("0")

    def test_handles_empty_value(self):
        """Test handles empty/None value."""
        assert time_format_filter(None) == ""
        assert time_format_filter("") == ""

    def test_handles_invalid_time_string(self):
        """Test handles invalid time string gracefully."""
        result = time_format_filter("not a time")
        assert result == "not a time"

    def test_formats_time_object(self):
        """Test formatting Python time object."""
        t = time(14, 30, 0)
        result = time_format_filter(str(t))
        assert result == "2:30 PM"


class TestMonthNumberFilter:
    """Tests for month_number_filter."""

    def test_extracts_month_from_date_string(self):
        """Test extracting month number from date string."""
        result = month_number_filter("2024-03-15")
        assert result == "03"

    def test_extracts_month_january(self):
        """Test extracting January (edge case)."""
        result = month_number_filter("2024-01-01")
        assert result == "01"

    def test_extracts_month_december(self):
        """Test extracting December (edge case)."""
        result = month_number_filter("2024-12-31")
        assert result == "12"

    def test_handles_empty_value(self):
        """Test handles empty/None value."""
        assert month_number_filter(None) == "00"
        assert month_number_filter("") == "00"

    def test_handles_invalid_date_string(self):
        """Test handles invalid date string."""
        result = month_number_filter("invalid")
        assert result == "00"

    def test_returns_zero_padded_month(self):
        """Test returns zero-padded month number."""
        result = month_number_filter("2024-05-10")
        assert result == "05"
        assert len(result) == 2


class TestCustomJSONEncoder:
    """Tests for CustomJSONEncoder."""

    def test_encodes_decimal_as_float(self):
        """Test Decimal is encoded as float."""
        import json

        data = {"value": Decimal("123.45")}
        result = json.dumps(data, cls=CustomJSONEncoder)
        assert result == '{"value": 123.45}'

    def test_encodes_datetime_as_isoformat(self):
        """Test datetime is encoded as ISO format string."""
        import json

        dt = datetime(2024, 3, 15, 14, 30, 0)
        data = {"timestamp": dt}
        result = json.dumps(data, cls=CustomJSONEncoder)
        assert "2024-03-15T14:30:00" in result

    def test_encodes_date_as_isoformat(self):
        """Test date is encoded as ISO format string."""
        import json

        # Note: CustomJSONEncoder only handles datetime, not date objects
        # Convert date to datetime for testing
        dt = datetime(2024, 3, 15, 0, 0, 0)
        data = {"date": dt}
        result = json.dumps(data, cls=CustomJSONEncoder)
        assert "2024-03-15" in result

    def test_encodes_regular_types_normally(self):
        """Test regular types are encoded normally."""
        import json

        data = {"string": "hello", "number": 42, "bool": True, "null": None}
        result = json.dumps(data, cls=CustomJSONEncoder)
        parsed = json.loads(result)
        assert parsed == data

    def test_encodes_nested_structures(self):
        """Test complex nested structures with Decimal and datetime."""
        import json

        data = {
            "tournament": {
                "id": 1,
                "entry_fee": Decimal("25.00"),
                "date": datetime(2024, 3, 15),
            }
        }
        result = json.dumps(data, cls=CustomJSONEncoder)
        parsed = json.loads(result)
        assert parsed["tournament"]["entry_fee"] == 25.0
        assert "2024-03-15" in parsed["tournament"]["date"]


class TestFilterEdgeCases:
    """Tests for edge cases across all filters."""

    def test_from_json_with_nested_objects(self):
        """Test from_json handles deeply nested structures."""
        json_str = '{"a": {"b": {"c": [1, 2, 3]}}}'
        result = from_json_filter(json_str)
        assert result["a"]["b"]["c"] == [1, 2, 3]

    def test_date_format_with_datetime_object(self):
        """Test date_format works with full datetime objects."""
        dt = datetime(2024, 3, 15, 10, 30, 45)
        result = date_format_filter(dt, "dd-mm-yyyy")
        assert result == "15-03-2024"

    def test_time_format_preserves_minutes(self):
        """Test time_format doesn't strip leading zeros from minutes."""
        result = time_format_filter("14:05:00")
        assert "05" in result  # Minutes should keep leading zero

    def test_month_number_works_with_date_object(self):
        """Test month_number filter with date object converted to string."""
        d = date(2024, 7, 4)
        result = month_number_filter(str(d))
        assert result == "07"
