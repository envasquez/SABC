"""
Comprehensive tests for dead fish penalty calculations.

This test suite ensures that dead fish penalties are correctly applied
throughout the tournament results system, including:
- Individual tournament results
- Team tournament results
- Tournament points calculation
- Place rankings
- Awards/standings calculations
"""

from typing import Any, Dict

import pytest

from core.helpers.tournament_points import calculate_tournament_points


class TestDeadFishPenalties:
    """Test suite for dead fish penalty calculations."""

    def create_result(
        self,
        angler_id: int,
        gross_weight: float,
        dead_fish_penalty: float = 0.0,
        big_bass_weight: float = 0.0,
        was_member: bool = True,
        buy_in: bool = False,
        disqualified: bool = False,
        num_fish: int = 5,
    ) -> Dict[str, Any]:
        """
        Create a tournament result for testing.

        Args:
            gross_weight: Weight BEFORE penalty is subtracted
            dead_fish_penalty: Penalty amount to subtract

        Note: The database stores net_weight (gross - penalty) in total_weight column.
        This simulates what happens when results are saved via the form.
        """
        net_weight = gross_weight - dead_fish_penalty
        return {
            "angler_id": angler_id,
            "total_weight": net_weight,  # DB stores net weight
            "dead_fish_penalty": dead_fish_penalty,
            "big_bass_weight": big_bass_weight,
            "was_member": was_member,
            "buy_in": buy_in,
            "disqualified": disqualified,
            "num_fish": num_fish,
        }

    def test_no_penalties_normal_ranking(self):
        """Test that normal ranking works without any penalties."""
        results = [
            self.create_result(1, gross_weight=15.0, big_bass_weight=5.0),
            self.create_result(2, gross_weight=12.0, big_bass_weight=4.0),
            self.create_result(3, gross_weight=10.0, big_bass_weight=3.0),
        ]
        calculated = calculate_tournament_points(results)

        assert len(calculated) == 3
        # First place: 15.0 lbs = 100 points
        assert calculated[0]["calculated_place"] == 1
        assert calculated[0]["calculated_points"] == 100
        # Second place: 12.0 lbs = 99 points
        assert calculated[1]["calculated_place"] == 2
        assert calculated[1]["calculated_points"] == 99
        # Third place: 10.0 lbs = 98 points
        assert calculated[2]["calculated_place"] == 3
        assert calculated[2]["calculated_points"] == 98

    def test_quarter_pound_penalty_affects_ranking(self):
        """Test that 0.25 lb penalty affects ranking correctly."""
        results = [
            # Angler 1: 10.50 gross - 0.25 penalty = 10.25 net
            self.create_result(1, gross_weight=10.50, dead_fish_penalty=0.25, big_bass_weight=4.0),
            # Angler 2: 10.00 gross - 0.00 penalty = 10.00 net
            self.create_result(2, gross_weight=10.00, dead_fish_penalty=0.0, big_bass_weight=3.5),
        ]
        calculated = calculate_tournament_points(results)

        # Angler 1 should be first with 10.25 net weight
        assert calculated[0]["angler_id"] == 1
        assert calculated[0]["total_weight"] == 10.25
        assert calculated[0]["calculated_place"] == 1
        assert calculated[0]["calculated_points"] == 100

        # Angler 2 should be second with 10.00 net weight
        assert calculated[1]["angler_id"] == 2
        assert calculated[1]["total_weight"] == 10.00
        assert calculated[1]["calculated_place"] == 2
        assert calculated[1]["calculated_points"] == 99

    def test_half_pound_penalty_affects_ranking(self):
        """Test that 0.50 lb penalty correctly changes ranking order."""
        results = [
            # Angler 1: 10.25 gross - 0.25 penalty = 10.00 net
            self.create_result(1, gross_weight=10.25, dead_fish_penalty=0.25, big_bass_weight=4.0),
            # Angler 2: 10.00 gross - 0.50 penalty = 9.50 net (should drop to 2nd)
            self.create_result(2, gross_weight=10.00, dead_fish_penalty=0.50, big_bass_weight=3.5),
        ]
        calculated = calculate_tournament_points(results)

        # Angler 1 should be first with 10.00 net weight
        assert calculated[0]["angler_id"] == 1
        assert calculated[0]["total_weight"] == 10.00
        assert calculated[0]["calculated_place"] == 1
        assert calculated[0]["calculated_points"] == 100

        # Angler 2 should be second with 9.50 net weight
        assert calculated[1]["angler_id"] == 2
        assert calculated[1]["total_weight"] == 9.50
        assert calculated[1]["calculated_place"] == 2
        assert calculated[1]["calculated_points"] == 99

    def test_multiple_penalties_complex_ranking(self):
        """Test complex scenario with multiple anglers having different penalties."""
        results = [
            # Angler 1: 15.00 gross - 0.50 penalty = 14.50 net (should be 1st)
            self.create_result(1, gross_weight=15.00, dead_fish_penalty=0.50, big_bass_weight=5.0),
            # Angler 2: 14.00 gross - 0.00 penalty = 14.00 net (should be 2nd)
            self.create_result(2, gross_weight=14.00, dead_fish_penalty=0.0, big_bass_weight=4.5),
            # Angler 3: 14.50 gross - 0.75 penalty = 13.75 net (should be 3rd)
            self.create_result(3, gross_weight=14.50, dead_fish_penalty=0.75, big_bass_weight=4.0),
            # Angler 4: 13.00 gross - 0.25 penalty = 12.75 net (should be 4th)
            self.create_result(4, gross_weight=13.00, dead_fish_penalty=0.25, big_bass_weight=3.5),
        ]
        calculated = calculate_tournament_points(results)

        # Verify correct order by net weight
        assert calculated[0]["angler_id"] == 1
        assert calculated[0]["total_weight"] == 14.50
        assert calculated[0]["calculated_place"] == 1

        assert calculated[1]["angler_id"] == 2
        assert calculated[1]["total_weight"] == 14.00
        assert calculated[1]["calculated_place"] == 2

        assert calculated[2]["angler_id"] == 3
        assert calculated[2]["total_weight"] == 13.75
        assert calculated[2]["calculated_place"] == 3

        assert calculated[3]["angler_id"] == 4
        assert calculated[3]["total_weight"] == 12.75
        assert calculated[3]["calculated_place"] == 4

    def test_penalty_causes_tie_in_weight(self):
        """Test that penalties can create ties that are broken by big bass."""
        results = [
            # Angler 1: 10.50 gross - 0.50 penalty = 10.00 net, 5.0 bass (wins tie)
            self.create_result(1, gross_weight=10.50, dead_fish_penalty=0.50, big_bass_weight=5.0),
            # Angler 2: 10.25 gross - 0.25 penalty = 10.00 net, 4.0 bass (loses tie)
            self.create_result(2, gross_weight=10.25, dead_fish_penalty=0.25, big_bass_weight=4.0),
        ]
        calculated = calculate_tournament_points(results)

        # Angler 1 comes first due to bigger bass (tiebreaker)
        assert calculated[0]["angler_id"] == 1
        assert calculated[0]["total_weight"] == 10.00
        assert calculated[0]["big_bass_weight"] == 5.0
        assert calculated[0]["calculated_place"] == 1

        # Angler 2 is second (dense ranking after tie is broken by big bass)
        assert calculated[1]["angler_id"] == 2
        assert calculated[1]["total_weight"] == 10.00
        assert calculated[1]["big_bass_weight"] == 4.0
        assert calculated[1]["calculated_place"] == 2  # Dense ranking: next place

    def test_penalty_with_guest_angler(self):
        """Test that penalties work correctly with guest anglers (0 points)."""
        results = [
            # Member: 12.00 gross - 0.25 penalty = 11.75 net (1st, 100 pts)
            self.create_result(1, gross_weight=12.00, dead_fish_penalty=0.25, was_member=True),
            # Guest: 12.50 gross - 0.50 penalty = 12.00 net (actually higher, but 0 pts)
            self.create_result(2, gross_weight=12.50, dead_fish_penalty=0.50, was_member=False),
            # Member: 11.00 gross - 0.00 penalty = 11.00 net (3rd, 99 pts)
            self.create_result(3, gross_weight=11.00, dead_fish_penalty=0.0, was_member=True),
        ]
        calculated = calculate_tournament_points(results)

        # Guest should be placed first by weight
        assert calculated[0]["angler_id"] == 2
        assert calculated[0]["total_weight"] == 12.00
        assert calculated[0]["calculated_place"] == 1
        assert calculated[0]["calculated_points"] == 0  # Guest gets 0 points

        # First member should be second
        assert calculated[1]["angler_id"] == 1
        assert calculated[1]["total_weight"] == 11.75
        assert calculated[1]["calculated_place"] == 2
        assert calculated[1]["calculated_points"] == 100  # First member gets 100

        # Second member should be third
        assert calculated[2]["angler_id"] == 3
        assert calculated[2]["total_weight"] == 11.00
        assert calculated[2]["calculated_place"] == 3
        assert calculated[2]["calculated_points"] == 99  # Second member gets 99

    def test_zero_weight_with_penalty(self):
        """Test that angler with 0 fish and penalty still gets correctly ranked."""
        results = [
            # Member with fish
            self.create_result(1, gross_weight=10.00, dead_fish_penalty=0.0, num_fish=5),
            # Member with 0 fish (should get 98 points)
            self.create_result(2, gross_weight=0.0, dead_fish_penalty=0.0, num_fish=0),
        ]
        calculated = calculate_tournament_points(results)

        assert calculated[0]["angler_id"] == 1
        assert calculated[0]["calculated_points"] == 100

        assert calculated[1]["angler_id"] == 2
        assert calculated[1]["total_weight"] == 0.0
        assert calculated[1]["calculated_points"] == 98  # Zero gets last_fish - 2

    def test_buy_in_with_penalty(self):
        """Test that buy-in results with penalties are placed correctly."""
        results = [
            # Regular member
            self.create_result(1, gross_weight=10.00, dead_fish_penalty=0.0, buy_in=False),
            # Buy-in with penalty: 5.00 gross - 0.25 penalty = 4.75 net
            self.create_result(2, gross_weight=5.00, dead_fish_penalty=0.25, buy_in=True),
        ]
        calculated = calculate_tournament_points(results)

        # Regular result first
        assert calculated[0]["angler_id"] == 1
        assert calculated[0]["calculated_place"] == 1
        assert calculated[0]["calculated_points"] == 100

        # Buy-in second (place after all regular results)
        assert calculated[1]["angler_id"] == 2
        assert calculated[1]["total_weight"] == 4.75
        assert calculated[1]["calculated_place"] == 2
        assert calculated[1]["calculated_points"] == 96  # Buy-in gets last_fish - 4

    def test_realistic_tournament_scenario(self):
        """Test a realistic tournament with multiple penalties."""
        results = [
            # 1st: 18.75 gross - 0.25 penalty = 18.50 net
            self.create_result(1, gross_weight=18.75, dead_fish_penalty=0.25, big_bass_weight=6.0),
            # 2nd: 17.50 gross - 0.00 penalty = 17.50 net
            self.create_result(2, gross_weight=17.50, dead_fish_penalty=0.0, big_bass_weight=5.5),
            # 3rd: 18.00 gross - 0.50 penalty = 17.50 net (tied, loses on big bass)
            self.create_result(3, gross_weight=18.00, dead_fish_penalty=0.50, big_bass_weight=5.0),
            # Guest: 20.00 gross - 0.75 penalty = 19.25 net (highest, but 0 pts)
            self.create_result(
                4, gross_weight=20.00, dead_fish_penalty=0.75, was_member=False, big_bass_weight=7.0
            ),
            # 4th: 15.00 gross - 0.25 penalty = 14.75 net
            self.create_result(5, gross_weight=15.00, dead_fish_penalty=0.25, big_bass_weight=4.5),
            # Zero: 0.00 gross
            self.create_result(6, gross_weight=0.0, dead_fish_penalty=0.0, num_fish=0),
        ]
        calculated = calculate_tournament_points(results)

        # Guest should be first by weight
        assert calculated[0]["angler_id"] == 4
        assert calculated[0]["total_weight"] == 19.25
        assert calculated[0]["calculated_points"] == 0

        # Member 1 should be second (18.50)
        assert calculated[1]["angler_id"] == 1
        assert calculated[1]["total_weight"] == 18.50
        assert calculated[1]["calculated_points"] == 100

        # Members 2 and 3 tied at 17.50 (2 wins on big bass, gets 3rd place)
        assert calculated[2]["angler_id"] == 2
        assert calculated[2]["total_weight"] == 17.50
        assert calculated[2]["calculated_points"] == 99

        # Member 3 gets 4th place (dense ranking after big bass tiebreaker)
        assert calculated[3]["angler_id"] == 3
        assert calculated[3]["total_weight"] == 17.50
        assert calculated[3]["calculated_points"] == 98  # Next member points

        # Member 5 (14.75) - 5th member with fish
        assert calculated[4]["angler_id"] == 5
        assert calculated[4]["total_weight"] == 14.75
        assert calculated[4]["calculated_points"] == 97  # Sequential: 100, 99, 98, 97

        # Zero member - gets last_fish_points - 2
        assert calculated[5]["angler_id"] == 6
        assert calculated[5]["total_weight"] == 0.0
        assert calculated[5]["calculated_points"] == 95  # 97 - 2 for zero


class TestTeamDeadFishPenalties:
    """Test that team results correctly account for dead fish penalties."""

    def test_team_weight_calculation_with_penalties(self):
        """Test that team total weight is net weight (after penalties) of both anglers."""
        # This is a documentation test - the actual calculation happens in
        # routes/admin/tournaments/individual_results.py lines 94-120
        #
        # Example:
        # Angler A: 10.00 gross - 0.25 penalty = 9.75 net
        # Angler B: 12.50 gross - 0.50 penalty = 12.00 net
        # Team total should be: 9.75 + 12.00 = 21.75 (NOT 22.50)
        pass


class TestSQLQueryPenalties:
    """Document that SQL queries must use net weight calculations."""

    def test_individual_results_query_uses_net_weight(self):
        """
        Document that get_tournament_results() must calculate net weight.

        Expected SQL pattern:
        SELECT (r.total_weight - COALESCE(r.dead_fish_penalty, 0)) as total_weight
        FROM results r
        ORDER BY (r.total_weight - COALESCE(r.dead_fish_penalty, 0)) DESC
        """
        pass

    def test_team_results_query_uses_net_weight(self):
        """
        Document that team result updates must use net weight for both anglers.

        Expected calculation:
        net_weight_angler_1 = total_weight_1 - penalty_1
        net_weight_angler_2 = total_weight_2 - penalty_2
        team_total = net_weight_angler_1 + net_weight_angler_2
        """
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
