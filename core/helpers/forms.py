"""Form data helper utilities for type-safe extraction."""

from typing import Optional, Union

from fastapi import UploadFile
from starlette.datastructures import FormData


def get_form_string(form_data: Union[FormData, dict], key: str, default: str = "") -> str:
    """
    Safely extract string value from form data.

    FastAPI form data can contain UploadFile | str values.
    This helper ensures we only extract string values.

    Args:
        form_data: Form data from request.form() or dict
        key: Key to extract
        default: Default value if key not found or value is not string

    Returns:
        String value or default
    """
    value = form_data.get(key, default)
    if isinstance(value, str):
        return value.strip()
    return default


def get_form_int(
    form_data: Union[FormData, dict], key: str, default: Optional[int] = None
) -> Optional[int]:
    """
    Safely extract integer value from form data.

    Args:
        form_data: Form data from request.form() or dict
        key: Key to extract
        default: Default value if key not found or conversion fails

    Returns:
        Integer value or default
    """
    value = form_data.get(key)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except (ValueError, AttributeError):
            return default
    return default


def get_form_float(
    form_data: Union[FormData, dict], key: str, default: Optional[float] = None
) -> Optional[float]:
    """
    Safely extract float value from form data.

    Args:
        form_data: Form data from request.form() or dict
        key: Key to extract
        default: Default value if key not found or conversion fails

    Returns:
        Float value or default
    """
    value = form_data.get(key)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except (ValueError, AttributeError):
            return default
    return default


def get_form_file(form_data: Union[FormData, dict], key: str) -> Optional[UploadFile]:
    """
    Safely extract UploadFile from form data.

    Args:
        form_data: Form data from request.form() or dict
        key: Key to extract

    Returns:
        UploadFile or None
    """
    value = form_data.get(key)
    if isinstance(value, UploadFile):
        return value
    return None


def get_form_bool(form_data: Union[FormData, dict], key: str, default: bool = False) -> bool:
    """
    Safely extract boolean value from form data.

    Form checkboxes are only present when checked, so we check for key existence.

    Args:
        form_data: Form data from request.form() or dict
        key: Key to extract
        default: Default value if key not found

    Returns:
        Boolean value
    """
    value = form_data.get(key)
    if value is None:
        return default
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes", "on")
    return default
