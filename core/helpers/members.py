"""Shared definitions of membership status.

Three pages each used to answer "how many active members are there?"
differently, and they disagreed in production:

* the home page counted ``member AND dues_paid_through >= today`` but never
  excluded the seed admin account, so it over-reported by one;
* the roster counted a per-year ``was_member`` override with no dues check at
  all, so it counted members whose dues date was never filled in;
* ``/admin/users`` had a third copy of the dues predicate.

The admin exclusion is keyed on the account's *email*, not its display name.
The production seed account is named "SABC Admin", so the ``name != 'Admin
User'`` filters scattered through the codebase silently match nothing there.
"""

from datetime import date
from typing import Any, List

from sqlalchemy.sql.elements import ColumnElement

from core.db_schema import Angler

#: Email of the seed administrator account. Matched case-insensitively.
#: Identity is keyed on this rather than ``anglers.name`` because the display
#: name is editable (production renamed it to "SABC Admin") while the email is
#: pinned by ``scripts/setup_admin.py`` and carries a UNIQUE constraint.
SEED_ADMIN_EMAIL = "admin@sabc.com"

#: Portable, NULL-safe SQL predicate excluding the seed admin. ``email`` is
#: nullable, and a bare ``email != '...'`` evaluates to NULL for those rows,
#: which silently drops them. COALESCE works on both PostgreSQL and SQLite.
EXCLUDE_SEED_ADMIN_SQL = f"COALESCE(LOWER(a.email), '') != '{SEED_ADMIN_EMAIL}'"


def is_dues_current(dues_paid_through: Any) -> bool:
    """Check whether dues are paid through today or later.

    Accepts a ``date``, an ISO-8601 string (raw SQL rows hand back strings on
    some drivers), or None. A missing or unparseable value counts as not
    current.

    Args:
        dues_paid_through: Date the member's dues lapse, or None.

    Returns:
        True if dues are current, False otherwise.
    """
    if dues_paid_through is None:
        return False
    if isinstance(dues_paid_through, str):
        try:
            dues_paid_through = date.fromisoformat(dues_paid_through)
        except ValueError:
            return False
    if isinstance(dues_paid_through, date):
        return dues_paid_through >= date.today()
    return False


def is_seed_admin(email: Any) -> bool:
    """Check whether an email belongs to the seed administrator account."""
    return isinstance(email, str) and email.lower() == SEED_ADMIN_EMAIL


def active_member_criteria() -> List[ColumnElement[bool]]:
    """ORM filter criteria for "an active member of the club".

    A member flagged as such, with current dues, that is not the seed admin
    account. Spread into a query with ``.filter(*active_member_criteria())``.
    """
    return [
        Angler.member.is_(True),
        Angler.dues_paid_through.isnot(None),
        Angler.dues_paid_through >= date.today(),
        Angler.email.is_(None) | (Angler.email.notilike(SEED_ADMIN_EMAIL)),
    ]
