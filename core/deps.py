import json
from datetime import datetime
from decimal import Decimal
from typing import Any, AsyncGenerator, Dict, Union

from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import Connection

from core.db_schema import engine
from core.helpers.auth import admin, require_admin_async


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (datetime,)):
            return obj.isoformat()
        return super().default(obj)


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
        if hasattr(date_str, "strftime"):
            date_obj = date_str
        else:
            date_obj = datetime.strptime(str(date_str), "%Y-%m-%d")
        if format_type == "dd-mm-yyyy":
            return date_obj.strftime("%d-%m-%Y")
        if format_type == "mm-dd-yyyy":
            return date_obj.strftime("%m-%d-%Y")
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


templates = Jinja2Templates(directory="templates")
templates.env.filters["time_format"] = time_format_filter


async def get_db() -> AsyncGenerator[Connection, None]:
    with engine.connect() as conn:
        yield conn


async def get_admin_or_redirect(request: Request) -> Union[Dict[str, Any], RedirectResponse]:
    return admin(request)


require_admin = require_admin_async
