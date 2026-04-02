"""Shared type definitions for the SABC application."""

from datetime import date, datetime
from typing import TypedDict


class UserDict(TypedDict, total=False):
    """Type definition for user/angler dictionaries returned from database queries.

    Maps to the 'anglers' table columns. Uses total=False because not all fields
    are always present (e.g., get_current_user may return a subset, and some
    fields like password_hash are excluded from certain queries).
    """

    id: int
    name: str
    email: str | None
    member: bool | None
    is_admin: bool | None
    password_hash: str | None
    year_joined: int | None
    phone: str | None
    created_at: datetime | None
    dues_paid_through: date | None
    dues_banner_dismissed_at: datetime | None
