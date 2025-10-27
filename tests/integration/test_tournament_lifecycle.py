"""
Integration tests for complete tournament lifecycle.

This test suite covers the entire tournament workflow from creation through
results entry, points calculation, and standings - the core business logic.
"""

import pytest
from fastapi.testclient import TestClient

from app_setup import create_app
from core.db_schema import Angler, Event, Tournament
from core.db_schema.session import get_session


@pytest.fixture
def app():
    """Create test application."""
    return create_app()


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def admin_session(client):
    """Create an authenticated admin session."""
    # Login as admin
    with get_session() as session:
        admin = session.query(Angler).filter(Angler.is_admin == True).first()  # noqa: E712
        if not admin:
            # Create admin if doesn't exist
            admin = Angler(
                name="Test Admin",
                email="admin@test.com",
                member=True,
                is_admin=True,
            )
            session.add(admin)
            session.commit()

    # Perform login
    client.post(
        "/login",
        data={"email": "admin@test.com", "password": "testpass"},
        follow_redirects=False,
    )
    return client


class TestTournamentCreation:
    """Test tournament creation workflow."""

    def test_create_sabc_tournament_event(self, admin_session):
        """Test creating a complete SABC tournament event."""
        # Create an event
        event_data = {
            "date": "2025-01-15",
            "event_type": "sabc_tournament",
            "name": "Test Tournament",
            "description": "Integration test tournament",
            "start_time": "06:00",
            "weigh_in_time": "15:00",
            "lake_name": "Lake Travis",
            "ramp_name": "Mansfield Dam",
            "entry_fee": "50.00",
            "fish_limit": "5",
            "aoy_points": "true",
        }

        response = admin_session.post("/admin/events", data=event_data)
        assert response.status_code in [200, 303]  # Success or redirect

    def test_create_meeting_event(self, admin_session):
        """Test creating a meeting event."""
        event_data = {
            "date": "2025-01-20",
            "event_type": "meeting",
            "name": "Monthly Meeting",
            "description": "Test meeting",
        }

        response = admin_session.post("/admin/events", data=event_data)
        assert response.status_code in [200, 303]


class TestTournamentResults:
    """Test tournament results entry and calculations."""

    @pytest.fixture(autouse=True)
    def setup_tournament(self, admin_session):
        """Create a tournament for testing."""
        with get_session() as session:
            # Create test anglers
            angler1 = Angler(name="Angler One", email="a1@test.com", member=True)
            angler2 = Angler(name="Angler Two", email="a2@test.com", member=True)
            angler3 = Angler(name="Guest Angler", email="a3@test.com", member=False)
            session.add_all([angler1, angler2, angler3])
            session.commit()

            # Create event and tournament
            event = Event(
                date="2025-02-01",
                name="Test Tournament",
                event_type="sabc_tournament",
            )
            session.add(event)
            session.commit()

            tournament = Tournament(
                event_id=event.id,
                lake_id=1,
                ramp_id=1,
                fish_limit=5,
                entry_fee=50.00,
            )
            session.add(tournament)
            session.commit()

            self.tournament_id = tournament.id
            self.angler1_id = angler1.id
            self.angler2_id = angler2.id
            self.angler3_id = angler3.id

    def test_enter_individual_results(self, admin_session):
        """Test entering individual tournament results."""
        # Enter results for angler 1
        result_data = {
            "angler_id": self.angler1_id,
            "num_fish": "5",
            "total_weight": "15.50",
            "big_bass_weight": "5.25",
            "dead_fish": "0.0",
            "disqualified": "false",
            "buy_in": "false",
            "was_member": "true",
        }

        response = admin_session.post(
            f"/admin/tournaments/{self.tournament_id}/results",
            data=result_data,
        )
        assert response.status_code == 200
        assert response.json().get("success") is True

    def test_enter_results_with_dead_fish_penalty(self, admin_session):
        """Test that dead fish penalties are correctly subtracted."""
        # Enter result with 0.25 lb penalty
        result_data = {
            "angler_id": self.angler2_id,
            "num_fish": "5",
            "total_weight": "12.25",  # Gross weight
            "big_bass_weight": "4.00",
            "dead_fish": "0.25",  # Penalty
            "disqualified": "false",
            "buy_in": "false",
            "was_member": "true",
        }

        response = admin_session.post(
            f"/admin/tournaments/{self.tournament_id}/results",
            data=result_data,
        )
        assert response.status_code == 200

        # Verify net weight is stored (12.25 - 0.25 = 12.00)
        with get_session() as session:
            from core.db_schema import Result

            result = (
                session.query(Result)
                .filter(
                    Result.tournament_id == self.tournament_id,
                    Result.angler_id == self.angler2_id,
                )
                .first()
            )
            assert result is not None
            assert float(result.total_weight) == 12.00  # Net weight
            assert float(result.dead_fish_penalty) == 0.25

    def test_delete_individual_result(self, admin_session):
        """Test deleting an individual result."""
        # First create a result
        result_data = {
            "angler_id": self.angler1_id,
            "num_fish": "3",
            "total_weight": "8.00",
            "big_bass_weight": "3.00",
            "dead_fish": "0.0",
        }

        response = admin_session.post(
            f"/admin/tournaments/{self.tournament_id}/results",
            data=result_data,
        )

        # Get the result ID
        with get_session() as session:
            from core.db_schema import Result

            result = (
                session.query(Result)
                .filter(
                    Result.tournament_id == self.tournament_id,
                    Result.angler_id == self.angler1_id,
                )
                .first()
            )
            result_id = result.id

        # Delete it
        response = admin_session.delete(
            f"/admin/tournaments/{self.tournament_id}/results/{result_id}"
        )
        assert response.status_code == 200
        assert response.json().get("success") is True


class TestPointsCalculation:
    """Test that tournament points are calculated correctly."""

    def test_points_with_members_and_guests(self):
        """Test points calculation with mix of members and guests."""
        from core.helpers.tournament_points import calculate_tournament_points

        results = [
            {
                "angler_id": 1,
                "total_weight": 15.0,
                "big_bass_weight": 5.0,
                "was_member": True,
                "buy_in": False,
                "disqualified": False,
            },
            {
                "angler_id": 2,
                "total_weight": 12.0,
                "big_bass_weight": 4.0,
                "was_member": False,  # Guest
                "buy_in": False,
                "disqualified": False,
            },
            {
                "angler_id": 3,
                "total_weight": 10.0,
                "big_bass_weight": 3.0,
                "was_member": True,
                "buy_in": False,
                "disqualified": False,
            },
        ]

        calculated = calculate_tournament_points(results)

        # Member with highest weight gets 100 points
        assert calculated[0]["calculated_points"] == 100
        # Guest gets 0 points
        assert calculated[1]["calculated_points"] == 0
        # Second member gets 99 points (100 - 1)
        assert calculated[2]["calculated_points"] == 99


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
