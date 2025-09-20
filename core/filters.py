import json
from datetime import datetime
from typing import Any


def from_json_filter(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return {}
    return value


def date_format_filter(date_str: Any, format_type: str = "display") -> str:
    if not date_str:
        return ""
    try:
        # Handle datetime.date objects directly
        if hasattr(date_str, "strftime"):
            date_obj = date_str
        else:
            date_obj = datetime.strptime(str(date_str), "%Y-%m-%d")

        if format_type == "dd-mm-yyyy":
            return date_obj.strftime("%d-%m-%Y")
        return date_obj.strftime("%b. %d, %Y")
    except Exception:
        return str(date_str)


def time_format_filter(time_str: Any) -> str:
    if not time_str:
        return ""
    try:
        if len(str(time_str)) == 8:
            time_obj = datetime.strptime(str(time_str), "%H:%M:%S")
        else:
            time_obj = datetime.strptime(str(time_str), "%H:%M")
        return time_obj.strftime("%I:%M %p").lstrip("0")
    except Exception:
        return str(time_str)


def month_number_filter(date_str: Any) -> str:
    if not date_str:
        return "00"
    try:
        date_obj = datetime.strptime(str(date_str), "%Y-%m-%d")
        return date_obj.strftime("%m")
    except Exception:
        return "00"
