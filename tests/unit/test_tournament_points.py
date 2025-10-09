"""Unit tests for tournament points calculation."""

from typing import Any, Dict

from core.helpers.tournament_points import calculate_tournament_points


class TestTournamentPointsCalculation:
    """Test suite for tournament points calculator."""

    def create_result(
        self,
        total_weight: float,
        big_bass_weight: float = 0.0,
        was_member: bool = True,
        buy_in: bool = False,
        disqualified: bool = False,
    ) -> Dict[str, Any]:
        """Create a tournament result for testing."""
        return {
            "total_weight": total_weight,
            "big_bass_weight": big_bass_weight,
            "was_member": was_member,
            "buy_in": buy_in,
            "disqualified": disqualified,
        }

    def test_empty_results_returns_empty_list(self):
        """Test that empty results list returns empty list."""
        result = calculate_tournament_points([])
        assert result == []

    def test_single_member_with_fish_gets_100_points(self):
        """Test single member with fish gets 100 points and place 1."""
        results = [self.create_result(total_weight=10.5, big_bass_weight=3.2)]
        calculated = calculate_tournament_points(results)

        assert len(calculated) == 1
        assert calculated[0]["calculated_points"] == 100
        assert calculated[0]["calculated_place"] == 1

    def test_two_members_sequential_points(self):
        """Test two members get sequential points (100, 99)."""
        results = [
            self.create_result(total_weight=15.0, big_bass_weight=5.0),
            self.create_result(total_weight=10.0, big_bass_weight=3.0),
        ]
        calculated = calculate_tournament_points(results)

        assert len(calculated) == 2
        assert calculated[0]["calculated_points"] == 100
        assert calculated[0]["calculated_place"] == 1
        assert calculated[1]["calculated_points"] == 99
        assert calculated[1]["calculated_place"] == 2

    def test_guest_gets_zero_points(self):
        """Test guest gets 0 points but is placed by weight."""
        results = [
            self.create_result(total_weight=15.0, big_bass_weight=5.0, was_member=True),
            self.create_result(total_weight=10.0, big_bass_weight=3.0, was_member=False),
        ]
        calculated = calculate_tournament_points(results)

        assert calculated[0]["calculated_points"] == 100  # Member
        assert calculated[1]["calculated_points"] == 0  # Guest
        assert calculated[1]["calculated_place"] == 2  # Still placed 2nd

    def test_member_after_guest_gets_correct_points(self):
        """Test member after guest gets previous_member_points - 1."""
        results = [
            self.create_result(total_weight=15.0, was_member=True),  # 100 pts
            self.create_result(total_weight=12.0, was_member=False),  # 0 pts (guest)
            self.create_result(total_weight=10.0, was_member=True),  # Should be 99 pts
        ]
        calculated = calculate_tournament_points(results)

        assert calculated[0]["calculated_points"] == 100
        assert calculated[1]["calculated_points"] == 0  # Guest
        assert calculated[2]["calculated_points"] == 99  # Next member gets 100-1

    def test_member_zero_weight_gets_minus_two_points(self):
        """Test member with 0 weight gets last_member_points - 2."""
        results = [
            self.create_result(total_weight=15.0, was_member=True),  # 100 pts
            self.create_result(total_weight=10.0, was_member=True),  # 99 pts
            self.create_result(total_weight=0.0, was_member=True),  # Should be 99-2 = 97
        ]
        calculated = calculate_tournament_points(results)

        assert calculated[0]["calculated_points"] == 100
        assert calculated[1]["calculated_points"] == 99
        assert calculated[2]["calculated_points"] == 97  # 99 - 2 (last fish - 2)

    def test_weight_tie_same_place(self):
        """Test tied total weight results in same place."""
        results = [
            self.create_result(total_weight=10.0, big_bass_weight=3.0),
            self.create_result(total_weight=10.0, big_bass_weight=3.0),
            self.create_result(total_weight=8.0, big_bass_weight=2.0),
        ]
        calculated = calculate_tournament_points(results)

        assert calculated[0]["calculated_place"] == 1
        assert calculated[1]["calculated_place"] == 1  # Tied for 1st
        assert calculated[2]["calculated_place"] == 3  # Not 2nd (dense ranking)

    def test_weight_tie_broken_by_big_bass(self):
        """Test weight tie broken by big bass weight."""
        results = [
            self.create_result(total_weight=10.0, big_bass_weight=5.0),
            self.create_result(total_weight=10.0, big_bass_weight=3.0),
        ]
        calculated = calculate_tournament_points(results)

        assert calculated[0]["calculated_place"] == 1
        assert calculated[0]["big_bass_weight"] == 5.0
        assert calculated[1]["calculated_place"] == 2
        assert calculated[1]["big_bass_weight"] == 3.0

    def test_buy_in_placed_after_regular_results(self):
        """Test buy-in results are placed after all regular results."""
        results = [
            self.create_result(total_weight=15.0, was_member=True),
            self.create_result(total_weight=10.0, was_member=True),
            self.create_result(total_weight=20.0, was_member=True, buy_in=True),
        ]
        calculated = calculate_tournament_points(results)

        # Find the buy-in result
        buy_in_result = [r for r in calculated if r["buy_in"]][0]
        assert buy_in_result["calculated_place"] == 3  # After 2 regular results

    def test_buy_in_gets_last_fish_points_minus_four(self):
        """Test buy-in gets last_member_with_fish_points - 4."""
        results = [
            self.create_result(total_weight=15.0, was_member=True),  # 100 pts
            self.create_result(total_weight=10.0, was_member=True),  # 99 pts
            self.create_result(total_weight=20.0, was_member=True, buy_in=True),  # 99-4=95
        ]
        calculated = calculate_tournament_points(results)

        buy_in_result = [r for r in calculated if r["buy_in"]][0]
        assert buy_in_result["calculated_points"] == 95  # 99 - 4

    def test_disqualified_not_included(self):
        """Test disqualified results are not included in calculations."""
        results = [
            self.create_result(total_weight=15.0, was_member=True),
            self.create_result(total_weight=10.0, was_member=True, disqualified=True),
            self.create_result(total_weight=8.0, was_member=True),
        ]
        calculated = calculate_tournament_points(results)

        # Only 2 results should be included
        assert len(calculated) == 2
        assert calculated[0]["calculated_place"] == 1
        assert calculated[1]["calculated_place"] == 2

    def test_sorting_by_weight_descending(self):
        """Test results are sorted by weight descending (heaviest first)."""
        results = [
            self.create_result(total_weight=8.0),
            self.create_result(total_weight=15.0),
            self.create_result(total_weight=10.0),
        ]
        calculated = calculate_tournament_points(results)

        assert calculated[0]["total_weight"] == 15.0
        assert calculated[1]["total_weight"] == 10.0
        assert calculated[2]["total_weight"] == 8.0

    def test_all_zeros_member_edge_case(self):
        """Test edge case where all members have zero weight."""
        results = [
            self.create_result(total_weight=0.0, was_member=True),
            self.create_result(total_weight=0.0, was_member=True),
        ]
        calculated = calculate_tournament_points(results)

        # When no members have fish, all zeros get 98 (no fish yet edge case)
        # The second zero doesn't get points reduction because last_member_with_fish_points is None
        assert calculated[0]["calculated_points"] == 98
        assert calculated[1]["calculated_points"] == 98

    def test_buy_in_only_edge_case(self):
        """Test edge case where only buy-ins exist."""
        results = [
            self.create_result(total_weight=10.0, was_member=True, buy_in=True),
        ]
        calculated = calculate_tournament_points(results)

        assert len(calculated) == 1
        assert calculated[0]["calculated_place"] == 1
        assert calculated[0]["calculated_points"] == 96  # Edge case default

    def test_complex_scenario_mixed_members_guests_zeros(self):
        """Test complex scenario with members, guests, and zeros."""
        results = [
            self.create_result(total_weight=20.0, big_bass_weight=6.0, was_member=True),  # 100
            self.create_result(total_weight=18.0, big_bass_weight=5.0, was_member=False),  # 0
            self.create_result(total_weight=15.0, big_bass_weight=4.0, was_member=True),  # 99
            self.create_result(total_weight=10.0, big_bass_weight=3.0, was_member=True),  # 98
            self.create_result(total_weight=0.0, big_bass_weight=0.0, was_member=True),  # 96
        ]
        calculated = calculate_tournament_points(results)

        assert calculated[0]["calculated_points"] == 100  # 1st member with fish
        assert calculated[1]["calculated_points"] == 0  # Guest
        assert calculated[2]["calculated_points"] == 99  # 2nd member with fish
        assert calculated[3]["calculated_points"] == 98  # 3rd member with fish
        assert calculated[4]["calculated_points"] == 96  # Zero (98-2)

        assert calculated[0]["calculated_place"] == 1
        assert calculated[1]["calculated_place"] == 2
        assert calculated[2]["calculated_place"] == 3
        assert calculated[3]["calculated_place"] == 4
        assert calculated[4]["calculated_place"] == 5
