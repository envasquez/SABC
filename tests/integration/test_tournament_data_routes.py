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

    def test_format_team_results_handles_null_numeric_fields(self):
        """Regression: prod tournament 136 crashed with `int(None)` because
        `r.get('total_fish', 0)` returns None when the key exists with a
        NULL value (the default kicks in only for missing keys). The
        underlying team_results columns (num_fish, place_finish,
        total_weight) are nullable in the schema, so the formatter must
        tolerate None and collapse it to zero."""
        from routes.tournaments.formatters import format_team_results

        raw_data = [
            {
                "place_finish": None,
                "angler1_name": "Solo Angler",
                "angler2_name": "",
                "angler2_id": None,
                "total_fish": None,
                "total_weight": None,
                "angler1_was_member": True,
                "angler2_was_member": True,
                "id": None,
            }
        ]
        result = format_team_results(raw_data)
        assert len(result) == 1
        place, team_name, fish, weight, _, _, row_id, team_size = result[0]
        assert (place, fish, weight, row_id, team_size) == (0, 0, 0.0, 0, 1)
        assert team_name == "Solo Angler"

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

    def test_format_individual_results_handles_null_id_from_team_format(self):
        """Regression: prod tournament 175 (team-format) crashed with
        `int(None)` on `r.get('id', 0)`. get_tournament_results LEFT JOINs
        `results` onto v_angler_tournament_results; team-format anglers
        only have a team_results row, so `r.id` comes back NULL. The
        nullable DB numerics (num_fish, total_weight, big_bass_weight) can
        also be NULL. All four must collapse to 0, not blow up."""
        from routes.tournaments.formatters import format_individual_results

        raw_data = [
            {
                "calculated_place": 1,
                "angler_name": "Team Angler",
                "num_fish": None,
                "total_weight": None,
                "big_bass_weight": None,
                "calculated_points": 100,
                "was_member": True,
                "id": None,
                "buy_in": False,
                "disqualified": False,
            }
        ]
        result = format_individual_results(raw_data)
        assert len(result) == 1
        place, name, fish, weight, big_bass, points, _, row_id = result[0]
        assert (place, fish, weight, big_bass, points, row_id) == (1, 0, 0.0, 0.0, 100, 0)
        assert name == "Team Angler"

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

    def test_format_buy_in_results_handles_null_id(self):
        """Regression: same LEFT JOIN nullability as individual results —
        buy-in rows from team-format tournaments can have `id = None`."""
        from routes.tournaments.formatters import format_buy_in_results

        raw_data = [
            {
                "calculated_place": 10,
                "angler_name": "Team Buy-in",
                "calculated_points": 50,
                "was_member": True,
                "id": None,
                "buy_in": True,
            }
        ]
        place, results = format_buy_in_results(raw_data)
        assert place == 10
        assert results[0][4] == 0  # row id collapses to 0 instead of raising

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
