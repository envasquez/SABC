"""Load testing scenarios for SABC application using Locust.

Run with: locust -f tests/load/locustfile.py --host=http://localhost:8000
Web UI: http://localhost:8089
"""

from locust import HttpUser, between, task


class BrowsingUser(HttpUser):
    """Simulates a typical user browsing the public site."""

    wait_time = between(2, 5)  # Wait 2-5 seconds between tasks

    @task(3)
    def view_homepage(self):
        """View homepage (most common action)."""
        self.client.get("/")

    @task(2)
    def view_calendar(self):
        """View calendar page."""
        self.client.get("/calendar")

    @task(2)
    def view_awards(self):
        """View awards/standings page."""
        self.client.get("/awards")

    @task(1)
    def view_health(self):
        """Check health endpoint."""
        self.client.get("/health")


class AuthenticatedUser(HttpUser):
    """Simulates authenticated member browsing and voting."""

    wait_time = between(3, 8)

    def on_start(self):
        """Login before starting tasks."""
        # Note: This requires a test user in the database
        response = self.client.post(
            "/login",
            data={
                "email": "loadtest@example.com",
                "password": "LoadTest123!",
            },
        )
        if response.status_code != 302:
            print(f"Login failed with status {response.status_code}")

    @task(3)
    def view_homepage(self):
        """View homepage."""
        self.client.get("/")

    @task(2)
    def view_polls(self):
        """View voting page."""
        self.client.get("/polls")

    @task(1)
    def view_profile(self):
        """View profile page."""
        self.client.get("/profile")

    @task(1)
    def view_calendar(self):
        """View calendar."""
        self.client.get("/calendar")


class AdminUser(HttpUser):
    """Simulates admin user performing management tasks."""

    wait_time = between(5, 10)

    def on_start(self):
        """Login as admin before starting tasks."""
        # Note: This requires a test admin user in the database
        response = self.client.post(
            "/login",
            data={
                "email": "admin@example.com",
                "password": "Admin123!",
            },
        )
        if response.status_code != 302:
            print(f"Admin login failed with status {response.status_code}")

    @task(2)
    def view_admin_dashboard(self):
        """View admin dashboard."""
        self.client.get("/admin")

    @task(1)
    def view_admin_events(self):
        """View events management."""
        self.client.get("/admin/events")

    @task(1)
    def view_admin_users(self):
        """View user management."""
        self.client.get("/admin/users")


class MixedWorkload(HttpUser):
    """Simulates realistic mix of user types and behaviors."""

    wait_time = between(1, 5)

    # Mix of tasks weighted by realistic usage patterns
    @task(10)
    def browse_public_pages(self):
        """Browse public pages (most common)."""
        pages = ["/", "/calendar", "/awards"]
        for page in pages:
            self.client.get(page)

    @task(3)
    def view_specific_content(self):
        """View specific tournament or event pages."""
        # Note: Requires valid IDs in database
        self.client.get("/calendar")  # Safe fallback

    @task(1)
    def check_health(self):
        """Health check."""
        self.client.get("/health")
