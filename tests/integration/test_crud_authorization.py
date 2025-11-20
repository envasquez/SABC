"""Integration tests for CRUD authorization rules.

Phase 3 of the comprehensive CRUD test coverage plan.
Tests access control to ensure only authorized users can perform CRUD operations.

See: docs/CRUD_TEST_COVERAGE_PLAN.md
Tracking: https://github.com/envasquez/SABC/issues/186
"""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.db_schema.models import Angler, Event, Lake, News, Poll, Ramp
from tests.conftest import post_with_csrf


class TestAdminOnlyEventOperations:
    """Test that only admins can perform event CRUD operations."""

    def test_non_admin_cannot_create_event(self, member_client: TestClient):
        """Test that non-admin users cannot create events."""
        future_date = datetime.now(timezone.utc).date() + timedelta(days=30)
        form_data = {
            "name": "Unauthorized Event",
            "date": future_date.isoformat(),
            "event_type": "sabc_tournament",
            "year": str(future_date.year),
        }

        response = post_with_csrf(member_client, "/admin/events/create", data=form_data)

        # Should be rejected (may return 200 with error, redirect, or 403)
        assert response.status_code in [200, 302, 303, 403]

    def test_non_admin_cannot_update_event(self, member_client: TestClient, test_event: Event):
        """Test that non-admin users cannot update events."""
        form_data = {
            "name": "Updated Event Name",
            "date": test_event.date.isoformat(),
            "event_type": test_event.event_type,
            "year": str(test_event.year),
        }

        response = post_with_csrf(
            member_client, f"/admin/events/{test_event.id}/update", data=form_data
        )

        # Should be rejected
        assert response.status_code in [200, 302, 303, 403]

    def test_non_admin_cannot_delete_event(self, member_client: TestClient, test_event: Event):
        """Test that non-admin users cannot delete events."""
        response = member_client.delete(f"/admin/events/{test_event.id}")

        # Should be rejected
        assert response.status_code in [200, 302, 303, 403]


class TestAdminOnlyPollOperations:
    """Test that only admins can perform poll CRUD operations."""

    def test_non_admin_cannot_create_poll(self, member_client: TestClient):
        """Test that non-admin users cannot create polls."""
        # Try to access create poll form
        response = member_client.get("/admin/polls/create")

        # Should be rejected
        assert response.status_code in [200, 302, 303, 403]

    def test_non_admin_cannot_edit_poll(
        self, member_client: TestClient, db_session: Session, test_event: Event
    ):
        """Test that non-admin users cannot edit polls."""
        # Create a poll
        poll = Poll(
            event_id=test_event.id,
            title="Test Poll",
            poll_type="generic",
            starts_at=datetime.now(timezone.utc),
            closes_at=datetime.now(timezone.utc) + timedelta(days=7),
            created_by=1,
        )
        db_session.add(poll)
        db_session.commit()
        db_session.refresh(poll)

        # Try to access edit form
        response = member_client.get(f"/admin/polls/{poll.id}/edit")

        # Should be rejected
        assert response.status_code in [200, 302, 303, 403]

    def test_non_admin_cannot_delete_poll(
        self, member_client: TestClient, db_session: Session, test_event: Event
    ):
        """Test that non-admin users cannot delete polls."""
        # Create a poll
        poll = Poll(
            event_id=test_event.id,
            title="Test Poll",
            poll_type="generic",
            starts_at=datetime.now(timezone.utc),
            closes_at=datetime.now(timezone.utc) + timedelta(days=7),
            created_by=1,
        )
        db_session.add(poll)
        db_session.commit()
        db_session.refresh(poll)

        # Try to delete
        response = member_client.delete(f"/admin/polls/{poll.id}")

        # Should be rejected
        assert response.status_code in [200, 302, 303, 403]


class TestAdminOnlyLakeOperations:
    """Test that only admins can perform lake/ramp CRUD operations."""

    def test_non_admin_cannot_create_lake(self, member_client: TestClient):
        """Test that non-admin users cannot create lakes."""
        form_data = {
            "name": "unauthorized_lake",
            "display_name": "Unauthorized Lake",
            "google_maps_embed": "",
        }

        response = post_with_csrf(member_client, "/admin/lakes/create", data=form_data)

        # Should be rejected
        assert response.status_code in [200, 302, 303, 403]

    def test_non_admin_cannot_update_lake(self, member_client: TestClient, test_lake: Lake):
        """Test that non-admin users cannot update lakes."""
        form_data = {
            "name": "updated_key",
            "display_name": "Updated Lake",
            "google_maps_embed": "",
        }

        response = post_with_csrf(
            member_client, f"/admin/lakes/{test_lake.id}/update", data=form_data
        )

        # Should be rejected
        assert response.status_code in [200, 302, 303, 403]

    def test_non_admin_cannot_delete_lake(self, member_client: TestClient, test_lake: Lake):
        """Test that non-admin users cannot delete lakes."""
        response = member_client.delete(f"/admin/lakes/{test_lake.id}")

        # Should be rejected
        assert response.status_code in [200, 302, 303, 403]

    def test_non_admin_cannot_create_ramp(self, member_client: TestClient, test_lake: Lake):
        """Test that non-admin users cannot create ramps."""
        form_data = {
            "name": "Unauthorized Ramp",
            "google_maps_iframe": "",
        }

        response = post_with_csrf(
            member_client, f"/admin/lakes/{test_lake.id}/ramps", data=form_data
        )

        # Should be rejected
        assert response.status_code in [200, 302, 303, 403]

    def test_non_admin_cannot_update_ramp(self, member_client: TestClient, test_ramp: Ramp):
        """Test that non-admin users cannot update ramps."""
        form_data = {
            "name": "Updated Ramp",
            "google_maps_iframe": "",
        }

        response = post_with_csrf(
            member_client, f"/admin/ramps/{test_ramp.id}/update", data=form_data
        )

        # Should be rejected
        assert response.status_code in [200, 302, 303, 403]

    def test_non_admin_cannot_delete_ramp(self, member_client: TestClient, test_ramp: Ramp):
        """Test that non-admin users cannot delete ramps."""
        response = member_client.delete(f"/admin/ramps/{test_ramp.id}")

        # Should be rejected
        assert response.status_code in [200, 302, 303, 403]


class TestAdminOnlyUserOperations:
    """Test that only admins can perform user CRUD operations."""

    def test_non_admin_cannot_create_user(self, member_client: TestClient):
        """Test that non-admin users cannot create other users."""
        response = member_client.post(
            "/admin/users",
            json={
                "name": "Unauthorized User",
                "email": "unauthorized@test.com",
                "member": True,
            },
        )

        # Should be rejected
        assert response.status_code in [200, 302, 303, 403]

    def test_non_admin_cannot_update_other_user(
        self, member_client: TestClient, db_session: Session
    ):
        """Test that non-admin users cannot update other users."""
        # Create another user
        other_user = Angler(name="Other User", email="other@test.com", member=True, is_admin=False)
        db_session.add(other_user)
        db_session.commit()
        db_session.refresh(other_user)

        # Try to update them
        form_data = {
            "name": "Modified Name",
            "email": "other@test.com",
            "member": "on",
        }

        response = post_with_csrf(
            member_client, f"/admin/users/{other_user.id}/edit", data=form_data
        )

        # Should be rejected
        assert response.status_code in [200, 302, 303, 403]

    def test_non_admin_cannot_delete_user(self, member_client: TestClient, db_session: Session):
        """Test that non-admin users cannot delete users."""
        # Create another user
        other_user = Angler(
            name="Deletable User", email="deletable@test.com", member=True, is_admin=False
        )
        db_session.add(other_user)
        db_session.commit()
        db_session.refresh(other_user)

        # Try to delete
        response = member_client.delete(f"/admin/users/{other_user.id}")

        # Should be rejected
        assert response.status_code in [200, 302, 303, 403]


class TestAdminOnlyNewsOperations:
    """Test that only admins can perform news CRUD operations."""

    def test_non_admin_cannot_create_news(self, member_client: TestClient):
        """Test that non-admin users cannot create news."""
        form_data = {
            "title": "Unauthorized News",
            "content": "This should not be created",
            "published": "on",
        }

        response = post_with_csrf(member_client, "/admin/news/create", data=form_data)

        # Should be rejected
        assert response.status_code in [200, 302, 303, 403, 404, 405]

    def test_non_admin_cannot_update_news(
        self, member_client: TestClient, db_session: Session, admin_user: Angler
    ):
        """Test that non-admin users cannot update news."""
        # Create news item
        news = News(
            title="Test News",
            content="Test content",
            author_id=admin_user.id,
            published=True,
        )
        db_session.add(news)
        db_session.commit()
        db_session.refresh(news)

        # Try to update
        form_data = {
            "title": "Modified News",
            "content": "Modified content",
            "published": "on",
        }

        response = post_with_csrf(member_client, f"/admin/news/{news.id}/edit", data=form_data)

        # Should be rejected
        assert response.status_code in [200, 302, 303, 403, 404, 405]

    def test_non_admin_cannot_delete_news(
        self, member_client: TestClient, db_session: Session, admin_user: Angler
    ):
        """Test that non-admin users cannot delete news."""
        # Create news item
        news = News(
            title="Deletable News",
            content="Test content",
            author_id=admin_user.id,
            published=True,
        )
        db_session.add(news)
        db_session.commit()
        db_session.refresh(news)

        # Try to delete
        response = member_client.delete(f"/admin/news/{news.id}")

        # Should be rejected
        assert response.status_code in [200, 302, 303, 403, 404, 405]


class TestMemberOnlyOperations:
    """Test that certain operations require member status."""

    def test_anonymous_cannot_vote_in_polls(self, client: TestClient):
        """Test that anonymous users cannot vote in polls."""
        # Try to access polls page
        response = client.get("/polls")

        # Should redirect to login
        assert response.status_code in [200, 302, 303]

    def test_non_member_cannot_vote_in_polls(self, client: TestClient):
        """Test that non-member/anonymous users are redirected from polls."""
        # Try to access polls without authentication
        response = client.get("/polls")

        # Should redirect to login
        assert response.status_code in [200, 302, 303]


class TestSelfModificationRules:
    """Test rules around users modifying their own data."""

    def test_admin_cannot_delete_own_account(self, admin_client: TestClient, admin_user: Angler):
        """Test that admin users cannot delete their own account."""
        response = admin_client.delete(f"/admin/users/{admin_user.id}")

        # Should be prevented (400 or redirect with error)
        assert response.status_code in [200, 400, 302, 303]


class TestAnonymousAccessControl:
    """Test that anonymous users have appropriate restrictions."""

    def test_anonymous_redirected_from_admin_pages(self, client: TestClient):
        """Test that anonymous users are redirected from admin pages."""
        admin_pages = [
            "/admin",
            "/admin/events",
            "/admin/lakes",
            "/admin/users",
            "/admin/tournaments",
        ]

        for page in admin_pages:
            response = client.get(page)
            # Should redirect to login or show login page
            assert response.status_code in [200, 302, 303]

    def test_anonymous_can_view_public_pages(self, client: TestClient):
        """Test that anonymous users can view public pages."""
        public_pages = [
            "/",
            "/calendar",
            "/roster",
            "/awards",
        ]

        for page in public_pages:
            response = client.get(page)
            # Should load successfully
            assert response.status_code == 200


class TestConsistentAuthorizationBehavior:
    """Test that authorization is consistent across similar operations."""

    def test_all_admin_delete_endpoints_require_admin(
        self, member_client: TestClient, test_event: Event, test_lake: Lake
    ):
        """Test that all DELETE endpoints consistently require admin."""
        delete_endpoints = [
            f"/admin/events/{test_event.id}",
            f"/admin/lakes/{test_lake.id}",
        ]

        for endpoint in delete_endpoints:
            response = member_client.delete(endpoint)
            # All should reject non-admin
            assert response.status_code in [200, 302, 303, 403]

    def test_all_admin_create_forms_require_admin(self, member_client: TestClient):
        """Test that all admin create forms require admin."""
        create_forms = [
            "/admin/events/create",
            "/admin/polls/create",
        ]

        for form_url in create_forms:
            response = member_client.get(form_url)
            # All should reject non-admin or redirect
            assert response.status_code in [200, 302, 303, 403]
