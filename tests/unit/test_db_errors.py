"""Unit tests for database integrity error classification."""

from sqlalchemy.exc import IntegrityError

from core.helpers.db_errors import is_duplicate_email_error


def _integrity_error(orig_message: str) -> IntegrityError:
    """Build an IntegrityError wrapping a driver exception with a given message."""
    return IntegrityError("INSERT INTO anglers ...", {}, Exception(orig_message))


class TestIsDuplicateEmailError:
    """Test detection of the anglers.email unique constraint violation."""

    def test_detects_postgres_unique_violation(self):
        """PostgreSQL names the constraint in the driver message."""
        exc = _integrity_error(
            'duplicate key value violates unique constraint "anglers_email_key"\n'
            "DETAIL:  Key (email)=(angler@example.com) already exists.\n"
        )
        assert is_duplicate_email_error(exc) is True

    def test_detects_sqlite_unique_violation(self):
        """SQLite names the table and column instead of the constraint."""
        exc = _integrity_error("UNIQUE constraint failed: anglers.email")
        assert is_duplicate_email_error(exc) is True

    def test_ignores_other_unique_violations(self):
        """A different table's constraint must not be misread as a duplicate email."""
        exc = _integrity_error(
            'duplicate key value violates unique constraint "poll_votes_poll_id_angler_id_key"'
        )
        assert is_duplicate_email_error(exc) is False

    def test_ignores_not_null_violation(self):
        """Non-uniqueness integrity failures are real defects, not duplicates."""
        exc = _integrity_error('null value in column "name" violates not-null constraint')
        assert is_duplicate_email_error(exc) is False

    def test_handles_missing_orig(self):
        """An IntegrityError without a wrapped driver exception must not raise."""
        exc = IntegrityError("INSERT INTO anglers ...", {}, None)  # type: ignore[arg-type]
        assert is_duplicate_email_error(exc) is False
