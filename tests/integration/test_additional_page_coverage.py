"""Integration tests to increase coverage of various pages and routes.

Simple GET request tests to exercise code paths in low-coverage modules.
"""

from fastapi.testclient import TestClient


class TestPublicPages:
    """Test public-facing pages for better coverage."""

    def test_calendar_page_loads(self, client: TestClient):
        """Test that calendar page loads successfully."""
        response = client.get("/calendar")

        assert response.status_code == 200

    def test_roster_page_loads(self, client: TestClient):
        """Test that roster page loads successfully."""
        response = client.get("/roster")

        assert response.status_code == 200

    def test_awards_page_loads(self, client: TestClient):
        """Test that awards page loads successfully."""
        response = client.get("/awards")

        assert response.status_code == 200

    def test_awards_page_with_year(self, client: TestClient):
        """Test that awards page works with year parameter."""
        response = client.get("/awards?year=2024")

        assert response.status_code == 200

    def test_health_endpoint(self, client: TestClient):
        """Test that health check endpoint works."""
        response = client.get("/health")

        assert response.status_code == 200

    def test_metrics_endpoint(self, client: TestClient):
        """Test that metrics endpoint works."""
        response = client.get("/metrics")

        assert response.status_code in [200, 401, 403]  # May require auth

    def test_favicon_endpoint(self, client: TestClient):
        """Test that favicon endpoint works."""
        response = client.get("/favicon.ico")

        assert response.status_code in [200, 301, 302, 404]


class TestAdminPages:
    """Test admin pages for better coverage."""

    def test_admin_dashboard_loads(self, admin_client: TestClient):
        """Test that admin dashboard loads."""
        response = admin_client.get("/admin")

        assert response.status_code == 200

    def test_admin_events_page_loads(self, admin_client: TestClient):
        """Test that admin events page loads."""
        response = admin_client.get("/admin/events")

        assert response.status_code == 200

    def test_admin_lakes_page_loads(self, admin_client: TestClient):
        """Test that admin lakes page loads."""
        response = admin_client.get("/admin/lakes")

        assert response.status_code == 200

    def test_admin_users_page_loads(self, admin_client: TestClient):
        """Test that admin users page loads."""
        response = admin_client.get("/admin/users")

        assert response.status_code == 200

    def test_admin_tournaments_page_loads(self, admin_client: TestClient):
        """Test that admin tournaments list page loads."""
        response = admin_client.get("/admin/tournaments")

        assert response.status_code == 200


class TestAPIEndpoints:
    """Test API endpoints for coverage."""

    def test_lakes_api_endpoint(self, client: TestClient):
        """Test that lakes API endpoint works."""
        response = client.get("/api/lakes")

        assert response.status_code == 200
        # Should return JSON
        data = response.json()
        assert isinstance(data, (list, dict))
