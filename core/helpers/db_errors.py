"""Helpers for interpreting database integrity errors.

A ``UniqueViolation`` surfaces as a generic :class:`IntegrityError`, so callers
that want to turn one specific constraint into a friendly message need a way to
ask *which* constraint failed. Matching on the driver's message text is the only
portable option — SQLAlchemy does not expose the constraint name as structured
data across dialects.
"""

from sqlalchemy.exc import IntegrityError

# PostgreSQL names the constraint in its error text; SQLite names the table and
# column instead. Both dialects are in play (production is Postgres, the test
# suite runs on SQLite), so both spellings have to be recognised.
_EMAIL_CONSTRAINT_MARKERS = (
    "anglers_email_key",  # PostgreSQL: unique constraint name
    "anglers.email",  # SQLite: "UNIQUE constraint failed: anglers.email"
)


def is_duplicate_email_error(exc: IntegrityError) -> bool:
    """Return True if ``exc`` was caused by the anglers.email unique constraint.

    Used to distinguish "this email is already registered" — an expected,
    user-correctable outcome — from every other integrity failure, which is a
    real defect and must not be reported to the user as a duplicate email.

    Args:
        exc: The IntegrityError raised by the failed flush or commit.

    Returns:
        True when the failure is the email uniqueness constraint.
    """
    # ``exc.orig`` is the underlying DBAPI exception, which carries the detailed
    # message; fall back to the wrapper if it is absent.
    message = str(getattr(exc, "orig", None) or exc)
    return any(marker in message for marker in _EMAIL_CONSTRAINT_MARKERS)
