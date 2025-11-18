"""Admin news management tests."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.db_schema import News
from tests.conftest import post_with_csrf


class TestAdminNews:
    """Test admin news management."""

    def test_admin_news_list(self, admin_client: TestClient):
        """Test admin can view news list."""
        response = admin_client.get("/admin/news")
        assert response.status_code == 200

    def test_admin_create_news(self, admin_client: TestClient, db_session: Session):
        """Test admin can create news."""
        response = post_with_csrf(
            admin_client,
            "/admin/news/create",
            data={
                "title": "Test News",
                "content": "Test content",
                "published": "true",
            },
        )
        assert response.status_code in [200, 303]

    def test_admin_edit_news(
        self, admin_client: TestClient, db_session: Session, admin_user
    ):
        """Test admin can edit news."""
        news = News(
            title="Original",
            content="Original content",
            author_id=admin_user.id,
            published=False,
        )
        db_session.add(news)
        db_session.commit()

        response = admin_client.get(f"/admin/news/{news.id}/edit")
        assert response.status_code == 200

    def test_admin_delete_news(
        self, admin_client: TestClient, db_session: Session, admin_user
    ):
        """Test admin can delete news."""
        news = News(
            title="Delete Me",
            content="Content",
            author_id=admin_user.id,
            published=False,
        )
        db_session.add(news)
        db_session.commit()

        response = post_with_csrf(
            admin_client,
            f"/admin/news/{news.id}/delete",
            data={},
        )
        assert response.status_code in [200, 303]
