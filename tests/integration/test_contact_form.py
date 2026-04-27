"""Contact form tests."""

import time
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.db_schema import Angler
from tests.conftest import post_with_csrf


def _valid_form_data(**overrides: str) -> dict:
    """Return valid contact form data with spam protection fields."""
    data = {
        "name": "John Doe",
        "email": "john@example.com",
        "subject": "Question about membership",
        "message": "I would like to join the club.",
        "website": "",  # honeypot - must be empty
        "phone": "",  # alt honeypot - must be empty
        "form_loaded_at": str(int(time.time()) - 15),  # loaded 15 seconds ago
    }
    data.update(overrides)
    return data


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

    def test_about_page_has_honeypot_field(self, client: TestClient):
        """Test that the about page contains the hidden honeypot fields."""
        response = client.get("/about")
        assert response.status_code == 200
        assert 'name="website"' in response.text
        assert 'name="phone"' in response.text
        assert 'name="form_loaded_at"' in response.text


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
                data=_valid_form_data(),
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
                data=_valid_form_data(
                    name="Jane",
                    email="jane@example.com",
                    subject="Test",
                    message="Hello, I have a question about joining.",
                ),
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
            data=_valid_form_data(
                name="Test",
                email="test@example.com",
                subject="Test",
                message="Hello, this is a test message.",
            ),
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
                data=_valid_form_data(
                    name="Test",
                    email="test@example.com",
                    subject="Test",
                    message="Hello, this is a test message.",
                ),
            )
            assert response.status_code == 200
            assert "error" in str(response.url) or "Failed to send" in response.text


class TestContactFormSpamProtection:
    """Test spam protection mechanisms."""

    def test_honeypot_blocks_spam(self, client: TestClient):
        """Test that filling the honeypot field blocks the submission."""
        with patch("routes.pages.home.send_contact_email") as mock_send:
            response = post_with_csrf(
                client,
                "/about/contact",
                data=_valid_form_data(website="http://spam.com"),
            )
            assert response.status_code == 200
            # Returns fake success to not tip off bots
            assert "success" in str(response.url) or "been sent" in response.text
            # But email was NOT actually sent
            mock_send.assert_not_called()

    def test_fast_submission_blocks_spam(self, client: TestClient):
        """Test that submitting too quickly blocks the submission."""
        with patch("routes.pages.home.send_contact_email") as mock_send:
            response = post_with_csrf(
                client,
                "/about/contact",
                data=_valid_form_data(form_loaded_at=str(int(time.time()))),  # just now
            )
            assert response.status_code == 200
            assert "success" in str(response.url) or "been sent" in response.text
            mock_send.assert_not_called()

    def test_missing_timestamp_blocks_spam(self, client: TestClient):
        """Test that missing form_loaded_at blocks the submission."""
        with patch("routes.pages.home.send_contact_email") as mock_send:
            response = post_with_csrf(
                client,
                "/about/contact",
                data=_valid_form_data(form_loaded_at=""),
            )
            assert response.status_code == 200
            assert "success" in str(response.url) or "been sent" in response.text
            mock_send.assert_not_called()

    def test_url_in_name_blocks_spam(self, client: TestClient):
        """Test that URLs in the name field block the submission."""
        with patch("routes.pages.home.send_contact_email") as mock_send:
            response = post_with_csrf(
                client,
                "/about/contact",
                data=_valid_form_data(name="http://spam.example.com"),
            )
            assert response.status_code == 200
            assert "success" in str(response.url) or "been sent" in response.text
            mock_send.assert_not_called()

    def test_message_mostly_urls_blocks_spam(self, client: TestClient):
        """Test that messages that are mostly URLs are blocked."""
        with patch("routes.pages.home.send_contact_email") as mock_send:
            response = post_with_csrf(
                client,
                "/about/contact",
                data=_valid_form_data(message="http://spam.example.com/deposit"),
            )
            assert response.status_code == 200
            assert "success" in str(response.url) or "been sent" in response.text
            mock_send.assert_not_called()

    def test_legitimate_message_with_url_passes(
        self, client: TestClient, db_session: Session, password_hash: str
    ):
        """Test that a real message containing a URL is allowed."""
        admin = Angler(
            name="Admin",
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
                data=_valid_form_data(
                    message="Hi, I saw your site at https://sabc.com and I want to join the club!"
                ),
            )
            assert response.status_code == 200
            mock_send.assert_called_once()


class TestSpamDetectionUnit:
    """Unit tests for the _is_spam_submission function."""

    def test_clean_submission(self):
        from routes.pages.home import _is_spam_submission

        result = _is_spam_submission(
            "", "", str(int(time.time()) - 15), "John", "Question", "A real message here"
        )
        assert result is None

    def test_honeypot_filled(self):
        from routes.pages.home import _is_spam_submission

        result = _is_spam_submission(
            "spam", "", str(int(time.time()) - 15), "John", "Question", "A real message here"
        )
        assert result == "honeypot filled"

    def test_alt_honeypot_filled(self):
        from routes.pages.home import _is_spam_submission

        result = _is_spam_submission(
            "", "555-1212", str(int(time.time()) - 15), "John", "Question", "A real message here"
        )
        assert result == "alt honeypot filled"

    def test_too_fast(self):
        from routes.pages.home import _is_spam_submission

        result = _is_spam_submission(
            "", "", str(int(time.time())), "John", "Question", "A real message here"
        )
        assert result is not None
        assert "too fast" in result

    def test_invalid_timestamp(self):
        from routes.pages.home import _is_spam_submission

        result = _is_spam_submission("", "", "not-a-number", "John", "Question", "A real message")
        assert result == "missing timestamp"

    def test_url_in_name(self):
        from routes.pages.home import _is_spam_submission

        result = _is_spam_submission(
            "",
            "",
            str(int(time.time()) - 15),
            "http://spam.com",
            "Question",
            "A real message here",
        )
        assert result == "URL in name field"

    def test_message_mostly_urls(self):
        from routes.pages.home import _is_spam_submission

        result = _is_spam_submission(
            "", "", str(int(time.time()) - 15), "John", "Question", "https://spam.example.com"
        )
        assert result is not None
        assert "URLs" in result

    def test_solicitor_pattern_two_matches_blocked(self):
        from routes.pages.home import _is_spam_submission

        msg = (
            "Hello, I noticed your website while researching local clubs. "
            "Our team can help boost your search engine ranking with our SEO services. "
            "Reply for a free consultation."
        )
        result = _is_spam_submission(
            "", "", str(int(time.time()) - 15), "Marketing Pro", "Quick question", msg
        )
        assert result is not None
        assert "solicitor" in result

    def test_solicitor_single_phrase_allowed(self):
        from routes.pages.home import _is_spam_submission

        # One coincidental match should not block legitimate users.
        msg = "Hi, I noticed your website mentions tournament dates. When is the next one?"
        result = _is_spam_submission(
            "", "", str(int(time.time()) - 15), "John Doe", "Tournament dates", msg
        )
        assert result is None


class TestTurnstileVerification:
    """Test Cloudflare Turnstile CAPTCHA integration."""

    def test_turnstile_skipped_when_not_configured(
        self, client: TestClient, db_session: Session, password_hash: str
    ):
        """Test that Turnstile is skipped when no secret key is set."""
        admin = Angler(
            name="Admin",
            email="admin@example.com",
            password_hash=password_hash,
            member=True,
            is_admin=True,
        )
        db_session.add(admin)
        db_session.commit()

        # No TURNSTILE_SECRET_KEY set (default) — should send email normally
        with patch("routes.pages.home.send_contact_email", return_value=True) as mock_send:
            response = post_with_csrf(
                client,
                "/about/contact",
                data=_valid_form_data(),
            )
            assert response.status_code == 200
            mock_send.assert_called_once()

    def test_turnstile_blocks_invalid_token(
        self, client: TestClient, db_session: Session, password_hash: str
    ):
        """Test that invalid Turnstile token blocks submission."""
        admin = Angler(
            name="Admin",
            email="admin@example.com",
            password_hash=password_hash,
            member=True,
            is_admin=True,
        )
        db_session.add(admin)
        db_session.commit()

        with (
            patch("routes.pages.home.TURNSTILE_SECRET_KEY", "test-secret-key"),
            patch(
                "routes.pages.home._verify_turnstile", new_callable=AsyncMock, return_value=False
            ),
            patch("routes.pages.home.send_contact_email") as mock_send,
        ):
            response = post_with_csrf(
                client,
                "/about/contact",
                data=_valid_form_data(),
            )
            assert response.status_code == 200
            assert "error" in str(response.url) or "CAPTCHA" in response.text
            mock_send.assert_not_called()

    def test_turnstile_allows_valid_token(
        self, client: TestClient, db_session: Session, password_hash: str
    ):
        """Test that valid Turnstile token allows submission."""
        admin = Angler(
            name="Admin",
            email="admin@example.com",
            password_hash=password_hash,
            member=True,
            is_admin=True,
        )
        db_session.add(admin)
        db_session.commit()

        with (
            patch("routes.pages.home.TURNSTILE_SECRET_KEY", "test-secret-key"),
            patch("routes.pages.home._verify_turnstile", new_callable=AsyncMock, return_value=True),
            patch("routes.pages.home.send_contact_email", return_value=True) as mock_send,
        ):
            response = post_with_csrf(
                client,
                "/about/contact",
                data={**_valid_form_data(), "cf-turnstile-response": "valid-token"},
            )
            assert response.status_code == 200
            mock_send.assert_called_once()

    def test_turnstile_rejects_missing_token_when_site_key_configured(
        self, client: TestClient, db_session: Session, password_hash: str
    ):
        """Test that missing Turnstile token is rejected when site key is set.

        This is the core fix for issue #278: when the Turnstile widget is
        displayed (TURNSTILE_SITE_KEY is set), submitting without completing
        the CAPTCHA must fail -- even if the secret key is not configured.
        """
        admin = Angler(
            name="Admin",
            email="admin@example.com",
            password_hash=password_hash,
            member=True,
            is_admin=True,
        )
        db_session.add(admin)
        db_session.commit()

        with (
            patch("routes.pages.home.TURNSTILE_SITE_KEY", "test-site-key"),
            patch("routes.pages.home.TURNSTILE_SECRET_KEY", ""),
            patch("routes.pages.home.send_contact_email") as mock_send,
        ):
            response = post_with_csrf(
                client,
                "/about/contact",
                data=_valid_form_data(),  # no cf-turnstile-response field
            )
            assert response.status_code == 200
            assert "error" in str(response.url) or "CAPTCHA" in response.text
            mock_send.assert_not_called()

    def test_turnstile_rejects_empty_token_when_site_key_configured(
        self, client: TestClient, db_session: Session, password_hash: str
    ):
        """Test that an empty Turnstile token is rejected when site key is set."""
        admin = Angler(
            name="Admin",
            email="admin@example.com",
            password_hash=password_hash,
            member=True,
            is_admin=True,
        )
        db_session.add(admin)
        db_session.commit()

        with (
            patch("routes.pages.home.TURNSTILE_SITE_KEY", "test-site-key"),
            patch("routes.pages.home.TURNSTILE_SECRET_KEY", "test-secret-key"),
            patch("routes.pages.home.send_contact_email") as mock_send,
        ):
            response = post_with_csrf(
                client,
                "/about/contact",
                data={**_valid_form_data(), "cf-turnstile-response": ""},
            )
            assert response.status_code == 200
            assert "error" in str(response.url) or "CAPTCHA" in response.text
            mock_send.assert_not_called()

    def test_turnstile_widget_shown_when_configured(self, client: TestClient):
        """Test that Turnstile widget appears when site key is set."""
        with patch("routes.pages.home.TURNSTILE_SITE_KEY", "test-site-key"):
            response = client.get("/about")
            assert response.status_code == 200
            assert "cf-turnstile" in response.text
            assert "test-site-key" in response.text

    def test_turnstile_widget_hidden_when_not_configured(self, client: TestClient):
        """Test that Turnstile widget is hidden when no site key is set."""
        response = client.get("/about")
        assert response.status_code == 200
        assert "cf-turnstile" not in response.text


class TestVerifyTurnstileUnit:
    """Unit tests for the _verify_turnstile function."""

    def test_skips_when_no_secret(self):
        import asyncio

        from routes.pages.home import _verify_turnstile

        with patch("routes.pages.home.TURNSTILE_SECRET_KEY", ""):
            result = asyncio.get_event_loop().run_until_complete(_verify_turnstile("any-token"))
            assert result is True

    def test_rejects_empty_token(self):
        import asyncio

        from routes.pages.home import _verify_turnstile

        with patch("routes.pages.home.TURNSTILE_SECRET_KEY", "secret"):
            result = asyncio.get_event_loop().run_until_complete(_verify_turnstile(""))
            assert result is False


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
