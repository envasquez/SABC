"""Auth registration and profile tests."""

from fastapi.testclient import TestClient


class TestRegistration:
    """Test user registration."""

    def test_registration_page_loads(self, client: TestClient):
        """Test registration page loads."""
        response = client.get("/auth/register")
        assert response.status_code == 200
