"""Data sanitization utilities for safe template rendering."""

import json
import re
from typing import Any, Dict, List


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


def sanitize_event_data(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sanitize event data for safe template rendering.

    Args:
        events: List of event dictionaries

    Returns:
        Sanitized event data
    """
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
