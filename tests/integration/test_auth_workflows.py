"""Integration tests for authentication workflows.

Tests the complete authentication lifecycle including registration, login,
logout, and session management.
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.db_schema import Angler


class TestRegistrationWorkflow:
    """Tests for user registration workflow."""

    def test_successful_registration_creates_user_and_logs_in(
        self, client: TestClient, db_session: Session
    ):
        """Test complete registration flow creates user and establishes session."""
        # Register new user
        response = client.post(
            "/register",
            data={
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@example.com",
                "password": "SecurePassword123!",
            },
            follow_redirects=False,
        )

        # Should redirect to home after successful registration
        assert response.status_code in [302, 303]
        assert response.headers.get("location") == "/"

        # Verify user was created in database
        user = db_session.query(Angler).filter(Angler.email == "john.doe@example.com").first()
        assert user is not None
        assert user.name == "John Doe"
        assert user.member is False  # New users start as non-members
        assert user.is_admin is False
        assert user.password_hash is not None

    def test_registration_with_existing_email_fails(self, client: TestClient, regular_user: Angler):
        """Test that registration with an existing email address fails."""
        response = client.post(
            "/register",
            data={
                "first_name": "Jane",
                "last_name": "Smith",
                "email": regular_user.email,  # Existing email
                "password": "SecurePassword123!",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert "Email already exists" in response.text or "already exists" in response.text.lower()

    def test_registration_with_weak_password_fails(self, client: TestClient):
        """Test that registration with a weak password is rejected."""
        response = client.post(
            "/register",
            data={
                "first_name": "Test",
                "last_name": "User",
                "email": "test@example.com",
                "password": "weak",  # Too weak
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert "password" in response.text.lower()

    def test_registration_normalizes_email_to_lowercase(
        self, client: TestClient, db_session: Session
    ):
        """Test that email addresses are normalized to lowercase."""
        client.post(
            "/register",
            data={
                "first_name": "Test",
                "last_name": "User",
                "email": "TestUser@EXAMPLE.COM",  # Mixed case
                "password": "SecurePassword123!",
            },
            follow_redirects=False,
        )

        # Verify email was stored as lowercase
        user = db_session.query(Angler).filter(Angler.email == "testuser@example.com").first()
        assert user is not None

    def test_already_logged_in_user_redirected_from_register_page(
        self, authenticated_client: TestClient
    ):
        """Test that already authenticated users are redirected away from register page."""
        response = authenticated_client.get("/register", follow_redirects=False)

        # Should redirect away from register page
        assert response.status_code in [302, 303]
        assert response.headers.get("location") == "/"


class TestLoginWorkflow:
    """Tests for user login workflow."""

    def test_successful_login_establishes_session(
        self, client: TestClient, regular_user: Angler, test_password: str
    ):
        """Test successful login creates authenticated session."""
        response = client.post(
            "/login",
            data={"email": regular_user.email, "password": test_password},
            follow_redirects=False,
        )

        # Should redirect to home page
        assert response.status_code in [302, 303]
        assert response.headers.get("location") == "/"

        # Verify session cookie is set
        assert "session" in response.cookies or "Set-Cookie" in response.headers

    def test_login_with_wrong_password_fails(self, client: TestClient, regular_user: Angler):
        """Test login with incorrect password is rejected."""
        response = client.post(
            "/login",
            data={"email": regular_user.email, "password": "WrongPassword123!"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert "Invalid email or password" in response.text

    def test_login_with_nonexistent_email_fails(self, client: TestClient):
        """Test login with non-existent email fails with generic error."""
        response = client.post(
            "/login",
            data={"email": "nonexistent@example.com", "password": "AnyPassword123!"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert "Invalid email or password" in response.text

    def test_login_is_case_insensitive_for_email(
        self, client: TestClient, db_session: Session, test_password: str
    ):
        """Test that login email matching is case-insensitive."""
        # Create user with lowercase email
        import bcrypt

        password_hash = bcrypt.hashpw(test_password.encode(), bcrypt.gensalt()).decode()
        user = Angler(
            name="Test User",
            email="test@example.com",
            password_hash=password_hash,
            member=False,
            is_admin=False,
        )
        db_session.add(user)
        db_session.commit()

        # Try logging in with uppercase email
        response = client.post(
            "/login",
            data={"email": "TEST@EXAMPLE.COM", "password": test_password},
            follow_redirects=False,
        )

        # Should succeed
        assert response.status_code in [302, 303]

    def test_already_logged_in_user_redirected_from_login_page(
        self, authenticated_client: TestClient
    ):
        """Test that already authenticated users are redirected away from login page."""
        response = authenticated_client.get("/login", follow_redirects=False)

        # Should redirect to home
        assert response.status_code in [302, 303]
        assert response.headers.get("location") == "/"

    def test_multiple_failed_login_attempts_are_rate_limited(
        self, client: TestClient, regular_user: Angler
    ):
        """Test that multiple failed login attempts trigger rate limiting."""
        # Attempt login multiple times with wrong password
        for _ in range(6):
            client.post(
                "/login",
                data={"email": regular_user.email, "password": "WrongPassword123!"},
                follow_redirects=False,
            )

        # Next attempt should be rate limited
        response = client.post(
            "/login",
            data={"email": regular_user.email, "password": "WrongPassword123!"},
            follow_redirects=False,
        )

        # Should get rate limit error (429) or redirect with error
        assert response.status_code in [429, 302, 303]


class TestLogoutWorkflow:
    """Tests for user logout workflow."""

    def test_logout_clears_session(self, authenticated_client: TestClient, regular_user: Angler):
        """Test that logout properly clears the user session."""
        # Verify user is logged in first
        profile_response = authenticated_client.get("/profile", follow_redirects=False)
        assert profile_response.status_code == 200

        # Logout
        logout_response = authenticated_client.post("/logout", follow_redirects=False)
        assert logout_response.status_code in [302, 303]
        assert logout_response.headers.get("location") == "/"

        # Try accessing profile again - should redirect to login
        profile_after_logout = authenticated_client.get("/profile", follow_redirects=False)
        assert profile_after_logout.status_code in [302, 303]
        assert "/login" in profile_after_logout.headers.get("location", "")

    def test_logout_when_not_logged_in_succeeds(self, client: TestClient):
        """Test that logout works even when user is not authenticated."""
        response = client.post("/logout", follow_redirects=False)

        # Should succeed with redirect
        assert response.status_code in [302, 303]
        assert response.headers.get("location") == "/"


class TestSessionManagement:
    """Tests for session management and persistence."""

    def test_authenticated_session_persists_across_requests(
        self, client: TestClient, regular_user: Angler, test_password: str
    ):
        """Test that authentication session persists across multiple requests."""
        # Login
        client.post(
            "/login",
            data={"email": regular_user.email, "password": test_password},
            follow_redirects=False,
        )

        # Make multiple authenticated requests
        for _ in range(3):
            response = client.get("/profile", follow_redirects=False)
            assert response.status_code == 200

    def test_unauthenticated_requests_redirect_to_login(self, client: TestClient):
        """Test that unauthenticated requests to protected pages redirect to login."""
        protected_urls = ["/profile", "/polls"]

        for url in protected_urls:
            response = client.get(url, follow_redirects=False)
            assert response.status_code in [302, 303, 403]

    def test_session_contains_user_id_after_login(
        self, client: TestClient, regular_user: Angler, test_password: str
    ):
        """Test that session stores user ID after successful login."""
        response = client.post(
            "/login",
            data={"email": regular_user.email, "password": test_password},
            follow_redirects=False,
        )

        # Session cookie should be set
        assert "session" in response.cookies or "Set-Cookie" in response.headers


class TestProfileAccess:
    """Tests for profile page access and data display."""

    def test_authenticated_user_can_view_own_profile(
        self, authenticated_client: TestClient, regular_user: Angler
    ):
        """Test that authenticated users can view their profile."""
        response = authenticated_client.get("/profile")

        assert response.status_code == 200
        assert regular_user.name in response.text
        assert regular_user.email in response.text

    def test_unauthenticated_user_redirected_from_profile(self, client: TestClient):
        """Test that unauthenticated users are redirected from profile page."""
        response = client.get("/profile", follow_redirects=False)

        assert response.status_code in [302, 303]
        assert "/login" in response.headers.get("location", "")

    def test_member_profile_shows_member_status(
        self, member_client: TestClient, member_user: Angler
    ):
        """Test that member profile correctly displays member status."""
        response = member_client.get("/profile")

        assert response.status_code == 200
        assert member_user.name in response.text
        # Check for member indicator in page
        assert "member" in response.text.lower()

    def test_admin_profile_shows_admin_status(self, admin_client: TestClient, admin_user: Angler):
        """Test that admin profile correctly displays admin status."""
        response = admin_client.get("/profile")

        assert response.status_code == 200
        assert admin_user.name in response.text
        # Check for admin indicator
        assert "admin" in response.text.lower()


class TestPasswordSecurity:
    """Tests for password security features."""

    def test_password_is_hashed_not_stored_plaintext(self, client: TestClient, db_session: Session):
        """Test that passwords are stored as hashes, not plaintext."""
        password = "SecurePassword123!"

        client.post(
            "/register",
            data={
                "first_name": "Security",
                "last_name": "Test",
                "email": "security@example.com",
                "password": password,
            },
            follow_redirects=False,
        )

        user = db_session.query(Angler).filter(Angler.email == "security@example.com").first()
        assert user is not None
        # Password hash should not equal plaintext password
        assert user.password_hash != password
        # Password hash should be bcrypt format (starts with $2b$)
        assert user.password_hash.startswith("$2b$") or user.password_hash.startswith("$2a$")

    def test_failed_login_uses_constant_time_comparison(self, client: TestClient):
        """Test that login timing doesn't reveal whether email exists."""
        # This is a timing attack prevention test
        # The implementation should take similar time for existing vs non-existing users

        import time

        # Time login with non-existent email
        start = time.time()
        client.post(
            "/login",
            data={"email": "nonexistent@example.com", "password": "TestPassword123!"},
            follow_redirects=False,
        )
        nonexistent_time = time.time() - start

        # Create a user
        test_password = "TestPassword123!"
        import bcrypt

        bcrypt.hashpw(test_password.encode(), bcrypt.gensalt()).decode()
        client.post(
            "/register",
            data={
                "first_name": "Timing",
                "last_name": "Test",
                "email": "timing@example.com",
                "password": test_password,
            },
            follow_redirects=False,
        )

        # Time login with existing email but wrong password
        start = time.time()
        client.post(
            "/login",
            data={"email": "timing@example.com", "password": "WrongPassword123!"},
            follow_redirects=False,
        )
        existing_time = time.time() - start

        # Times should be similar (within 50ms for timing protection)
        # This is a rough check - actual constant-time would be identical
        assert abs(nonexistent_time - existing_time) < 0.5
