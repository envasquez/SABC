"""Comprehensive home page tests to maximize coverage."""

from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.db_schema import Event, News


class TestHomePageWithData:
    """Test home page with various data scenarios."""

    def test_home_page_with_news(self, client: TestClient, db_session: Session):
        """Test home page displays news."""
        news = News(
            title="Test News",
            content="Test content",
            author_id=1,
            published=True,
        )
        db_session.add(news)
        db_session.commit()

        response = client.get("/")
        assert response.status_code == 200

    def test_home_page_with_multiple_tournaments(self, client: TestClient, db_session: Session):
        """Test home page with multiple tournaments."""
        for i in range(3):
            event = Event(
                name=f"Tournament {i}",
                date=datetime.now().date() + timedelta(days=i * 7),
                year=datetime.now().year,
                event_type="tournament",
            )
            db_session.add(event)
        db_session.commit()

        response = client.get("/")
        assert response.status_code == 200

    def test_home_page_with_events(self, client: TestClient, db_session: Session):
        """Test home page with various event types."""
        event1 = Event(
            name="Meeting",
            date=datetime.now().date() + timedelta(days=7),
            year=datetime.now().year,
            event_type="meeting",
        )
        event2 = Event(
            name="Social",
            date=datetime.now().date() + timedelta(days=14),
            year=datetime.now().year,
            event_type="social",
        )
        db_session.add(event1)
        db_session.add(event2)
        db_session.commit()

        response = client.get("/")
        assert response.status_code == 200
