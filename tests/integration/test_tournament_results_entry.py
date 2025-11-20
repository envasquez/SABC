"""
Phase 14: Comprehensive tests for tournament results entry routes.

Coverage focus:
- routes/admin/tournaments/individual_results.py (25.0% → target 85%+)
- routes/admin/tournaments/team_results.py (27.1% → target 85%+)
- routes/admin/tournaments/enter_results.py (31.8% → target 85%+)
- routes/admin/tournaments/validation.py (0.0% → target 90%+)
"""

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from core.db_schema import Angler, Result, TeamResult, Tournament
from routes.admin.tournaments.validation import (
    sanitize_weight,
    validate_tournament_result,
)
from tests.conftest import TestClient, post_with_csrf


class TestEnterResultsPage:
    """Test enter results page display."""

    def test_enter_results_requires_admin(self, client: TestClient, test_tournament: Tournament):
        """Enter results page should require admin privileges."""
        response = client.get(
            f"/admin/tournaments/{test_tournament.id}/enter-results", follow_redirects=False
        )
        assert response.status_code in [302, 303, 307]
        assert "login" in response.headers.get("location", "").lower()

    def test_enter_results_page_displays(
        self, admin_client: TestClient, test_tournament: Tournament
    ):
        """Admin should be able to view enter results page."""
        response = admin_client.get(f"/admin/tournaments/{test_tournament.id}/enter-results")
        assert response.status_code == 200
        assert "Enter Results" in response.text or "Results" in response.text

    def test_enter_results_nonexistent_tournament(self, admin_client: TestClient):
        """Enter results for nonexistent tournament should redirect."""
        response = admin_client.get(
            "/admin/tournaments/99999/enter-results", follow_redirects=False
        )
        assert response.status_code == 303
        assert "admin/tournaments" in response.headers.get("location", "")


class TestIndividualResults:
    """Test individual tournament result entry."""

    def test_save_individual_result_new(
        self,
        admin_client: TestClient,
        db_session: Session,
        test_tournament: Tournament,
        member_user: Angler,
    ):
        """Admin should be able to save new individual result."""
        response = post_with_csrf(
            admin_client,
            f"/admin/tournaments/{test_tournament.id}/results",
            data={
                "angler_id": member_user.id,
                "num_fish": 5,
                "total_weight": 15.5,
                "big_bass_weight": 4.2,
                "dead_fish_penalty": 0.0,
                "disqualified": False,
                "buy_in": False,
                "was_member": True,
            },
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert f"/admin/tournaments/{test_tournament.id}/enter-results" in response.headers.get(
            "location", ""
        )

        # Verify result was created
        result = (
            db_session.query(Result)
            .filter(Result.tournament_id == test_tournament.id, Result.angler_id == member_user.id)
            .first()
        )
        assert result is not None
        assert result.num_fish == 5
        assert result.total_weight is not None and float(result.total_weight) == 15.5
        assert result.big_bass_weight is not None and float(result.big_bass_weight) == 4.2

    def test_save_individual_result_update_existing(
        self,
        admin_client: TestClient,
        db_session: Session,
        test_tournament: Tournament,
        member_user: Angler,
    ):
        """Admin should be able to update existing individual result."""
        # Create initial result
        result = Result(
            tournament_id=test_tournament.id,
            angler_id=member_user.id,
            num_fish=3,
            total_weight=10.0,
            big_bass_weight=3.0,
            disqualified=False,
        )
        db_session.add(result)
        db_session.commit()

        # Update the result
        response = post_with_csrf(
            admin_client,
            f"/admin/tournaments/{test_tournament.id}/results",
            data={
                "angler_id": member_user.id,
                "num_fish": 5,
                "total_weight": 18.0,
                "big_bass_weight": 5.0,
                "dead_fish_penalty": 0.0,
                "disqualified": False,
                "buy_in": False,
                "was_member": True,
            },
            follow_redirects=False,
        )

        assert response.status_code == 303

        # Verify result was updated
        db_session.expire_all()
        updated_result = (
            db_session.query(Result)
            .filter(Result.tournament_id == test_tournament.id, Result.angler_id == member_user.id)
            .first()
        )
        assert updated_result is not None
        assert updated_result.num_fish == 5
        assert updated_result.total_weight is not None and float(updated_result.total_weight) == 18.0

    def test_save_result_with_dead_fish_penalty(
        self,
        admin_client: TestClient,
        db_session: Session,
        test_tournament: Tournament,
        member_user: Angler,
    ):
        """Result should calculate net weight by subtracting dead fish penalty."""
        response = post_with_csrf(
            admin_client,
            f"/admin/tournaments/{test_tournament.id}/results",
            data={
                "angler_id": member_user.id,
                "num_fish": 5,
                "total_weight": 15.0,  # Gross weight
                "big_bass_weight": 4.0,
                "dead_fish_penalty": 1.0,  # Penalty
                "disqualified": False,
                "buy_in": False,
                "was_member": True,
            },
            follow_redirects=False,
        )

        assert response.status_code == 303

        # Verify net weight = gross - penalty
        result = (
            db_session.query(Result)
            .filter(Result.tournament_id == test_tournament.id, Result.angler_id == member_user.id)
            .first()
        )
        assert result is not None
        assert result.total_weight is not None and float(result.total_weight) == 14.0  # 15.0 - 1.0

    def test_save_result_missing_angler_id(
        self, admin_client: TestClient, test_tournament: Tournament
    ):
        """Saving result without angler ID should fail."""
        response = post_with_csrf(
            admin_client,
            f"/admin/tournaments/{test_tournament.id}/results",
            data={
                "num_fish": 5,
                "total_weight": 15.0,
                "big_bass_weight": 4.0,
                "dead_fish_penalty": 0.0,
            },
            follow_redirects=False,
        )

        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    def test_delete_individual_result(
        self,
        admin_client: TestClient,
        db_session: Session,
        test_tournament: Tournament,
        member_user: Angler,
    ):
        """Admin should be able to delete individual result."""
        # Create result
        result = Result(
            tournament_id=test_tournament.id,
            angler_id=member_user.id,
            num_fish=5,
            total_weight=15.0,
            disqualified=False,
        )
        db_session.add(result)
        db_session.commit()
        result_id = result.id

        # Delete the result
        response = post_with_csrf(
            admin_client,
            f"/admin/tournaments/{test_tournament.id}/delete-result/{result_id}",
            data={},
            follow_redirects=False,
        )

        assert response.status_code == 303

        # Verify result was deleted
        db_session.expire_all()
        deleted_result = db_session.query(Result).filter(Result.id == result_id).first()
        assert deleted_result is None


class TestTeamResults:
    """Test team tournament result entry."""

    def test_save_team_result_new(
        self,
        admin_client: TestClient,
        db_session: Session,
        test_tournament: Tournament,
        member_user: Angler,
        admin_user: Angler,
    ):
        """Admin should be able to save new team result."""
        # Create individual results first
        result1 = Result(
            tournament_id=test_tournament.id,
            angler_id=member_user.id,
            num_fish=5,
            total_weight=10.0,
            disqualified=False,
        )
        result2 = Result(
            tournament_id=test_tournament.id,
            angler_id=admin_user.id,
            num_fish=5,
            total_weight=12.0,
            disqualified=False,
        )
        db_session.add_all([result1, result2])
        db_session.commit()

        # Create team result
        response = post_with_csrf(
            admin_client,
            f"/admin/tournaments/{test_tournament.id}/team-results",
            data={
                "angler1_id": member_user.id,
                "angler2_id": admin_user.id,
            },
            follow_redirects=False,
        )

        assert response.status_code == 303

        # Verify team result was created
        team_result = (
            db_session.query(TeamResult)
            .filter(TeamResult.tournament_id == test_tournament.id)
            .first()
        )
        assert team_result is not None
        assert team_result.total_weight is not None and float(team_result.total_weight) == 22.0  # 10.0 + 12.0

    def test_save_team_result_solo_angler(
        self,
        admin_client: TestClient,
        db_session: Session,
        test_tournament: Tournament,
        member_user: Angler,
    ):
        """Admin should be able to save solo angler team result."""
        # Create individual result
        result = Result(
            tournament_id=test_tournament.id,
            angler_id=member_user.id,
            num_fish=5,
            total_weight=10.0,
            disqualified=False,
        )
        db_session.add(result)
        db_session.commit()

        # Create solo team result
        response = post_with_csrf(
            admin_client,
            f"/admin/tournaments/{test_tournament.id}/team-results",
            data={
                "angler1_id": member_user.id,
                "angler2_id": "",  # No second angler
            },
            follow_redirects=False,
        )

        assert response.status_code == 303

        # Verify team result was created with null angler2
        team_result = (
            db_session.query(TeamResult)
            .filter(TeamResult.tournament_id == test_tournament.id)
            .first()
        )
        assert team_result is not None
        assert team_result.angler2_id is None
        assert team_result.total_weight is not None and float(team_result.total_weight) == 10.0

    def test_save_team_result_update_existing(
        self,
        admin_client: TestClient,
        db_session: Session,
        test_tournament: Tournament,
        member_user: Angler,
        admin_user: Angler,
    ):
        """Admin should be able to update existing team result."""
        # Create individual results
        result1 = Result(
            tournament_id=test_tournament.id,
            angler_id=member_user.id,
            num_fish=5,
            total_weight=10.0,
            disqualified=False,
        )
        result2 = Result(
            tournament_id=test_tournament.id,
            angler_id=admin_user.id,
            num_fish=5,
            total_weight=12.0,
            disqualified=False,
        )
        db_session.add_all([result1, result2])
        db_session.commit()

        # Create initial team result
        team_result = TeamResult(
            tournament_id=test_tournament.id,
            angler1_id=member_user.id,
            angler2_id=admin_user.id,
            total_weight=20.0,  # Incorrect weight
        )
        db_session.add(team_result)
        db_session.commit()
        team_id = team_result.id

        # Update the team result (should recalculate weight)
        response = post_with_csrf(
            admin_client,
            f"/admin/tournaments/{test_tournament.id}/team-results",
            data={
                "team_result_id": team_id,
                "angler1_id": member_user.id,
                "angler2_id": admin_user.id,
            },
            follow_redirects=False,
        )

        assert response.status_code == 303

        # Verify weight was recalculated
        db_session.expire_all()
        updated_team = db_session.query(TeamResult).filter(TeamResult.id == team_id).first()
        assert updated_team is not None
        assert updated_team.total_weight is not None and float(updated_team.total_weight) == 22.0  # 10.0 + 12.0

    def test_save_team_result_missing_angler1(
        self, admin_client: TestClient, test_tournament: Tournament
    ):
        """Saving team result without angler1 should fail."""
        response = post_with_csrf(
            admin_client,
            f"/admin/tournaments/{test_tournament.id}/team-results",
            data={
                "angler2_id": 2,
            },
            follow_redirects=False,
        )

        assert response.status_code == 400
        data = response.json()
        assert "error" in data


class TestResultValidation:
    """Test tournament result validation functions."""

    def test_validate_result_success(self):
        """Valid result should pass validation."""
        valid, error = validate_tournament_result(
            num_fish=5, total_weight=15.5, big_bass_weight=4.2, dead_fish_penalty=0, fish_limit=5
        )
        assert valid is True
        assert error is None

    def test_validate_result_negative_fish(self):
        """Negative fish count should fail validation."""
        valid, error = validate_tournament_result(
            num_fish=-1, total_weight=15.0, big_bass_weight=4.0, dead_fish_penalty=0, fish_limit=5
        )
        assert valid is False
        assert "negative" in error.lower()

    def test_validate_result_exceeds_fish_limit(self):
        """Fish count exceeding limit should fail validation."""
        valid, error = validate_tournament_result(
            num_fish=6, total_weight=20.0, big_bass_weight=4.0, dead_fish_penalty=0, fish_limit=5
        )
        assert valid is False
        assert "exceed" in error.lower()

    def test_validate_result_negative_weight(self):
        """Negative total weight should fail validation."""
        valid, error = validate_tournament_result(
            num_fish=5, total_weight=-1.0, big_bass_weight=4.0, dead_fish_penalty=0, fish_limit=5
        )
        assert valid is False
        assert "negative" in error.lower()

    def test_validate_result_excessive_total_weight(self):
        """Excessive total weight should fail validation."""
        valid, error = validate_tournament_result(
            num_fish=5, total_weight=100.0, big_bass_weight=4.0, dead_fish_penalty=0, fish_limit=5
        )
        assert valid is False
        assert "maximum" in error.lower()

    def test_validate_result_big_bass_exceeds_total(self):
        """Big bass weight exceeding total should fail validation."""
        valid, error = validate_tournament_result(
            num_fish=5, total_weight=10.0, big_bass_weight=15.0, dead_fish_penalty=0, fish_limit=5
        )
        assert valid is False
        assert "exceed total" in error.lower()

    def test_validate_result_excessive_big_bass(self):
        """Excessive big bass weight should fail validation."""
        valid, error = validate_tournament_result(
            num_fish=5, total_weight=20.0, big_bass_weight=20.0, dead_fish_penalty=0, fish_limit=5
        )
        assert valid is False
        assert "maximum" in error.lower()

    def test_validate_result_dead_fish_exceeds_caught(self):
        """Dead fish penalty exceeding caught fish should fail."""
        valid, error = validate_tournament_result(
            num_fish=3, total_weight=10.0, big_bass_weight=3.0, dead_fish_penalty=5, fish_limit=5
        )
        assert valid is False
        assert "cannot exceed number of fish" in error.lower()

    def test_validate_result_excessive_avg_weight(self):
        """Excessive average fish weight should fail validation."""
        # Use 3 fish at 35 lbs total = 11.67 lbs avg (exceeds 10 lb max avg)
        valid, error = validate_tournament_result(
            num_fish=3, total_weight=35.0, big_bass_weight=12.0, dead_fish_penalty=0, fish_limit=5
        )
        assert valid is False
        assert "average" in error.lower()

    def test_validate_result_low_avg_weight(self):
        """Very low average fish weight should fail validation."""
        valid, error = validate_tournament_result(
            num_fish=5, total_weight=2.0, big_bass_weight=0.5, dead_fish_penalty=0, fish_limit=5
        )
        assert valid is False
        assert "average" in error.lower()

    def test_sanitize_weight_valid(self):
        """Valid weight string should be sanitized to Decimal."""
        weight = sanitize_weight("15.5")
        assert weight == Decimal("15.5")

    def test_sanitize_weight_with_spaces(self):
        """Weight string with spaces should be trimmed."""
        weight = sanitize_weight("  15.5  ")
        assert weight == Decimal("15.5")

    def test_sanitize_weight_negative_fails(self):
        """Negative weight should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid weight"):
            sanitize_weight("-5.0")

    def test_sanitize_weight_invalid_format(self):
        """Invalid weight format should raise ValueError."""
        with pytest.raises((ValueError, Exception)):
            sanitize_weight("not_a_number")


class TestAutoTeamResultUpdate:
    """Test automatic team result updates when individual results change."""

    def test_individual_result_updates_team_weight(
        self,
        admin_client: TestClient,
        db_session: Session,
        test_tournament: Tournament,
        member_user: Angler,
        admin_user: Angler,
    ):
        """Updating individual result should auto-update team weight."""
        # Create individual results
        result1 = Result(
            tournament_id=test_tournament.id,
            angler_id=member_user.id,
            num_fish=5,
            total_weight=10.0,
            disqualified=False,
        )
        result2 = Result(
            tournament_id=test_tournament.id,
            angler_id=admin_user.id,
            num_fish=5,
            total_weight=12.0,
            disqualified=False,
        )
        db_session.add_all([result1, result2])
        db_session.commit()

        # Create team result
        team_result = TeamResult(
            tournament_id=test_tournament.id,
            angler1_id=member_user.id,
            angler2_id=admin_user.id,
            total_weight=22.0,
        )
        db_session.add(team_result)
        db_session.commit()
        team_id = team_result.id

        # Update member_user's individual result
        post_with_csrf(
            admin_client,
            f"/admin/tournaments/{test_tournament.id}/results",
            data={
                "angler_id": member_user.id,
                "num_fish": 5,
                "total_weight": 15.0,  # Changed from 10.0
                "big_bass_weight": 0.0,
                "dead_fish_penalty": 0.0,
                "disqualified": False,
                "buy_in": False,
                "was_member": True,
            },
            follow_redirects=False,
        )

        # Verify team weight was auto-updated
        db_session.expire_all()
        updated_team = db_session.query(TeamResult).filter(TeamResult.id == team_id).first()
        assert updated_team is not None
        assert updated_team.total_weight is not None and float(updated_team.total_weight) == 27.0  # 15.0 + 12.0
