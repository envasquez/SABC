"""Unit tests for tournament points calculation."""

from core.helpers.tournament_points import calculate_tournament_points


class TestTournamentPoints:
    """Test tournament points calculation logic."""

    def test_calculate_points_single_angler(self):
        """Test points calculation for single angler."""
        results = [
            {
                "id": 1,
                "angler_name": "John Doe",
                "total_weight": 15.5,
                "num_fish": 5,
                "big_bass_weight": 5.2,
                "buy_in": False,
                "disqualified": False,
                "was_member": True,
            }
        ]
        calculated = calculate_tournament_points(results)
        assert len(calculated) == 1
        assert calculated[0]["calculated_place"] == 1
        assert "calculated_points" in calculated[0]

    def test_calculate_points_multiple_anglers(self):
        """Test points calculation for multiple anglers."""
        results = [
            {
                "id": 1,
                "angler_name": "John Doe",
                "total_weight": 15.5,
                "num_fish": 5,
                "big_bass_weight": 5.2,
                "buy_in": False,
                "disqualified": False,
                "was_member": True,
            },
            {
                "id": 2,
                "angler_name": "Jane Doe",
                "total_weight": 12.3,
                "num_fish": 5,
                "big_bass_weight": 4.1,
                "buy_in": False,
                "disqualified": False,
                "was_member": True,
            },
        ]
        calculated = calculate_tournament_points(results)
        assert len(calculated) == 2
        assert calculated[0]["calculated_place"] == 1
        assert calculated[1]["calculated_place"] == 2

    def test_calculate_points_with_buy_in(self):
        """Test points calculation includes buy-in entries."""
        results = [
            {
                "id": 1,
                "angler_name": "John Doe",
                "total_weight": 15.5,
                "num_fish": 5,
                "big_bass_weight": 5.2,
                "buy_in": False,
                "disqualified": False,
                "was_member": True,
            },
            {
                "id": 2,
                "angler_name": "Jane Doe",
                "total_weight": 0,
                "num_fish": 0,
                "big_bass_weight": 0,
                "buy_in": True,
                "disqualified": False,
                "was_member": True,
            },
        ]
        calculated = calculate_tournament_points(results)
        assert len(calculated) == 2
        buy_ins = [r for r in calculated if r["buy_in"]]
        assert len(buy_ins) == 1
