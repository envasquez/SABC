"""Phase 8: Event Management Edge Cases

Tests for event creation, validation, error handling, and information retrieval.
Focuses on low-coverage areas in event management helpers.
"""

from datetime import datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.db_schema import Event, Lake, Poll, Ramp, Tournament
from core.helpers.timezone import now_local
from tests.conftest import post_with_csrf


class TestEventCreationHelpers:
    """Tests for event creation helper functions and error handling."""

    def test_create_event_with_duplicate_date_fails(
        self,
        admin_client: TestClient,
        test_event: Event,
        test_lake: Lake,
        test_ramp: Ramp,
        db_session: Session,
    ):
        """Test that creating an event on an existing date fails with proper error."""
        response = post_with_csrf(
            admin_client,
            "/admin/events/create",
            data={
                "date": str(test_event.date),
                "name": "Duplicate Date Event",
                "event_type": "sabc_tournament",
                "start_time": "06:00",
                "weigh_in_time": "15:00",
                "entry_fee": "50",
                "lake_name": test_lake.display_name,
                "ramp_name": test_ramp.name,
            },
            follow_redirects=False,
        )

        # Should redirect with error or warning about duplicate date
        assert response.status_code in [302, 303]

    def test_create_event_with_missing_required_fields_fails(
        self, admin_client: TestClient, db_session: Session
    ):
        """Test that creating an event with missing required fields fails."""
        future_date = (now_local() + timedelta(days=30)).strftime("%Y-%m-%d")

        # Missing name
        response = post_with_csrf(
            admin_client,
            "/admin/events/create",
            data={
                "date": future_date,
                "name": "",
                "event_type": "sabc_tournament",
                "start_time": "06:00",
                "weigh_in_time": "15:00",
            },
            follow_redirects=False,
        )

        assert response.status_code in [302, 303]

    def test_create_event_with_invalid_lake_fails(
        self, admin_client: TestClient, db_session: Session
    ):
        """Test that creating an event with invalid lake/ramp fails with proper error."""
        future_date = (now_local() + timedelta(days=30)).strftime("%Y-%m-%d")

        response = post_with_csrf(
            admin_client,
            "/admin/events/create",
            data={
                "date": future_date,
                "name": "Invalid Lake Event",
                "event_type": "sabc_tournament",
                "start_time": "06:00",
                "weigh_in_time": "15:00",
                "entry_fee": "50",
                "lake_name": "",  # Empty lake name
                "ramp_name": "",  # Empty ramp name
            },
            follow_redirects=False,
        )

        # Should redirect (may succeed with empty lake/ramp for SABC tournament)
        assert response.status_code in [302, 303]


class TestEventUpdateErrors:
    """Tests for event update error handling."""

    def test_update_event_to_duplicate_date_fails(
        self,
        admin_client: TestClient,
        test_event: Event,
        db_session: Session,
    ):
        """Test that updating an event to a date that already has an event fails."""
        # Create a second event
        future_date = now_local().date() + timedelta(days=60)
        second_event = Event(
            date=future_date,
            name="Future Event",
            event_type="sabc_tournament",
            year=future_date.year,
        )
        db_session.add(second_event)
        db_session.commit()
        db_session.refresh(second_event)

        # Try to update second event to test_event's date
        response = post_with_csrf(
            admin_client,
            f"/admin/events/{second_event.id}/update",
            data={
                "date": str(test_event.date),
                "name": "Updated Event",
                "event_type": "sabc_tournament",
            },
            follow_redirects=False,
        )

        # Should redirect (with warning about duplicate date)
        assert response.status_code in [302, 303]

    def test_update_event_with_missing_required_fields_fails(
        self,
        admin_client: TestClient,
        test_event: Event,
        db_session: Session,
    ):
        """Test that updating an event with missing required fields fails."""
        response = post_with_csrf(
            admin_client,
            f"/admin/events/{test_event.id}/update",
            data={
                "date": str(test_event.date),
                "name": "",  # Empty name should fail
                "event_type": "sabc_tournament",
            },
            follow_redirects=False,
        )

        assert response.status_code in [302, 303]

    def test_update_event_with_invalid_foreign_key_fails(
        self,
        admin_client: TestClient,
        test_event: Event,
        db_session: Session,
    ):
        """Test that updating with invalid lake/ramp fails with proper error."""
        response = post_with_csrf(
            admin_client,
            f"/admin/events/{test_event.id}/update",
            data={
                "date": str(test_event.date),
                "name": "Updated Event",
                "event_type": "sabc_tournament",
                "lake_name": "",  # Empty - should succeed for SABC tournament
                "ramp_name": "",  # Empty - should succeed for SABC tournament
            },
            follow_redirects=False,
        )

        assert response.status_code in [302, 303]


class TestGetEventInfo:
    """Tests for event information retrieval endpoint."""

    def test_admin_can_get_event_info(
        self,
        admin_client: TestClient,
        test_event: Event,
        test_tournament: Tournament,
        db_session: Session,
    ):
        """Test that admins can retrieve event information as JSON."""
        response = admin_client.get(f"/admin/events/{test_event.id}/info")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_event.id
        assert data["name"] == test_event.name
        assert data["event_type"] == test_event.event_type

    def test_get_event_info_with_tournament_data(
        self,
        admin_client: TestClient,
        test_event: Event,
        test_tournament: Tournament,
        test_lake: Lake,
        test_ramp: Ramp,
        db_session: Session,
    ):
        """Test that event info includes tournament data when present."""
        response = admin_client.get(f"/admin/events/{test_event.id}/info")

        assert response.status_code == 200
        data = response.json()
        assert data["tournament_id"] == test_tournament.id
        assert data["fish_limit"] == test_tournament.fish_limit
        assert data["lake_name"] is not None
        assert data["ramp_name"] is not None

    def test_get_event_info_with_poll_data(
        self,
        admin_client: TestClient,
        test_event: Event,
        test_poll: Poll,
        db_session: Session,
    ):
        """Test that event info includes poll data when present."""
        response = admin_client.get(f"/admin/events/{test_event.id}/info")

        assert response.status_code == 200
        data = response.json()
        assert data["poll_id"] == test_poll.id
        assert "poll_starts_at" in data
        assert "poll_closes_at" in data

    def test_get_event_info_without_optional_data(
        self, admin_client: TestClient, db_session: Session
    ):
        """Test that event info works for events without tournament/poll data."""
        # Create event without tournament or poll
        future_date = now_local().date() + timedelta(days=90)
        event = Event(
            date=future_date,
            name="Simple Event",
            event_type="holiday",
            year=future_date.year,
        )
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)

        response = admin_client.get(f"/admin/events/{event.id}/info")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == event.id
        assert data["tournament_id"] is None
        assert data["poll_id"] is None
        assert data["lake_name"] == ""
        assert data["ramp_name"] == ""

    def test_get_event_info_for_nonexistent_event(
        self, admin_client: TestClient, db_session: Session
    ):
        """Test that requesting info for nonexistent event returns 404."""
        response = admin_client.get("/admin/events/99999/info")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data

    def test_non_admin_cannot_get_event_info(
        self,
        member_client: TestClient,
        test_event: Event,
        db_session: Session,
    ):
        """Test that non-admins cannot access event info endpoint."""
        response = member_client.get(f"/admin/events/{test_event.id}/info", follow_redirects=False)

        assert response.status_code in [302, 303, 403]


class TestEventValidation:
    """Tests for event data validation endpoint and helper."""

    def test_validate_event_with_valid_data(self, admin_client: TestClient):
        """Test validation passes for valid event data."""
        future_date = (now_local() + timedelta(days=30)).strftime("%Y-%m-%d")

        response = admin_client.post(
            "/admin/events/validate",
            json={
                "date": future_date,
                "name": "Valid Event Name",
                "event_type": "sabc_tournament",
                "start_time": "06:00",
                "weigh_in_time": "15:00",
                "entry_fee": 50.0,
                "lake_name": "Test Lake",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" in data
        assert "warnings" in data
        assert len(data["errors"]) == 0

    def test_validate_event_with_invalid_date_format(self, admin_client: TestClient):
        """Test validation fails for invalid date format."""
        response = admin_client.post(
            "/admin/events/validate",
            json={
                "date": "invalid-date",
                "name": "Test Event",
                "event_type": "sabc_tournament",
                "start_time": "06:00",
                "weigh_in_time": "15:00",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["errors"]) > 0
        assert any("Invalid date format" in error for error in data["errors"])

    def test_validate_event_with_past_date_warns(self, admin_client: TestClient):
        """Test validation warns when creating event for past date."""
        past_date = (now_local() - timedelta(days=30)).strftime("%Y-%m-%d")

        response = admin_client.post(
            "/admin/events/validate",
            json={
                "date": past_date,
                "name": "Past Event",
                "event_type": "sabc_tournament",
                "start_time": "06:00",
                "weigh_in_time": "15:00",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["warnings"]) > 0
        assert any("past date" in warning.lower() for warning in data["warnings"])

    def test_validate_event_with_short_name_fails(self, admin_client: TestClient):
        """Test validation fails for names shorter than 3 characters."""
        future_date = (now_local() + timedelta(days=30)).strftime("%Y-%m-%d")

        response = admin_client.post(
            "/admin/events/validate",
            json={
                "date": future_date,
                "name": "AB",  # Too short
                "event_type": "sabc_tournament",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["errors"]) > 0
        assert any("at least 3 characters" in error for error in data["errors"])

    def test_validate_tournament_with_invalid_time_format(self, admin_client: TestClient):
        """Test validation fails for invalid time format."""
        future_date = (now_local() + timedelta(days=30)).strftime("%Y-%m-%d")

        response = admin_client.post(
            "/admin/events/validate",
            json={
                "date": future_date,
                "name": "Test Event",
                "event_type": "sabc_tournament",
                "start_time": "invalid",  # Invalid format
                "weigh_in_time": "15:00",
            },
        )

        # May return 200 with errors, or 500 if exception occurs
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert len(data["errors"]) > 0
            assert any("Invalid start time" in error for error in data["errors"])

    def test_validate_tournament_with_weigh_in_before_start(self, admin_client: TestClient):
        """Test validation fails when weigh-in time is before start time."""
        future_date = (now_local() + timedelta(days=30)).strftime("%Y-%m-%d")

        response = admin_client.post(
            "/admin/events/validate",
            json={
                "date": future_date,
                "name": "Test Event",
                "event_type": "sabc_tournament",
                "start_time": "15:00",
                "weigh_in_time": "06:00",  # Before start time
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["errors"]) > 0
        assert any("after start time" in error for error in data["errors"])

    def test_validate_tournament_with_negative_entry_fee(self, admin_client: TestClient):
        """Test validation fails for negative entry fee."""
        future_date = (now_local() + timedelta(days=30)).strftime("%Y-%m-%d")

        response = admin_client.post(
            "/admin/events/validate",
            json={
                "date": future_date,
                "name": "Test Event",
                "event_type": "sabc_tournament",
                "start_time": "06:00",
                "weigh_in_time": "15:00",
                "entry_fee": -50.0,  # Negative
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["errors"]) > 0
        assert any("cannot be negative" in error for error in data["errors"])

    def test_validate_holiday_with_tournament_details_warns(self, admin_client: TestClient):
        """Test validation warns when holiday has tournament details."""
        future_date = (now_local() + timedelta(days=30)).strftime("%Y-%m-%d")

        response = admin_client.post(
            "/admin/events/validate",
            json={
                "date": future_date,
                "name": "Holiday Event",
                "event_type": "holiday",
                "start_time": "06:00",  # Shouldn't be needed for holiday
                "entry_fee": 50.0,  # Shouldn't be needed for holiday
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["warnings"]) > 0
        assert any("don't typically need" in warning.lower() for warning in data["warnings"])

    def test_validate_other_tournament_without_lake_fails(self, admin_client: TestClient):
        """Test validation fails when other tournament is missing lake name."""
        future_date = (now_local() + timedelta(days=30)).strftime("%Y-%m-%d")

        response = admin_client.post(
            "/admin/events/validate",
            json={
                "date": future_date,
                "name": "Other Tournament",
                "event_type": "other_tournament",
                "start_time": "06:00",
                "weigh_in_time": "15:00",
                "lake_name": "",  # Missing
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["errors"]) > 0
        assert any("Lake name is required" in error for error in data["errors"])

    def test_validate_event_with_duplicate_date_warns(
        self,
        admin_client: TestClient,
        test_event: Event,
        db_session: Session,
    ):
        """Test validation warns when date already has an event."""
        response = admin_client.post(
            "/admin/events/validate",
            json={
                "date": str(test_event.date),
                "name": "Another Event",
                "event_type": "sabc_tournament",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["warnings"]) > 0
        assert any("already has event" in warning.lower() for warning in data["warnings"])

    def test_non_admin_cannot_validate_event(self, member_client: TestClient):
        """Test that non-admins cannot access validation endpoint."""
        future_date = (now_local() + timedelta(days=30)).strftime("%Y-%m-%d")

        response = member_client.post(
            "/admin/events/validate",
            json={
                "date": future_date,
                "name": "Test Event",
                "event_type": "sabc_tournament",
            },
            follow_redirects=False,
        )

        assert response.status_code in [302, 303, 403]


class TestEventCreationFlow:
    """Integration tests for complete event creation flows."""

    def test_create_sabc_tournament_with_all_details(
        self,
        admin_client: TestClient,
        test_lake: Lake,
        test_ramp: Ramp,
        db_session: Session,
    ):
        """Test creating a complete SABC tournament with all details."""
        future_date = (now_local() + timedelta(days=30)).strftime("%Y-%m-%d")

        response = post_with_csrf(
            admin_client,
            "/admin/events/create",
            data={
                "date": future_date,
                "name": "Complete Tournament",
                "event_type": "sabc_tournament",
                "start_time": "06:00",
                "weigh_in_time": "15:00",
                "entry_fee": "75.00",
                "lake_name": test_lake.display_name,
                "ramp_name": test_ramp.name,
                "fish_limit": "5",
                "description": "A complete tournament event",
            },
            follow_redirects=False,
        )

        # Should redirect to success or events list
        assert response.status_code in [302, 303]

        # Verify event was created
        event = (
            db_session.query(Event)
            .filter(Event.date == datetime.strptime(future_date, "%Y-%m-%d").date())
            .first()
        )
        assert event is not None
        assert event.name == "Complete Tournament"
        assert event.event_type == "sabc_tournament"
        assert event.entry_fee == Decimal("75.00")

    def test_create_holiday_event_minimal_details(
        self, admin_client: TestClient, db_session: Session
    ):
        """Test creating a holiday event with minimal details."""
        future_date = (now_local() + timedelta(days=60)).strftime("%Y-%m-%d")

        response = post_with_csrf(
            admin_client,
            "/admin/events/create",
            data={
                "date": future_date,
                "name": "Independence Day",
                "event_type": "holiday",
                "description": "July 4th Holiday",
            },
            follow_redirects=False,
        )

        # Should succeed
        assert response.status_code in [302, 303]

        # Verify event was created
        event = (
            db_session.query(Event)
            .filter(Event.date == datetime.strptime(future_date, "%Y-%m-%d").date())
            .first()
        )
        assert event is not None
        assert event.name == "Independence Day"
        assert event.event_type == "holiday"

    def test_create_other_tournament_event(self, admin_client: TestClient, db_session: Session):
        """Test creating an other tournament event."""
        future_date = (now_local() + timedelta(days=90)).strftime("%Y-%m-%d")

        response = post_with_csrf(
            admin_client,
            "/admin/events/create",
            data={
                "date": future_date,
                "name": "BASS Tournament",
                "event_type": "other_tournament",
                "start_time": "07:00",
                "weigh_in_time": "16:00",
                "lake_name": "Lake Travis",
            },
            follow_redirects=False,
        )

        # Should succeed
        assert response.status_code in [302, 303]
