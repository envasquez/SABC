import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Generator

from fastapi.templating import Jinja2Templates
from markupsafe import Markup
from sqlalchemy import Connection

from core.db_schema import engine
from core.helpers.timezone import now_local, to_local
from core.query_service import QueryService


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


def safe_json_filter(value: Any) -> Markup:
    """Safely convert value to JSON and mark as safe for templates.

    This uses JSON encoding plus explicit escaping of HTML special characters
    (<, >, &) to prevent XSS attacks when embedded in HTML.

    Security Note: Python's json.dumps() doesn't escape <, >, & by default.
    We explicitly escape these characters after JSON encoding to prevent XSS.
    The result is safe for embedding in HTML <script> tags.

    Example:
        Input: {"name": "<script>alert('xss')</script>"}
        Output: {"name": "\\u003cscript\\u003ealert('xss')\\u003c\\/script\\u003e"}

    Use this instead of |tojson|safe in templates.
    """
    # First, convert to JSON
    json_str = json.dumps(value, cls=CustomJSONEncoder, ensure_ascii=True)

    # Then escape HTML special characters to prevent XSS
    # Replace < with \u003c, > with \u003e, & with \u0026
    json_str = json_str.replace("<", "\\u003c")
    json_str = json_str.replace(">", "\\u003e")
    json_str = json_str.replace("&", "\\u0026")

    # nosec B704: We explicitly escape all dangerous HTML characters (<, >, &)
    # This prevents XSS by ensuring <script>, </script>, etc. cannot appear in output
    return Markup(json_str)  # nosec


def tojson_attr_filter(value: Any) -> Markup:
    """Convert value to JSON and escape for use in HTML data attributes.

    This filter is specifically designed for embedding JSON in HTML data attributes
    using double quotes. It escapes:
    - " to &#34; (so JSON quotes don't break the attribute)
    - ' to &#39; (for single quotes in data)
    - < to &lt; (XSS prevention)
    - > to &gt; (XSS prevention)
    - & to &amp; (proper HTML entity encoding)

    The browser automatically unescapes these when reading dataset attributes,
    so JavaScript can use JSON.parse() directly on the result.

    Example:
        Template: <div data-foo="{{ data | tojson_attr }}">
        Input: {"name": "Test's Lake"}
        Output: {&#34;name&#34;: &#34;Test&#39;s Lake&#34;}

    Use this instead of |tojson|e for data attributes.
    """
    from markupsafe import escape

    # Convert to JSON string
    json_str = json.dumps(value, cls=CustomJSONEncoder, ensure_ascii=False)

    # Escape for HTML attribute context (this escapes ", <, >, &, ')
    escaped = str(escape(json_str))

    # Return as Markup to prevent Jinja2 from double-escaping
    # nosec B703: We explicitly escape all dangerous characters above
    return Markup(escaped)


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


def to_local_datetime_filter(dt: Any) -> Any:
    """Convert a datetime to the club's local timezone (Central Time).

    This filter is used to convert UTC datetimes from the database
    to Central Time for display to users.

    Args:
        dt: A datetime object (can be naive or timezone-aware)

    Returns:
        Timezone-aware datetime in America/Chicago timezone,
        or the original value if not a datetime
    """
    if dt is None:
        return dt
    if not hasattr(dt, "strftime"):
        return dt
    return to_local(dt)


def is_dues_current_filter(dues_paid_through: Any) -> bool:
    """Check if member dues are current (paid through today or later).

    This filter handles both date objects and string representations
    of dates from database query results.

    Args:
        dues_paid_through: Date when dues expire (date object or ISO string)

    Returns:
        True if dues are current, False otherwise
    """
    if dues_paid_through is None:
        return False
    # Handle string representations from raw SQL queries
    if isinstance(dues_paid_through, str):
        try:
            dues_paid_through = date.fromisoformat(dues_paid_through)
        except ValueError:
            return False
    return dues_paid_through >= date.today()


def month_number_filter(date_str: Any) -> str:
    if not date_str:
        return "00"
    try:
        date_obj = datetime.strptime(str(date_str), "%Y-%m-%d")
        return date_obj.strftime("%m")
    except Exception:
        return "00"


def nl2br_filter(value: Any) -> Markup:
    """Convert newlines to HTML <br> tags.

    This filter is useful for displaying user-entered text that contains
    newline characters in HTML where whitespace is normally collapsed.

    Example:
        Input: "Line 1\nLine 2\nLine 3"
        Output: "Line 1<br>\nLine 2<br>\nLine 3"

    The input is escaped first to prevent XSS, then newlines are converted
    to <br> tags.
    """
    from markupsafe import escape

    if not value:
        return Markup("")
    # First escape the value to prevent XSS, then replace newlines with <br>
    escaped = escape(str(value))
    # nosec B703: We explicitly escape the input above before adding <br> tags
    return Markup(str(escaped).replace("\n", "<br>\n"))


def nl2br_safe_filter(value: Any) -> Markup:
    """Convert newlines to HTML <br> tags, preserving existing HTML.

    This filter allows HTML tags (like <a>) to render while converting
    newlines to <br> tags. Use this only for trusted admin-entered content
    like poll descriptions where HTML links are intentional.

    WARNING: This does NOT escape HTML, so only use for trusted content.

    Example:
        Input: "Line 1\n<a href='/link'>Click</a>"
        Output: "Line 1<br>\n<a href='/link'>Click</a>"
    """
    if not value:
        return Markup("")
    # nosec B703: This filter intentionally preserves HTML for trusted admin content
    return Markup(str(value).replace("\n", "<br>\n"))


templates = Jinja2Templates(directory="templates")
templates.env.filters["time_format"] = time_format_filter
templates.env.filters["tojson_attr"] = tojson_attr_filter
templates.env.filters["from_json"] = from_json_filter

# Add now_local as a global function for templates
templates.env.globals["now_local"] = now_local


def get_db() -> Generator[Connection, None, None]:
    """Get database connection as a dependency."""
    with engine.connect() as conn:
        yield conn


def get_query_service() -> Generator[QueryService, None, None]:
    """
    Get QueryService instance as a FastAPI dependency.

    Usage:
        @router.get("/example")
        def example(qs: QueryService = Depends(get_query_service)):
            return qs.get_some_data()
    """
    with engine.connect() as conn:
        yield QueryService(conn)
