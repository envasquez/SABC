import json
from datetime import datetime


def from_json_filter(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return {}
    return value


def date_format_filter(date_str, format_type="display"):
    if not date_str:
        return ""
    try:
        date_obj = datetime.strptime(str(date_str), "%Y-%m-%d")
        if format_type == "dd-mm-yyyy":
            return date_obj.strftime("%d-%m-%Y")
        return date_obj.strftime("%b. %d, %Y")
    except:
        return str(date_str)


def time_format_filter(time_str):
    if not time_str:
        return ""
    try:
        if len(str(time_str)) == 8:
            time_obj = datetime.strptime(str(time_str), "%H:%M:%S")
        else:
            time_obj = datetime.strptime(str(time_str), "%H:%M")
        return time_obj.strftime("%I:%M %p").lstrip("0")
    except:
        return str(time_str)


def month_number_filter(date_str):
    if not date_str:
        return "00"
    try:
        date_obj = datetime.strptime(str(date_str), "%Y-%m-%d")
        return date_obj.strftime("%m")
    except:
        return "00"
