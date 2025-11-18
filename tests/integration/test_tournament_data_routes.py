"""Integration tests for tournament data and viewing routes.

Tests tournament viewing, results display, and tournament data helpers.
"""

from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.db_schema import Event, Lake, Ramp, Tournament


class TestTournamentViewRoutes:
    """Test tournament viewing routes."""

    def test_tournaments_list_page_loads(self, client: TestClient):
        """Test tournaments list page loads."""
        response = client.get("/tournaments")
        assert response.status_code == 200

    def test_individual_tournament_view(self, client: TestClient, db_session: Session):
        """Test individual tournament view page."""
        event = Event(
            name="Tournament",
            date=datetime.now().date(),
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

        tournament = Tournament(
            event_id=event.id,
            lake_id=lake.id,
            ramp_id=ramp.id,
            name="Test",
            complete=True,
        )
        db_session.add(tournament)
        db_session.commit()

        response = client.get(f"/tournaments/{tournament.id}")
        assert response.status_code == 200


class TestTournamentDataHelpers:
    """Test tournament data helper functions."""

    def test_format_team_results(self):
        """Test team results formatting."""
        from routes.tournaments.formatters import format_team_results

        raw_data = [
            {
                "place_finish": 1,
                "angler1_name": "John Doe",
                "angler2_name": "Jane Doe",
                "angler2_id": 2,
                "total_fish": 5,
                "total_weight": 15.5,
                "angler1_was_member": True,
                "angler2_was_member": True,
                "id": 1,
            }
        ]
        result = format_team_results(raw_data)
        assert len(result) == 1
        assert result[0][0] == 1  # place
        assert "John Doe / Jane Doe" in result[0][1]  # team name
        assert result[0][7] == 2  # team size

    def test_format_individual_results(self):
        """Test individual results formatting."""
        from routes.tournaments.formatters import format_individual_results

        raw_data = [
            {
                "calculated_place": 1,
                "angler_name": "John Doe",
                "num_fish": 5,
                "total_weight": 15.5,
                "big_bass_weight": 5.2,
                "calculated_points": 100,
                "was_member": True,
                "id": 1,
                "buy_in": False,
                "disqualified": False,
            }
        ]
        result = format_individual_results(raw_data)
        assert len(result) == 1
        assert result[0][0] == 1  # place
        assert result[0][1] == "John Doe"  # name

    def test_format_buy_in_results(self):
        """Test buy-in results formatting."""
        from routes.tournaments.formatters import format_buy_in_results

        raw_data = [
            {
                "calculated_place": 10,
                "angler_name": "John Doe",
                "calculated_points": 50,
                "was_member": True,
                "id": 1,
                "buy_in": True,
            }
        ]
        place, results = format_buy_in_results(raw_data)
        assert place == 10
        assert len(results) == 1
        assert results[0][0] == "John Doe"

    def test_format_disqualified_results(self):
        """Test disqualified results formatting."""
        from routes.tournaments.formatters import format_disqualified_results

        raw_data = [
            {"name": "John Doe", "was_member": True},
            {"name": "Jane Doe", "was_member": False},
        ]
        result = format_disqualified_results(raw_data)
        assert len(result) == 2
        assert result[0][0] == "John Doe"
        assert result[0][1] is True
