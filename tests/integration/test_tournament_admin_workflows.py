"""Integration tests for tournament administration workflows.

Tests admin-only functionality for managing tournaments and entering results.
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.db_schema import Angler, Event, Lake, Poll, Ramp, Result, TeamResult, Tournament


class TestAdminDashboardAccess:
    """Tests for admin dashboard access."""

    def test_admin_can_access_dashboard(self, admin_client: TestClient):
        """Test that admins can access the admin dashboard."""
        response = admin_client.get("/admin")

        assert response.status_code == 200

    def test_non_admin_cannot_access_dashboard(self, member_client: TestClient):
        """Test that non-admin users cannot access admin dashboard."""
        response = member_client.get("/admin", follow_redirects=False)

        # Should redirect or deny access
        assert response.status_code in [302, 303, 403]

    def test_unauthenticated_cannot_access_dashboard(self, client: TestClient):
        """Test that unauthenticated users cannot access admin dashboard."""
        response = client.get("/admin", follow_redirects=False)

        # Should redirect to login
        assert response.status_code in [302, 303]


class TestTournamentListingAdmin:
    """Tests for admin tournament listing page."""

    def test_admin_can_view_tournaments_list(
        self, admin_client: TestClient, test_tournament: Tournament
    ):
        """Test that admins can view list of tournaments."""
        response = admin_client.get("/admin/tournaments")

        assert response.status_code == 200
        assert test_tournament.name in response.text

    def test_non_admin_cannot_view_tournaments_admin_list(self, member_client: TestClient):
        """Test that non-admins cannot access admin tournaments list."""
        response = member_client.get("/admin/tournaments", follow_redirects=False)

        assert response.status_code in [302, 303, 403]


class TestTournamentResultsEntryAccess:
    """Tests for tournament results entry page access."""

    def test_admin_can_access_results_entry_page(
        self, admin_client: TestClient, test_tournament: Tournament
    ):
        """Test that admins can access tournament results entry page."""
        response = admin_client.get(f"/admin/tournaments/{test_tournament.id}/enter-results")

        assert response.status_code == 200

    def test_non_admin_cannot_access_results_entry(
        self, member_client: TestClient, test_tournament: Tournament
    ):
        """Test that non-admins cannot access results entry page."""
        response = member_client.get(
            f"/admin/tournaments/{test_tournament.id}/enter-results", follow_redirects=False
        )

        assert response.status_code in [302, 303, 403]

    def test_results_entry_page_shows_tournament_info(
        self,
        admin_client: TestClient,
        test_tournament: Tournament,
        test_lake: Lake,
        test_ramp: Ramp,
    ):
        """Test that results entry page displays tournament information."""
        response = admin_client.get(f"/admin/tournaments/{test_tournament.id}/enter-results")

        assert response.status_code == 200
        assert test_tournament.name in response.text
        assert test_lake.display_name in response.text


class TestIndividualResultsEntry:
    """Tests for entering individual tournament results."""

    def test_admin_can_enter_individual_results(
        self,
        admin_client: TestClient,
        test_tournament: Tournament,
        member_user: Angler,
        db_session: Session,
    ):
        """Test that admins can successfully enter individual tournament results."""
        response = admin_client.post(
            f"/admin/tournaments/{test_tournament.id}/individual-results",
            data={
                "angler_id": str(member_user.id),
                "total_weight": "15.75",
                "num_fish": "5",
                "big_bass_weight": "5.25",
                "points": "100",
                "buy_in": "true",
                "disqualified": "false",
            },
            follow_redirects=False,
        )

        # Should redirect after successful entry
        assert response.status_code in [302, 303]

        # Verify result was recorded in database
        result = (
            db_session.query(Result)
            .filter(
                Result.tournament_id == test_tournament.id,
                Result.angler_id == member_user.id,
            )
            .first()
        )
        assert result is not None
        assert result.total_weight is not None
        assert result.big_bass_weight is not None
        assert float(result.total_weight) == 15.75
        assert result.num_fish == 5
        assert float(result.big_bass_weight) == 5.25

    def test_admin_can_enter_zero_fish_result(
        self,
        admin_client: TestClient,
        test_tournament: Tournament,
        member_user: Angler,
        db_session: Session,
    ):
        """Test that admins can enter results for anglers who caught zero fish."""
        response = admin_client.post(
            f"/admin/tournaments/{test_tournament.id}/individual-results",
            data={
                "angler_id": str(member_user.id),
                "total_weight": "0",
                "num_fish": "0",
                "big_bass_weight": "0",
                "points": "0",
                "buy_in": "false",
                "disqualified": "false",
            },
            follow_redirects=False,
        )

        assert response.status_code in [302, 303]

        # Verify result was recorded
        result = (
            db_session.query(Result)
            .filter(
                Result.tournament_id == test_tournament.id,
                Result.angler_id == member_user.id,
            )
            .first()
        )
        assert result is not None
        assert result.total_weight is not None
        assert float(result.total_weight) == 0
        assert result.num_fish == 0

    def test_admin_can_mark_angler_as_disqualified(
        self,
        admin_client: TestClient,
        test_tournament: Tournament,
        member_user: Angler,
        db_session: Session,
    ):
        """Test that admins can mark tournament results as disqualified."""
        response = admin_client.post(
            f"/admin/tournaments/{test_tournament.id}/individual-results",
            data={
                "angler_id": str(member_user.id),
                "total_weight": "10.5",
                "num_fish": "4",
                "big_bass_weight": "3.5",
                "points": "0",
                "buy_in": "true",
                "disqualified": "true",
            },
            follow_redirects=False,
        )

        assert response.status_code in [302, 303]

        # Verify disqualification was recorded
        result = (
            db_session.query(Result)
            .filter(
                Result.tournament_id == test_tournament.id,
                Result.angler_id == member_user.id,
            )
            .first()
        )
        assert result is not None
        assert result.disqualified is True


class TestTeamResultsEntry:
    """Tests for entering team tournament results."""

    def test_admin_can_enter_team_results(
        self,
        admin_client: TestClient,
        test_tournament: Tournament,
        member_user: Angler,
        admin_user: Angler,
        db_session: Session,
    ):
        """Test that admins can successfully enter team tournament results."""
        response = admin_client.post(
            f"/admin/tournaments/{test_tournament.id}/team-results",
            data={
                "angler1_id": str(member_user.id),
                "angler2_id": str(admin_user.id),
                "total_weight": "25.5",
                "num_fish": "10",
                "big_bass_weight": "6.75",
            },
            follow_redirects=False,
        )

        # Should redirect after successful entry
        assert response.status_code in [302, 303]

        # Verify team result was recorded
        team_result = (
            db_session.query(TeamResult)
            .filter(
                TeamResult.tournament_id == test_tournament.id,
                TeamResult.angler1_id == member_user.id,
                TeamResult.angler2_id == admin_user.id,
            )
            .first()
        )
        assert team_result is not None
        assert team_result.total_weight is not None
        assert float(team_result.total_weight) == 25.5


class TestResultsManagement:
    """Tests for managing existing tournament results."""

    def test_admin_can_view_manage_results_page(
        self,
        admin_client: TestClient,
        test_tournament: Tournament,
        member_user: Angler,
        db_session: Session,
    ):
        """Test that admins can view results management page."""
        # Create a result first
        result = Result(
            tournament_id=test_tournament.id,
            angler_id=member_user.id,
            total_weight=12.5,
            num_fish=5,
            big_bass_weight=4.0,
            points=100,
            disqualified=False,
            buy_in=True,
        )
        db_session.add(result)
        db_session.commit()

        response = admin_client.get(f"/admin/tournaments/{test_tournament.id}/manage-results")

        assert response.status_code == 200
        assert member_user.name in response.text

    def test_admin_can_delete_individual_result(
        self,
        admin_client: TestClient,
        test_tournament: Tournament,
        member_user: Angler,
        db_session: Session,
    ):
        """Test that admins can delete tournament results."""
        # Create a result
        result = Result(
            tournament_id=test_tournament.id,
            angler_id=member_user.id,
            total_weight=12.5,
            num_fish=5,
            big_bass_weight=4.0,
            points=100,
            disqualified=False,
            buy_in=True,
        )
        db_session.add(result)
        db_session.commit()
        db_session.refresh(result)

        # Delete the result
        response = admin_client.post(
            f"/admin/tournaments/{test_tournament.id}/delete-result/{result.id}",
            follow_redirects=False,
        )

        assert response.status_code in [302, 303]

        # Verify result was deleted
        deleted_result = db_session.query(Result).filter(Result.id == result.id).first()
        assert deleted_result is None


class TestEventManagement:
    """Tests for event management by admins."""

    def test_admin_can_view_events_list(self, admin_client: TestClient, test_event: Event):
        """Test that admins can view the events list."""
        response = admin_client.get("/admin/events")

        assert response.status_code == 200
        assert test_event.name in response.text

    def test_admin_can_access_create_event_page(self, admin_client: TestClient):
        """Test that admins can access event creation page."""
        response = admin_client.get("/admin/events/create")

        assert response.status_code == 200

    def test_non_admin_cannot_access_event_management(self, member_client: TestClient):
        """Test that non-admins cannot access event management."""
        response = member_client.get("/admin/events", follow_redirects=False)

        assert response.status_code in [302, 303, 403]


class TestLakeAndRampManagement:
    """Tests for lake and ramp management by admins."""

    def test_admin_can_view_lakes_list(self, admin_client: TestClient, test_lake: Lake):
        """Test that admins can view list of lakes."""
        response = admin_client.get("/admin/lakes")

        assert response.status_code == 200
        assert test_lake.display_name in response.text

    def test_admin_can_access_edit_lake_page(self, admin_client: TestClient, test_lake: Lake):
        """Test that admins can access lake editing page."""
        response = admin_client.get(f"/admin/lakes/{test_lake.id}/edit")

        assert response.status_code == 200
        assert test_lake.display_name in response.text

    def test_non_admin_cannot_access_lake_management(self, member_client: TestClient):
        """Test that non-admins cannot access lake management."""
        response = member_client.get("/admin/lakes", follow_redirects=False)

        assert response.status_code in [302, 303, 403]


class TestUserManagement:
    """Tests for user management by admins."""

    def test_admin_can_view_users_list(
        self, admin_client: TestClient, member_user: Angler, regular_user: Angler
    ):
        """Test that admins can view list of all users."""
        response = admin_client.get("/admin/users")

        assert response.status_code == 200
        assert member_user.name in response.text
        assert regular_user.name in response.text

    def test_admin_can_access_edit_user_page(self, admin_client: TestClient, member_user: Angler):
        """Test that admins can access user editing page."""
        response = admin_client.get(f"/admin/users/{member_user.id}/edit")

        assert response.status_code == 200
        assert member_user.name in response.text
        assert member_user.email is not None
        assert member_user.email in response.text

    def test_non_admin_cannot_access_user_management(self, member_client: TestClient):
        """Test that non-admins cannot access user management."""
        response = member_client.get("/admin/users", follow_redirects=False)

        assert response.status_code in [302, 303, 403]


class TestPollManagementByAdmin:
    """Tests for poll management by admins."""

    def test_admin_can_access_create_poll_page(self, admin_client: TestClient):
        """Test that admins can access poll creation page."""
        response = admin_client.get("/admin/polls/create")

        assert response.status_code == 200

    def test_admin_can_access_edit_poll_page(self, admin_client: TestClient, test_poll: Poll):
        """Test that admins can access poll editing page."""
        response = admin_client.get(f"/admin/polls/{test_poll.id}/edit")

        assert response.status_code == 200
        assert test_poll.title in response.text

    def test_non_admin_cannot_access_poll_management(self, member_client: TestClient):
        """Test that non-admins cannot access poll management."""
        response = member_client.get("/admin/polls/create", follow_redirects=False)

        assert response.status_code in [302, 303, 403]


class TestDeadFishPenalties:
    """Tests for dead fish penalty handling in results."""

    def test_admin_can_enter_results_with_dead_fish_penalty(
        self,
        admin_client: TestClient,
        test_tournament: Tournament,
        member_user: Angler,
        db_session: Session,
    ):
        """Test that admins can enter results with dead fish penalties."""
        response = admin_client.post(
            f"/admin/tournaments/{test_tournament.id}/individual-results",
            data={
                "angler_id": str(member_user.id),
                "total_weight": "15.00",
                "num_fish": "5",
                "big_bass_weight": "5.0",
                "dead_fish_penalty": "0.25",  # Quarter pound penalty
                "points": "100",
                "buy_in": "true",
                "disqualified": "false",
            },
            follow_redirects=False,
        )

        assert response.status_code in [302, 303]

        # Verify penalty was recorded
        result = (
            db_session.query(Result)
            .filter(
                Result.tournament_id == test_tournament.id,
                Result.angler_id == member_user.id,
            )
            .first()
        )
        assert result is not None
        assert result.dead_fish_penalty is not None
        assert float(result.dead_fish_penalty) == 0.25

    def test_results_with_penalty_show_net_weight(
        self,
        admin_client: TestClient,
        test_tournament: Tournament,
        member_user: Angler,
        db_session: Session,
    ):
        """Test that results with dead fish penalties display net weight correctly."""
        # Enter result with penalty
        result = Result(
            tournament_id=test_tournament.id,
            angler_id=member_user.id,
            total_weight=15.00,
            num_fish=5,
            big_bass_weight=5.0,
            dead_fish_penalty=0.50,  # Half pound penalty
            points=100,
            disqualified=False,
            buy_in=True,
        )
        db_session.add(result)
        db_session.commit()

        # View tournament results
        response = admin_client.get(f"/tournaments/{test_tournament.id}")

        assert response.status_code == 200
        # Net weight should be 14.50 (15.00 - 0.50)
        assert "14.5" in response.text or "14.50" in response.text
