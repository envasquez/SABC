"""Data sanitization utilities for safe template rendering."""

import json
import re
from html.parser import HTMLParser
from typing import Any, Dict, List, Union

# Elements whose *contents* are not human-readable text and must be discarded
# entirely (not just have their tags stripped). A regex-based stripper would
# leave the script/style body behind as plain text — this set lets us drop it.
_SKIP_CONTENT_TAGS = frozenset({"script", "style"})

# Dangerous URI prefixes to scrub from the extracted text. Tag/attribute
# removal is handled by the parser; these literals can still appear in plain
# text (e.g. a pasted "javascript:alert(1)" string) and must be removed.
_DANGEROUS_PREFIXES = ("javascript:", "data:")


class _HTMLTextExtractor(HTMLParser):
    """Parse HTML and collect only the visible text content.

    Using the stdlib HTML parser instead of a regex makes tag stripping
    robust against malformed, nested, or unclosed tags — the parser tolerates
    all of those, whereas ``re.sub(r"<[^>]*>", "")`` is trivially bypassable.

    Text inside ``<script>``/``<style>`` elements is dropped entirely: those
    bodies are code, not content, so emitting them as text would be unsafe.
    """

    def __init__(self) -> None:
        # convert_charrefs=True so entities like &amp; resolve to text.
        super().__init__(convert_charrefs=True)
        self._chunks: List[str] = []
        # Depth counter for skip-content elements; >0 means "drop text".
        self._skip_depth: int = 0

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        if tag.lower() in _SKIP_CONTENT_TAGS:
            self._skip_depth += 1

    def handle_startendtag(self, tag: str, attrs: Any) -> None:
        # Self-closing tags (e.g. <br/>) contribute no text; nothing to do.
        return None

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in _SKIP_CONTENT_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        # Only keep text that is not inside a script/style element.
        if self._skip_depth == 0:
            self._chunks.append(data)

    def get_text(self) -> str:
        """Return the accumulated visible text."""
        return "".join(self._chunks)


def sanitize_html(text: str) -> str:
    """Remove HTML tags and potentially dangerous content from text.

    HTML is parsed with the stdlib :class:`html.parser.HTMLParser`, which
    reliably strips every tag — including malformed or unclosed ones that a
    regex would miss — and returns only the text content. The contents of
    ``<script>`` and ``<style>`` elements are discarded entirely.

    Args:
        text: Input text that may contain HTML

    Returns:
        Sanitized text with HTML removed
    """
    if not text:
        return ""

    # Parse and extract visible text only (all tags stripped, script/style
    # bodies dropped). HTMLParser does not raise on malformed markup.
    extractor = _HTMLTextExtractor()
    extractor.feed(text)
    extractor.close()
    result = extractor.get_text()

    # Scrub dangerous URI prefixes that can appear as plain text even after
    # tags are gone (e.g. a literal "javascript:alert(1)" string).
    for prefix in _DANGEROUS_PREFIXES:
        result = re.sub(re.escape(prefix), "", result, flags=re.IGNORECASE)

    return result


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
