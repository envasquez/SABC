from django import template
from django.utils.safestring import mark_safe
import re

register = template.Library()


@register.filter
def to_bullet_list(text):
    """Convert numbered lists to bullet points"""
    if not text:
        return text
    
    # Convert text to string if needed
    text = str(text)
    
    # Replace numbered items with bullet points
    # Match patterns like "1. ", "2) ", "(1) ", etc.
    text = re.sub(r'^(\d+[\.\)]|\(\d+\))\s+', '• ', text, flags=re.MULTILINE)
    text = re.sub(r'\n(\d+[\.\)]|\(\d+\))\s+', '\n• ', text)
    
    # Convert to HTML with line breaks
    text = text.replace('\n', '<br>')
    
    return mark_safe(text)


@register.filter
def lookup(dictionary, key):
    """Lookup a value in a dictionary or object attribute by key/field name"""
    if hasattr(dictionary, key):
        return getattr(dictionary, key)
    elif hasattr(dictionary, "__getitem__"):
        try:
            return dictionary[key]
        except (KeyError, TypeError):
            return None
    return None


@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary"""
    try:
        return dictionary.get(key, "")
    except AttributeError:
        return ""


@register.inclusion_tag("components/responsive_table.html")
def render_responsive_table(queryset, headers, **kwargs):
    """Render a responsive table with mobile card support"""
    return {
        "rows": [
            [getattr(obj, header["field"], "") for header in headers]
            for obj in queryset
        ],
        "headers": [header["label"] for header in headers],
        "mobile_cards": kwargs.get("mobile_cards", True),
        "searchable": kwargs.get("searchable", True),
        "table_class": kwargs.get("table_class", ""),
        "empty_message": kwargs.get("empty_message", "No records found"),
    }


@register.inclusion_tag("components/data_table.html")
def render_data_table(data, headers, **kwargs):
    """Render an advanced data table with sorting and filtering"""
    return {
        "data": data,
        "headers": headers,
        "table_id": kwargs.get("table_id", "dataTable"),
        "searchable": kwargs.get("searchable", True),
        "sortable": kwargs.get("sortable", True),
        "mobile_cards": kwargs.get("mobile_cards", True),
        "actions": kwargs.get("actions", []),
        "empty_message": kwargs.get("empty_message", "No records found"),
        "table_class": kwargs.get("table_class", ""),
    }
