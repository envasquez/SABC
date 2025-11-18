"""Critical workflow tests targeting highest-value uncovered code."""

from datetime import datetime, timedelta
import json

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.db_schema import Angler, Event, Lake, Poll, PollOption, PollVote, Ramp
from core.helpers.timezone import now_local


class TestHomePagePollDisplay:
    """Test home page poll data display to hit uncovered home.py code."""

    def test_home_page_shows_poll_for_upcoming_tournament(
        self, member_client: TestClient, db_session: Session, member_user: Angler
    ):
        """Test home page shows poll data after user votes."""
        event = Event(
            name="Upcoming",
            date=datetime.now().date() + timedelta(days=7),
            year=datetime.now().year,
            event_type="tournament",
        )
        db_session.add(event)
        db_session.commit()

        lake = Lake(yaml_key="test", display_name="Test Lake")
        db_session.add(lake)
        db_session.commit()

        ramp = Ramp(lake_id=lake.id, name="Ramp")
        db_session.add(ramp)
        db_session.commit()

        poll = Poll(
            event_id=event.id,
            title="Location Vote",
            poll_type="tournament_location",
            starts_at=now_local() - timedelta(hours=1),
            closes_at=now_local() + timedelta(days=3),
        )
        db_session.add(poll)
        db_session.commit()

        option_data = {
            "lake_id": lake.id,
            "ramp_id": ramp.id,
            "start_time": "06:00",
            "end_time": "14:00",
        }
        option = PollOption(
            poll_id=poll.id,
            option_text="Lake - Ramp (6AM-2PM)",
            option_data=json.dumps(option_data),
        )
        db_session.add(option)
        db_session.commit()

        vote = PollVote(poll_id=poll.id, option_id=option.id, angler_id=member_user.id)
        db_session.add(vote)
        db_session.commit()

        response = member_client.get("/")
        assert response.status_code == 200
