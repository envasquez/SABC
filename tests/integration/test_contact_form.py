"""Contact form tests."""

from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.db_schema import Angler
from tests.conftest import post_with_csrf


class TestContactFormPage:
    """Test the contact form is displayed on the about page."""

    def test_about_page_shows_contact_form(self, client: TestClient):
        """Test that the about page contains the contact form."""
        response = client.get("/about")
        assert response.status_code == 200
        assert "Contact Us" in response.text
        assert 'action="/about/contact"' in response.text
        assert 'name="name"' in response.text
        assert 'name="email"' in response.text
        assert 'name="subject"' in response.text
        assert 'name="message"' in response.text


class TestContactFormSubmission:
    """Test contact form submission logic."""

    def test_contact_form_missing_fields(self, client: TestClient):
        """Test that missing fields return an error."""
        response = post_with_csrf(
            client,
            "/about/contact",
            data={"name": "Test", "email": "", "subject": "", "message": ""},
        )
        assert response.status_code == 200  # After redirect
        assert "error" in str(response.url) or "All fields are required" in response.text

    def test_contact_form_success(
        self, client: TestClient, db_session: Session, password_hash: str
    ):
        """Test successful contact form submission sends email to admins."""
        # Create an admin user with a valid email
        admin = Angler(
            name="Admin User",
            email="admin@example.com",
            password_hash=password_hash,
            member=True,
            is_admin=True,
        )
        db_session.add(admin)
        db_session.commit()

        with patch("routes.pages.home.send_contact_email", return_value=True) as mock_send:
            response = post_with_csrf(
                client,
                "/about/contact",
                data={
                    "name": "John Doe",
                    "email": "john@example.com",
                    "subject": "Question about membership",
                    "message": "I would like to join the club.",
                },
            )
            assert response.status_code == 200  # After redirect
            mock_send.assert_called_once_with(
                admin_emails=["admin@example.com"],
                sender_name="John Doe",
                sender_email="john@example.com",
                subject_line="Question about membership",
                message="I would like to join the club.",
            )

    def test_contact_form_excludes_placeholder_domains(
        self, client: TestClient, db_session: Session, password_hash: str
    ):
        """Test that admin emails with placeholder domains are excluded."""
        # Admin with placeholder domain - should be excluded
        admin_placeholder = Angler(
            name="Placeholder Admin",
            email="admin@sabc.com",
            password_hash=password_hash,
            member=True,
            is_admin=True,
        )
        # Admin with club domain - should be excluded
        admin_club = Angler(
            name="Club Admin",
            email="admin@saustinbc.com",
            password_hash=password_hash,
            member=True,
            is_admin=True,
        )
        # Admin with valid email - should be included
        admin_valid = Angler(
            name="Valid Admin",
            email="valid@example.com",
            password_hash=password_hash,
            member=True,
            is_admin=True,
        )
        db_session.add_all([admin_placeholder, admin_club, admin_valid])
        db_session.commit()

        with patch("routes.pages.home.send_contact_email", return_value=True) as mock_send:
            response = post_with_csrf(
                client,
                "/about/contact",
                data={
                    "name": "Jane",
                    "email": "jane@example.com",
                    "subject": "Test",
                    "message": "Hello",
                },
            )
            assert response.status_code == 200
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert call_args.kwargs["admin_emails"] == ["valid@example.com"]

    def test_contact_form_no_admins(self, client: TestClient, db_session: Session):
        """Test contact form when no admin emails are available."""
        # No admins in DB
        response = post_with_csrf(
            client,
            "/about/contact",
            data={
                "name": "Test",
                "email": "test@example.com",
                "subject": "Test",
                "message": "Hello",
            },
        )
        assert response.status_code == 200
        assert "error" in str(response.url) or "Unable to send" in response.text

    def test_contact_form_email_failure(
        self, client: TestClient, db_session: Session, password_hash: str
    ):
        """Test contact form when email sending fails."""
        admin = Angler(
            name="Admin",
            email="admin@example.com",
            password_hash=password_hash,
            member=True,
            is_admin=True,
        )
        db_session.add(admin)
        db_session.commit()

        with patch("routes.pages.home.send_contact_email", return_value=False):
            response = post_with_csrf(
                client,
                "/about/contact",
                data={
                    "name": "Test",
                    "email": "test@example.com",
                    "subject": "Test",
                    "message": "Hello",
                },
            )
            assert response.status_code == 200
            assert "error" in str(response.url) or "Failed to send" in response.text


class TestContactEmailTemplate:
    """Test the contact email template generation."""

    def test_generate_contact_email_content(self):
        """Test that email content is generated correctly."""
        from core.email.templates import generate_contact_email_content

        subject, text_body, html_body = generate_contact_email_content(
            sender_name="John Doe",
            sender_email="john@example.com",
            subject_line="Membership inquiry",
            message="I want to join!",
        )

        assert "Contact: Membership inquiry" in subject
        assert "John Doe" in text_body
        assert "john@example.com" in text_body
        assert "I want to join!" in text_body
        assert "John Doe" in html_body
        assert "john@example.com" in html_body
        assert "I want to join!" in html_body
        assert "Reply-To" not in html_body  # Reply-To is a header, not in body
