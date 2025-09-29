"""Tests for user utility functions."""

from sqlalchemy import text

from core.helpers.user_utils import generate_guest_email


class TestGenerateGuestEmail:
    """Test email generation for guest users."""

    def test_generate_basic_email(self, db_conn):
        """Test generating email from full name."""
        email = generate_guest_email("John Smith")
        assert email == "john.smith@sabc.com"

    def test_generate_email_with_special_chars(self, db_conn):
        """Test email generation strips special characters."""
        email = generate_guest_email("John O'Brien")
        assert email == "john.obrien@sabc.com"

    def test_generate_email_single_name(self, db_conn):
        """Test that single names return None."""
        email = generate_guest_email("John")
        assert email is None

    def test_generate_email_empty_name(self, db_conn):
        """Test that empty names return None."""
        email = generate_guest_email("")
        assert email is None

    def test_generate_email_existing_conflict(self, db_conn):
        """Test numbered email when base email exists."""
        # Create existing user with base email
        db_conn.execute(
            text(
                "INSERT INTO anglers (name, email) VALUES ('Existing User', 'john.smith@sabc.com')"
            ),
        )
        db_conn.commit()

        # Should generate numbered version
        email = generate_guest_email("John Smith")
        assert email == "john.smith2@sabc.com"

    def test_generate_email_multiple_conflicts(self, db_conn):
        """Test numbered email with multiple conflicts."""
        # Create multiple conflicting emails
        db_conn.execute(
            text("INSERT INTO anglers (name, email) VALUES ('User 1', 'john.smith@sabc.com')"),
        )
        db_conn.execute(
            text("INSERT INTO anglers (name, email) VALUES ('User 2', 'john.smith2@sabc.com')"),
        )
        db_conn.execute(
            text("INSERT INTO anglers (name, email) VALUES ('User 3', 'john.smith3@sabc.com')"),
        )
        db_conn.commit()

        # Should generate john.smith4@sabc.com
        email = generate_guest_email("John Smith")
        assert email == "john.smith4@sabc.com"

    def test_generate_email_exclude_existing_user(self, db_conn):
        """Test that existing user ID is excluded from conflict check."""
        # Create user
        result = db_conn.execute(
            text(
                "INSERT INTO anglers (name, email) VALUES ('John Smith', 'john.smith@sabc.com') RETURNING id"
            ),
        )
        user_id = result.fetchone()[0]
        db_conn.commit()

        # Should return same email when excluding this user
        email = generate_guest_email("John Smith", existing_user_id=user_id)
        assert email == "john.smith@sabc.com"

    def test_generate_email_three_part_name(self, db_conn):
        """Test email generation with three-part name."""
        email = generate_guest_email("John Michael Smith")
        assert email == "john.smith@sabc.com"  # Uses first and last

    def test_generate_email_numbers_in_name(self, db_conn):
        """Test email generation preserves numbers."""
        email = generate_guest_email("John2 Smith3")
        assert email == "john2.smith3@sabc.com"
