"""Data sanitization utilities for safe template rendering."""

import json
import re
from typing import Any, Dict, List, Union


def sanitize_html(text: str) -> str:
    """Remove HTML tags and potentially dangerous content from text.

    Args:
        text: Input text that may contain HTML

    Returns:
        Sanitized text with HTML removed
    """
    if not text:
        return ""

    # Remove HTML tags
    text = re.sub(r"<[^>]*>", "", text)

    # Remove javascript: protocol
    text = re.sub(r"javascript:", "", text, flags=re.IGNORECASE)

    # Remove data: protocol (can be used for XSS)
    text = re.sub(r"data:", "", text, flags=re.IGNORECASE)

    # Remove on* event handlers
    text = re.sub(r"on\w+\s*=", "", text, flags=re.IGNORECASE)

    return text


def sanitize_iframe(raw_html: str) -> str:
    """Extract only a safe iframe tag from raw HTML input.

    Only allows iframes with Google Maps src URLs. Strips all other HTML,
    scripts, and attributes to prevent stored XSS.

    Args:
        raw_html: Raw HTML string (typically from admin form input)

    Returns:
        A sanitized iframe tag, or empty string if no valid iframe found
    """
    if not raw_html or not raw_html.strip():
        return ""

    # Match iframe with a Google Maps src URL. Tolerate both single- and
    # double-quoted attribute values: the seed data in scripts/lakes_production.json
    # ships single-quoted iframes (Google's "Share/Embed map" UI emitted those
    # historically), and the output normalizes to double quotes regardless.
    match = re.search(
        r"""<iframe\s[^>]*src=["'](https://(?:www\.google\.com/maps|maps\.google\.com/maps)[^"']*)["'][^>]*>""",
        raw_html,
        re.IGNORECASE,
    )
    if match:
        src = match.group(1)
        return (
            f'<iframe src="{src}" style="border:0" '
            f'allowfullscreen="" loading="lazy" referrerpolicy="no-referrer-when-downgrade">'
            f"</iframe>"
        )
    return ""


def sanitize_for_json(value: Any) -> Any:
    """Recursively sanitize data structure for safe JSON embedding in templates.

    This removes HTML and script tags from all string values in the data structure,
    making it safe to use with |tojson|safe in templates.

    Args:
        value: Any Python data structure (dict, list, str, etc.)

    Returns:
        Sanitized data structure with same shape but cleaned strings
    """
    if isinstance(value, dict):
        return {k: sanitize_for_json(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [sanitize_for_json(item) for item in value]
    elif isinstance(value, str):
        return sanitize_html(value)
    else:
        # Numbers, booleans, None, etc. pass through unchanged
        return value


def safe_json_dumps(data: Any) -> str:
    """Safely serialize data to JSON with sanitization.

    Args:
        data: Data to serialize

    Returns:
        JSON string with sanitized content
    """
    sanitized = sanitize_for_json(data)
    return json.dumps(sanitized)


def sanitize_lakes_data(lakes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sanitize lake data for safe template rendering.

    Args:
        lakes: List of lake dictionaries

    Returns:
        Sanitized lake data
    """
    return [
        {
            "id": lake.get("id"),
            "key": sanitize_html(str(lake.get("key", ""))),
            "name": sanitize_html(str(lake.get("name", ""))),
            "display_name": sanitize_html(str(lake.get("display_name", ""))),
            "ramps": [
                {
                    "id": ramp.get("id"),
                    "name": sanitize_html(str(ramp.get("name", ""))),
                }
                for ramp in lake.get("ramps", [])
            ],
        }
        for lake in lakes
    ]


def sanitize_event_data(
    events: Union[Dict[str, Any], List[Dict[str, Any]]],
) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """Sanitize event data for safe template rendering.

    Args:
        events: Either a single event dictionary or a list of event dictionaries

    Returns:
        Sanitized event data (same type as input)
    """
    # Handle single dict input
    if isinstance(events, dict):
        sanitized_event = {}
        for key, value in events.items():
            if isinstance(value, str):
                sanitized_event[key] = sanitize_html(value)
            else:
                sanitized_event[key] = value
        return sanitized_event

    # Handle list input
    sanitized = []
    for event in events:
        sanitized_event = {}
        for key, value in event.items():
            if isinstance(value, str):
                sanitized_event[key] = sanitize_html(value)
            else:
                sanitized_event[key] = value
        sanitized.append(sanitized_event)
    return sanitized
