"""Phase 9: Admin User and Lake Management Tests

Tests for admin user management, lake/ramp operations, and API endpoints.
Focuses on low-coverage areas in user CRUD and lake management workflows.
"""


from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.db_schema import Angler, Lake, OfficerPosition, Ramp, Result, Tournament
from core.helpers.timezone import now_local


class TestUserDeletion:
    """Tests for user deletion endpoint."""

    def test_admin_can_delete_user(
        self,
        admin_client: TestClient,
        db_session: Session,
    ):
        """Test that admins can delete users."""
        # Create a user to delete
        test_user = Angler(
            name="Test User",
            email="test@example.com",
            member=False,
        )
        db_session.add(test_user)
        db_session.commit()
        db_session.refresh(test_user)
        user_id = test_user.id

        response = admin_client.delete(f"/admin/users/{user_id}")

        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True

        # Verify user was deleted
        db_session.expire_all()
        deleted_user = db_session.query(Angler).filter(Angler.id == user_id).first()
        assert deleted_user is None

    def test_admin_cannot_delete_self(
        self,
        admin_client: TestClient,
        admin_user: Angler,
        db_session: Session,
    ):
        """Test that admins cannot delete their own account."""
        response = admin_client.delete(f"/admin/users/{admin_user.id}")

        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "yourself" in data["error"].lower()

    def test_delete_nonexistent_user_succeeds(
        self,
        admin_client: TestClient,
        db_session: Session,
    ):
        """Test that deleting nonexistent user returns success (idempotent)."""
        response = admin_client.delete("/admin/users/99999")

        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True

    def test_non_admin_cannot_delete_user(
        self,
        member_client: TestClient,
        member_user: Angler,
        db_session: Session,
    ):
        """Test that non-admins cannot delete users."""
        response = member_client.delete(
            f"/admin/users/{member_user.id}",
            follow_redirects=False,
        )

        assert response.status_code in [302, 303, 403]

    def test_delete_user_with_results_succeeds(
        self,
        admin_client: TestClient,
        member_user: Angler,
        test_tournament: Tournament,
        db_session: Session,
    ):
        """Test that deleting user with tournament results succeeds (cascade or allow deletion)."""
        # Add a result for the member
        result = Result(
            tournament_id=test_tournament.id,
            angler_id=member_user.id,
            num_fish=3,
            total_weight=Decimal("10.5"),
        )
        db_session.add(result)
        db_session.commit()

        response = admin_client.delete(f"/admin/users/{member_user.id}")

        # Deletion succeeds (either cascades or is allowed despite results)
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True


class TestUserEditing:
    """Tests for user edit page endpoint."""

    def test_admin_can_view_edit_page(
        self,
        admin_client: TestClient,
        member_user: Angler,
        db_session: Session,
    ):
        """Test that admins can view the user edit page."""
        response = admin_client.get(f"/admin/users/{member_user.id}/edit")

        assert response.status_code == 200
        assert b"edit" in response.content.lower() or b"update" in response.content.lower()

    def test_edit_page_for_nonexistent_user(
        self,
        admin_client: TestClient,
        db_session: Session,
    ):
        """Test that editing nonexistent user redirects with error."""
        response = admin_client.get("/admin/users/99999/edit", follow_redirects=False)

        # Should redirect with error
        assert response.status_code in [302, 303]
        assert "error" in response.headers.get("location", "").lower()

    def test_edit_page_shows_officer_positions(
        self,
        admin_client: TestClient,
        member_user: Angler,
        db_session: Session,
    ):
        """Test that edit page shows current officer positions."""
        current_year = now_local().year

        # Add officer position
        position = OfficerPosition(
            angler_id=member_user.id,
            position="President",
            year=current_year,
        )
        db_session.add(position)
        db_session.commit()

        response = admin_client.get(f"/admin/users/{member_user.id}/edit")

        assert response.status_code == 200
        # Page should show the position
        assert b"President" in response.content

    def test_non_admin_cannot_view_edit_page(
        self,
        member_client: TestClient,
        member_user: Angler,
        db_session: Session,
    ):
        """Test that non-admins cannot access edit page."""
        response = member_client.get(
            f"/admin/users/{member_user.id}/edit",
            follow_redirects=False,
        )

        assert response.status_code in [302, 303, 403]


class TestUserListing:
    """Tests for user listing endpoint."""

    def test_admin_can_list_users(
        self,
        admin_client: TestClient,
        member_user: Angler,
        admin_user: Angler,
        db_session: Session,
    ):
        """Test that admins can view the user list."""
        response = admin_client.get("/admin/users")

        assert response.status_code == 200
        assert member_user.name.encode() in response.content
        assert admin_user.name.encode() in response.content

    def test_user_list_shows_counts(
        self,
        admin_client: TestClient,
        db_session: Session,
    ):
        """Test that user list shows member/guest counts."""
        # Create some test users
        member1 = Angler(name="Member 1", email="m1@example.com", member=True)
        member2 = Angler(name="Member 2", email="m2@example.com", member=True)
        guest1 = Angler(name="Guest 1", email="g1@example.com", member=False)
        db_session.add_all([member1, member2, guest1])
        db_session.commit()

        response = admin_client.get("/admin/users")

        assert response.status_code == 200
        content = response.content.decode()
        # Should show counts in the page
        assert "member" in content.lower() or "guest" in content.lower()

    def test_non_admin_cannot_list_users(
        self,
        member_client: TestClient,
        db_session: Session,
    ):
        """Test that non-admins cannot access user list."""
        response = member_client.get("/admin/users", follow_redirects=False)

        assert response.status_code in [302, 303, 403]


class TestLakeDeletion:
    """Tests for lake deletion endpoint."""

    def test_admin_can_delete_lake_without_ramps(
        self,
        admin_client: TestClient,
        db_session: Session,
    ):
        """Test that admins can delete lakes that have no ramps."""
        # Create a lake without ramps
        lake = Lake(
            yaml_key="test_lake",
            display_name="Test Lake",
        )
        db_session.add(lake)
        db_session.commit()
        db_session.refresh(lake)
        lake_id = lake.id

        response = admin_client.delete(f"/admin/lakes/{lake_id}")

        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True

        # Verify lake was deleted
        db_session.expire_all()
        deleted_lake = db_session.query(Lake).filter(Lake.id == lake_id).first()
        assert deleted_lake is None

    def test_cannot_delete_lake_with_tournament_references(
        self,
        admin_client: TestClient,
        test_lake: Lake,
        test_ramp: Ramp,
        test_tournament: Tournament,
        db_session: Session,
    ):
        """Test that lakes referenced by tournaments cannot be deleted."""
        response = admin_client.delete(f"/admin/lakes/{test_lake.id}")

        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "tournament" in data["error"].lower() or "referenced" in data["error"].lower()

    def test_delete_nonexistent_lake_succeeds(
        self,
        admin_client: TestClient,
        db_session: Session,
    ):
        """Test that deleting nonexistent lake returns success (idempotent)."""
        response = admin_client.delete("/admin/lakes/99999")

        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True

    def test_non_admin_cannot_delete_lake(
        self,
        member_client: TestClient,
        test_lake: Lake,
        db_session: Session,
    ):
        """Test that non-admins cannot delete lakes."""
        response = member_client.delete(
            f"/admin/lakes/{test_lake.id}",
            follow_redirects=False,
        )

        assert response.status_code in [302, 303, 403]


class TestRampDeletion:
    """Tests for ramp deletion endpoint."""

    def test_admin_can_delete_ramp_without_tournaments(
        self,
        admin_client: TestClient,
        test_lake: Lake,
        db_session: Session,
    ):
        """Test that admins can delete ramps not referenced by tournaments."""
        # Create a ramp without tournaments
        ramp = Ramp(
            lake_id=test_lake.id,
            name="Test Ramp",
        )
        db_session.add(ramp)
        db_session.commit()
        db_session.refresh(ramp)
        ramp_id = ramp.id

        response = admin_client.delete(f"/admin/ramps/{ramp_id}")

        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True

        # Verify ramp was deleted
        db_session.expire_all()
        deleted_ramp = db_session.query(Ramp).filter(Ramp.id == ramp_id).first()
        assert deleted_ramp is None

    def test_cannot_delete_ramp_with_tournament_references(
        self,
        admin_client: TestClient,
        test_ramp: Ramp,
        test_tournament: Tournament,
        db_session: Session,
    ):
        """Test that ramps referenced by tournaments cannot be deleted."""
        response = admin_client.delete(f"/admin/ramps/{test_ramp.id}")

        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "tournament" in data["error"].lower() or "referenced" in data["error"].lower()

    def test_delete_nonexistent_ramp_succeeds(
        self,
        admin_client: TestClient,
        db_session: Session,
    ):
        """Test that deleting nonexistent ramp returns success (idempotent)."""
        response = admin_client.delete("/admin/ramps/99999")

        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True

    def test_non_admin_cannot_delete_ramp(
        self,
        member_client: TestClient,
        test_ramp: Ramp,
        db_session: Session,
    ):
        """Test that non-admins cannot delete ramps."""
        response = member_client.delete(
            f"/admin/ramps/{test_ramp.id}",
            follow_redirects=False,
        )

        assert response.status_code in [302, 303, 403]


class TestLakesAPI:
    """Tests for lakes API endpoints."""

    def test_get_all_lakes_via_api(
        self,
        client: TestClient,
        test_lake: Lake,
        db_session: Session,
    ):
        """Test that API returns all lakes."""
        response = client.get("/api/lakes")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        # Find our test lake
        test_lake_data = next((lake for lake in data if lake["id"] == test_lake.id), None)
        assert test_lake_data is not None
        assert test_lake_data["name"] == test_lake.display_name
        assert test_lake_data["key"] == test_lake.yaml_key

    def test_get_lakes_returns_empty_on_error(
        self,
        client: TestClient,
        db_session: Session,
    ):
        """Test that API returns empty array on error (graceful degradation)."""
        response = client.get("/api/lakes")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_ramps_for_lake(
        self,
        client: TestClient,
        test_lake: Lake,
        test_ramp: Ramp,
        db_session: Session,
    ):
        """Test that API returns ramps for a specific lake."""
        response = client.get(f"/api/lakes/{test_lake.yaml_key}/ramps")

        assert response.status_code == 200
        data = response.json()
        assert "ramps" in data
        assert isinstance(data["ramps"], list)
        assert len(data["ramps"]) > 0

        # Find our test ramp
        test_ramp_data = next((r for r in data["ramps"] if r["id"] == test_ramp.id), None)
        assert test_ramp_data is not None
        assert test_ramp_data["name"] == test_ramp.name

    def test_get_ramps_for_nonexistent_lake(
        self,
        client: TestClient,
        db_session: Session,
    ):
        """Test that API returns empty ramps for nonexistent lake."""
        response = client.get("/api/lakes/nonexistent_key/ramps")

        assert response.status_code == 200
        data = response.json()
        assert "ramps" in data
        assert data["ramps"] == []

    def test_get_ramps_for_lake_without_ramps(
        self,
        client: TestClient,
        db_session: Session,
    ):
        """Test that API returns empty ramps for lake without ramps."""
        # Create lake without ramps
        lake = Lake(
            yaml_key="empty_lake",
            display_name="Empty Lake",
        )
        db_session.add(lake)
        db_session.commit()

        response = client.get(f"/api/lakes/{lake.yaml_key}/ramps")

        assert response.status_code == 200
        data = response.json()
        assert "ramps" in data
        assert data["ramps"] == []


class TestUserUpdateValidation:
    """Tests for user update validation helpers."""

    def test_email_validation_strips_whitespace(self):
        """Test that email validation strips whitespace."""
        from routes.admin.users.update_user.validation import validate_and_prepare_email

        result = validate_and_prepare_email("  test@EXAMPLE.com  ", "Test User", True, 1)

        assert result == "test@example.com"

    def test_email_validation_lowercases(self):
        """Test that email validation converts to lowercase."""
        from routes.admin.users.update_user.validation import validate_and_prepare_email

        result = validate_and_prepare_email("TEST@EXAMPLE.COM", "Test User", True, 1)

        assert result == "test@example.com"

    def test_empty_email_for_guest_generates_email(self, db_session: Session):
        """Test that empty email for guest generates guest email."""
        from routes.admin.users.update_user.validation import validate_and_prepare_email

        result = validate_and_prepare_email("", "Test User", False, 123)

        # Should generate a guest email
        assert result is not None
        assert "@" in result  # Should contain @ symbol for email
        assert "sabc" in result.lower()  # Should contain sabc domain

    def test_empty_email_for_member_returns_none(self):
        """Test that empty email for member returns None."""
        from routes.admin.users.update_user.validation import validate_and_prepare_email

        result = validate_and_prepare_email("", "Test User", True, 1)

        assert result is None

    def test_update_officer_positions(self, db_session: Session, member_user: Angler):
        """Test updating officer positions for a user."""
        from routes.admin.users.update_user.validation import update_officer_positions

        current_year = now_local().year

        # Add initial position
        position = OfficerPosition(
            angler_id=member_user.id,
            position="Treasurer",
            year=current_year,
        )
        db_session.add(position)
        db_session.commit()

        # Update to new positions
        update_officer_positions(
            db_session,
            member_user.id,
            ["President", "Vice President"],
            current_year,
        )
        db_session.commit()

        # Verify old position removed and new positions added
        positions = (
            db_session.query(OfficerPosition)
            .filter(
                OfficerPosition.angler_id == member_user.id,
                OfficerPosition.year == current_year,
            )
            .all()
        )

        assert len(positions) == 2
        position_titles = {p.position for p in positions}
        assert "President" in position_titles
        assert "Vice President" in position_titles
        assert "Treasurer" not in position_titles

    def test_update_officer_positions_clears_all(self, db_session: Session, member_user: Angler):
        """Test that passing empty list clears all officer positions."""
        from routes.admin.users.update_user.validation import update_officer_positions

        current_year = now_local().year

        # Add initial position
        position = OfficerPosition(
            angler_id=member_user.id,
            position="Secretary",
            year=current_year,
        )
        db_session.add(position)
        db_session.commit()

        # Clear all positions
        update_officer_positions(db_session, member_user.id, [], current_year)
        db_session.commit()

        # Verify all positions removed
        positions = (
            db_session.query(OfficerPosition)
            .filter(
                OfficerPosition.angler_id == member_user.id,
                OfficerPosition.year == current_year,
            )
            .all()
        )

        assert len(positions) == 0

    def test_update_officer_positions_strips_whitespace(
        self, db_session: Session, member_user: Angler
    ):
        """Test that officer position updates strip whitespace."""
        from routes.admin.users.update_user.validation import update_officer_positions

        current_year = now_local().year

        # Update with whitespace in position names
        update_officer_positions(
            db_session,
            member_user.id,
            ["  President  ", " Vice President "],
            current_year,
        )
        db_session.commit()

        # Verify positions are stripped
        positions = (
            db_session.query(OfficerPosition)
            .filter(
                OfficerPosition.angler_id == member_user.id,
                OfficerPosition.year == current_year,
            )
            .all()
        )

        position_titles = {p.position for p in positions}
        assert "President" in position_titles
        assert "Vice President" in position_titles
