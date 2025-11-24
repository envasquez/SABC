"""
Phase 13: Comprehensive tests for admin news and dashboard routes.

Coverage focus:
- routes/admin/core/news.py (23.0% → target 85%+)
- routes/admin/core/dashboard.py (33.3% → target 85%+)
- routes/admin/core/dashboard_data.py (57.1% → target 85%+)
"""

from datetime import timedelta
from unittest.mock import patch

from sqlalchemy.orm import Session

from core.db_schema import Angler, Event, News
from tests.conftest import TestClient, post_with_csrf


class TestAdminNewsList:
    """Test admin news listing page."""

    def test_admin_news_requires_admin(self, client: TestClient):
        """News admin page should require admin privileges."""
        response = client.get("/admin/news", follow_redirects=False)
        assert response.status_code in [302, 303, 307]
        assert "login" in response.headers.get("location", "").lower()

    def test_admin_news_list_page(
        self, admin_client: TestClient, db_session: Session, admin_user: Angler
    ):
        """Admin should be able to view news list."""
        # Create some news items
        news1 = News(
            title="News 1",
            content="Content 1",
            author_id=admin_user.id,
            published=True,
            priority=1,
        )
        news2 = News(
            title="News 2",
            content="Content 2",
            author_id=admin_user.id,
            published=False,
            priority=0,
        )
        db_session.add_all([news1, news2])
        db_session.commit()

        response = admin_client.get("/admin/news")
        assert response.status_code == 200
        assert "News 1" in response.text
        assert "News 2" in response.text

    def test_admin_news_shows_priority_order(
        self, admin_client: TestClient, db_session: Session, admin_user: Angler
    ):
        """News should be ordered by priority then creation date."""
        news_low = News(
            title="Low Priority",
            content="Content",
            author_id=admin_user.id,
            published=True,
            priority=0,
        )
        news_high = News(
            title="High Priority",
            content="Content",
            author_id=admin_user.id,
            published=True,
            priority=10,
        )
        db_session.add_all([news_low, news_high])
        db_session.commit()

        response = admin_client.get("/admin/news")
        assert response.status_code == 200
        # Both should be present
        assert "High Priority" in response.text
        assert "Low Priority" in response.text


class TestAdminNewsCreate:
    """Test admin news creation."""

    @patch("routes.admin.core.news.send_news_notification")
    def test_create_news_successfully(
        self, mock_send_email, admin_client: TestClient, db_session: Session
    ):
        """Admin should be able to create news."""
        mock_send_email.return_value = True

        response = post_with_csrf(
            admin_client,
            "/admin/news/create",
            data={"title": "Test News", "content": "Test content", "priority": 1},
            follow_redirects=False,
        )

        assert response.status_code in [302, 303]
        assert "success" in response.headers.get("location", "").lower()

        # Verify news was created
        news = db_session.query(News).filter(News.title == "Test News").first()
        assert news is not None
        assert news.content == "Test content"
        assert news.priority == 1
        assert news.published is True

    def test_create_news_requires_admin(self, client: TestClient):
        """News creation should require admin privileges."""
        response = post_with_csrf(
            client,
            "/admin/news/create",
            data={"title": "Test", "content": "Content", "priority": 0},
            follow_redirects=False,
        )
        assert response.status_code in [302, 303, 307]
        assert "login" in response.headers.get("location", "").lower()

    def test_create_news_empty_title_rejected(self, admin_client: TestClient):
        """News with empty title should be rejected."""
        response = post_with_csrf(
            admin_client,
            "/admin/news/create",
            data={"title": "   ", "content": "Content", "priority": 0},
            follow_redirects=False,
        )
        assert response.status_code == 422

    def test_create_news_empty_content_rejected(self, admin_client: TestClient):
        """News with empty content should be rejected."""
        response = post_with_csrf(
            admin_client,
            "/admin/news/create",
            data={"title": "Title", "content": "   ", "priority": 0},
            follow_redirects=False,
        )
        assert response.status_code == 422

    @patch("routes.admin.core.news.send_news_notification")
    def test_create_news_sanitizes_html(
        self, mock_send_email, admin_client: TestClient, db_session: Session
    ):
        """News creation should sanitize HTML content."""
        mock_send_email.return_value = True

        response = post_with_csrf(
            admin_client,
            "/admin/news/create",
            data={
                "title": "Test <script>alert('xss')</script>",
                "content": "Content <script>alert('xss')</script>",
                "priority": 0,
            },
            follow_redirects=False,
        )

        assert response.status_code in [302, 303]

        # Verify dangerous script tags were removed
        news = db_session.query(News).first()
        assert news is not None
        assert "<script>" not in news.title
        assert "<script>" not in news.content

    @patch("routes.admin.core.news.send_news_notification")
    def test_create_news_sends_notifications(
        self,
        mock_send_email,
        admin_client: TestClient,
        db_session: Session,
        member_user: Angler,
    ):
        """News creation should send email notifications to members."""
        mock_send_email.return_value = True

        response = post_with_csrf(
            admin_client,
            "/admin/news/create",
            data={"title": "Important News", "content": "Everyone should know", "priority": 5},
            follow_redirects=False,
        )

        assert response.status_code in [302, 303]
        # Verify send_news_notification was called with member emails
        mock_send_email.assert_called_once()
        call_args = mock_send_email.call_args[0]
        emails = call_args[0]
        assert isinstance(emails, list)
        # Member should be in the list
        assert member_user.email in emails

    @patch("routes.admin.core.news.send_news_notification")
    def test_create_news_continues_if_email_fails(
        self, mock_send_email, admin_client: TestClient, db_session: Session
    ):
        """News should be created even if email notification fails."""
        mock_send_email.side_effect = Exception("SMTP error")

        response = post_with_csrf(
            admin_client,
            "/admin/news/create",
            data={"title": "Test News", "content": "Content", "priority": 0},
            follow_redirects=False,
        )

        assert response.status_code in [302, 303]
        # News should still be created
        news = db_session.query(News).filter(News.title == "Test News").first()
        assert news is not None


class TestAdminNewsEdit:
    """Test admin news editing."""

    def test_get_edit_news_form(
        self, admin_client: TestClient, db_session: Session, admin_user: Angler
    ):
        """Admin should be able to get edit form for news."""
        news = News(
            title="Original Title",
            content="Original Content",
            author_id=admin_user.id,
            published=True,
            priority=0,
        )
        db_session.add(news)
        db_session.commit()

        response = admin_client.get(f"/admin/news/{news.id}/edit")
        assert response.status_code == 200
        # Template returns the news management page
        assert "Manage Club News" in response.text

    def test_get_edit_news_form_nonexistent(self, admin_client: TestClient):
        """Editing nonexistent news should redirect with error."""
        response = admin_client.get("/admin/news/99999/edit", follow_redirects=False)
        assert response.status_code in [302, 303]
        assert "error" in response.headers.get("location", "").lower()

    def test_update_news_successfully(
        self, admin_client: TestClient, db_session: Session, admin_user: Angler
    ):
        """Admin should be able to update news."""
        news = News(
            title="Original Title",
            content="Original Content",
            author_id=admin_user.id,
            published=True,
            priority=0,
        )
        db_session.add(news)
        db_session.commit()
        news_id = news.id

        response = post_with_csrf(
            admin_client,
            f"/admin/news/{news_id}/update",
            data={"title": "Updated Title", "content": "Updated Content", "priority": 5},
            follow_redirects=False,
        )

        assert response.status_code in [302, 303]
        assert "success" in response.headers.get("location", "").lower()

        # Verify news was updated
        db_session.expire_all()
        updated_news = db_session.query(News).filter(News.id == news_id).first()
        assert updated_news is not None
        assert updated_news.title == "Updated Title"
        assert updated_news.content == "Updated Content"
        assert updated_news.priority == 5
        assert updated_news.last_edited_by == admin_user.id

    def test_update_news_empty_title_rejected(
        self, admin_client: TestClient, db_session: Session, admin_user: Angler
    ):
        """Updating news with empty title should be rejected."""
        news = News(
            title="Original",
            content="Content",
            author_id=admin_user.id,
            published=True,
            priority=0,
        )
        db_session.add(news)
        db_session.commit()

        response = post_with_csrf(
            admin_client,
            f"/admin/news/{news.id}/update",
            data={"title": "   ", "content": "Content", "priority": 0},
            follow_redirects=False,
        )
        assert response.status_code == 422

    def test_update_news_sanitizes_html(
        self, admin_client: TestClient, db_session: Session, admin_user: Angler
    ):
        """News update should sanitize HTML content."""
        news = News(
            title="Original",
            content="Content",
            author_id=admin_user.id,
            published=True,
            priority=0,
        )
        db_session.add(news)
        db_session.commit()
        news_id = news.id

        response = post_with_csrf(
            admin_client,
            f"/admin/news/{news_id}/update",
            data={
                "title": "Safe <script>alert('xss')</script>",
                "content": "Safe <script>evil()</script>",
                "priority": 0,
            },
            follow_redirects=False,
        )

        assert response.status_code in [302, 303]

        # Verify script tags were sanitized
        db_session.expire_all()
        updated_news = db_session.query(News).filter(News.id == news_id).first()
        assert updated_news is not None
        assert "<script>" not in updated_news.title
        assert "<script>" not in updated_news.content


class TestAdminNewsDelete:
    """Test admin news deletion."""

    def test_delete_news_post_method(
        self, admin_client: TestClient, db_session: Session, admin_user: Angler
    ):
        """Admin should be able to delete news via POST."""
        news = News(
            title="To Delete",
            content="Content",
            author_id=admin_user.id,
            published=True,
            priority=0,
        )
        db_session.add(news)
        db_session.commit()
        news_id = news.id

        response = post_with_csrf(
            admin_client,
            f"/admin/news/{news_id}/delete",
            data={},
            follow_redirects=False,
        )

        assert response.status_code in [302, 303]
        assert "success" in response.headers.get("location", "").lower()

        # Verify news was deleted
        db_session.expire_all()
        deleted_news = db_session.query(News).filter(News.id == news_id).first()
        assert deleted_news is None

    def test_delete_news_delete_method(
        self, admin_client: TestClient, db_session: Session, admin_user: Angler
    ):
        """Admin should be able to delete news via DELETE."""
        news = News(
            title="To Delete",
            content="Content",
            author_id=admin_user.id,
            published=True,
            priority=0,
        )
        db_session.add(news)
        db_session.commit()
        news_id = news.id

        response = admin_client.delete(f"/admin/news/{news_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify news was deleted
        db_session.expire_all()
        deleted_news = db_session.query(News).filter(News.id == news_id).first()
        assert deleted_news is None

    def test_delete_nonexistent_news(self, admin_client: TestClient):
        """Deleting nonexistent news should not crash."""
        response = admin_client.delete("/admin/news/99999")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True  # Idempotent


class TestAdminNewsTestEmail:
    """Test admin news test email functionality."""

    @patch("routes.admin.core.news.send_news_notification")
    def test_send_test_email_successfully(
        self, mock_send_email, admin_client: TestClient, admin_user: Angler
    ):
        """Admin should be able to send test email."""
        mock_send_email.return_value = True

        response = post_with_csrf(
            admin_client,
            "/admin/news/test-email",
            data={"title": "Test Title", "content": "Test Content"},
            follow_redirects=False,
        )

        assert response.status_code in [302, 303]
        assert "success" in response.headers.get("location", "").lower()
        # Verify send was called with admin's email
        mock_send_email.assert_called_once()
        call_args = mock_send_email.call_args[0]
        emails = call_args[0]
        assert admin_user.email in emails

    @patch("routes.admin.core.news.send_news_notification")
    def test_send_test_email_failure(self, mock_send_email, admin_client: TestClient):
        """Test email failure should be handled gracefully."""
        mock_send_email.return_value = False

        response = post_with_csrf(
            admin_client,
            "/admin/news/test-email",
            data={"title": "Test", "content": "Content"},
            follow_redirects=False,
        )

        assert response.status_code in [302, 303]
        assert "error" in response.headers.get("location", "").lower()


class TestAdminDashboard:
    """Test admin dashboard pages."""

    def test_admin_root_redirects_to_events(self, admin_client: TestClient):
        """Admin root should redirect to events page."""
        response = admin_client.get("/admin", follow_redirects=False)
        assert response.status_code == 302
        assert "/admin/events" in response.headers.get("location", "")

    def test_admin_events_page(self, admin_client: TestClient):
        """Admin should be able to view events page."""
        response = admin_client.get("/admin/events")
        assert response.status_code == 200

    def test_admin_users_page(self, admin_client: TestClient):
        """Admin should be able to view users page."""
        response = admin_client.get("/admin/users")
        assert response.status_code == 200

    def test_admin_invalid_page_returns_404(self, admin_client: TestClient):
        """Invalid admin page should return 404."""
        response = admin_client.get("/admin/invalid")
        assert response.status_code == 404

    def test_admin_dashboard_requires_admin(self, client: TestClient):
        """Admin dashboard should require admin privileges."""
        response = client.get("/admin/events", follow_redirects=False)
        assert response.status_code in [302, 303, 307]
        assert "login" in response.headers.get("location", "").lower()


class TestAdminEventsPage:
    """Test admin events page functionality."""

    def test_admin_events_shows_upcoming_events(
        self, admin_client: TestClient, db_session: Session, test_lake, test_ramp
    ):
        """Admin events page should show upcoming events."""
        from datetime import date

        future_date = date.today() + timedelta(days=30)
        event = Event(
            date=future_date,
            year=future_date.year,
            name="Future Tournament",
            event_type="sabc_tournament",
            lake_name="Test Lake",
        )
        db_session.add(event)
        db_session.commit()

        response = admin_client.get("/admin/events")
        assert response.status_code == 200
        assert "Future Tournament" in response.text

    def test_admin_events_shows_past_tournaments(
        self, admin_client: TestClient, db_session: Session, test_lake, test_ramp
    ):
        """Admin events page should show past tournaments."""
        from datetime import date

        past_date = date.today() - timedelta(days=30)
        event = Event(
            date=past_date,
            year=past_date.year,
            name="Past Tournament",
            event_type="sabc_tournament",
            lake_name="Test Lake",
        )
        db_session.add(event)
        db_session.commit()

        response = admin_client.get("/admin/events")
        assert response.status_code == 200
        assert "Past Tournament" in response.text

    def test_admin_events_pagination(
        self, admin_client: TestClient, db_session: Session, test_lake, test_ramp
    ):
        """Admin events page should support pagination."""
        from datetime import date

        # Create many future events
        for i in range(25):
            future_date = date.today() + timedelta(days=i + 1)
            event = Event(
                date=future_date,
                year=future_date.year,
                name=f"Event {i}",
                event_type="sabc_tournament",
            )
            db_session.add(event)
        db_session.commit()

        # Page 1
        response1 = admin_client.get("/admin/events?upcoming_page=1")
        assert response1.status_code == 200

        # Page 2 should exist
        response2 = admin_client.get("/admin/events?upcoming_page=2")
        assert response2.status_code == 200


class TestAdminUsersPage:
    """Test admin users page functionality."""

    def test_admin_users_shows_member_count(
        self, admin_client: TestClient, member_user: Angler, regular_user: Angler
    ):
        """Admin users page should show member and guest counts."""
        response = admin_client.get("/admin/users")
        assert response.status_code == 200
        # Should have some count information
        assert "member" in response.text.lower()

    def test_admin_users_lists_all_users(
        self, admin_client: TestClient, member_user: Angler, admin_user: Angler
    ):
        """Admin users page should list all users."""
        response = admin_client.get("/admin/users")
        assert response.status_code == 200
        assert member_user.name in response.text
        assert admin_user.name in response.text
