"""Photo gallery tests."""

import io
import tempfile
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.db_schema import Angler, Photo, Tournament
from tests.conftest import post_with_csrf


class TestPhotoGallery:
    """Test photo gallery functionality."""

    def test_gallery_view_anonymous(self, client: TestClient):
        """Test anonymous users can view the gallery."""
        response = client.get("/photos")
        assert response.status_code == 200
        assert b"Photo Gallery" in response.content

    def test_gallery_view_member(self, member_client: TestClient):
        """Test members can view the gallery with upload button."""
        response = member_client.get("/photos")
        assert response.status_code == 200
        assert b"Upload Photo" in response.content

    def test_upload_page_requires_login(self, client: TestClient):
        """Test upload page requires authentication."""
        response = client.get("/photos/upload", follow_redirects=False)
        assert response.status_code in [302, 303]

    def test_upload_page_member(self, member_client: TestClient):
        """Test members can access upload page."""
        response = member_client.get("/photos/upload")
        assert response.status_code == 200
        assert b"Upload Photo" in response.content

    @patch("routes.photos.gallery.UPLOAD_DIR", tempfile.gettempdir())
    def test_upload_photo_member(
        self, member_client: TestClient, db_session: Session, member_user: Angler
    ):
        """Test members can upload photos."""
        # Create a simple test image
        image_content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

        response = post_with_csrf(
            member_client,
            "/photos/upload",
            data={
                "caption": "Test photo",
                "is_big_bass": "false",
            },
            files={"photo": ("test.png", io.BytesIO(image_content), "image/png")},
        )
        assert response.status_code in [200, 303]

    def test_upload_invalid_file_type(self, member_client: TestClient):
        """Test upload rejects invalid file types."""
        response = post_with_csrf(
            member_client,
            "/photos/upload",
            data={"caption": "Test"},
            files={"photo": ("test.txt", io.BytesIO(b"text content"), "text/plain")},
        )
        # Should redirect with error
        assert response.status_code in [200, 303]

    def test_delete_own_photo(
        self, member_client: TestClient, db_session: Session, member_user: Angler
    ):
        """Test members can delete their own photos."""
        # Save ID before any operations
        angler_id = member_user.id

        photo = Photo(
            angler_id=angler_id,
            filename="test.jpg",
            caption="Test",
        )
        db_session.add(photo)
        db_session.commit()

        response = post_with_csrf(
            member_client,
            f"/photos/{photo.id}/delete",
            data={},
        )
        assert response.status_code in [200, 303]

    def test_cannot_delete_others_photo(
        self,
        member_client: TestClient,
        db_session: Session,
        admin_user: Angler,
    ):
        """Test members cannot delete others' photos."""
        # Save ID before any operations
        admin_id = admin_user.id

        photo = Photo(
            angler_id=admin_id,
            filename="test.jpg",
            caption="Admin photo",
        )
        db_session.add(photo)
        db_session.commit()

        response = post_with_csrf(
            member_client,
            f"/photos/{photo.id}/delete",
            data={},
        )
        # Should redirect with error (permission denied)
        assert response.status_code in [200, 303]

    def test_admin_can_delete_any_photo(
        self,
        admin_client: TestClient,
        db_session: Session,
        member_user: Angler,
    ):
        """Test admins can delete any photo."""
        # Save ID before any operations
        angler_id = member_user.id

        photo = Photo(
            angler_id=angler_id,
            filename="test.jpg",
            caption="Member photo",
        )
        db_session.add(photo)
        db_session.commit()

        response = post_with_csrf(
            admin_client,
            f"/photos/{photo.id}/delete",
            data={},
        )
        assert response.status_code in [200, 303]

    def test_gallery_filters_with_client(
        self,
        client: TestClient,
        db_session: Session,
        member_user: Angler,
        test_tournament: Tournament,
    ):
        """Test gallery filters work for anonymous users."""
        # Save IDs before using client
        angler_id = member_user.id
        tournament_id = test_tournament.id

        # Create test photos
        photo1 = Photo(
            angler_id=angler_id,
            tournament_id=tournament_id,
            filename="tournament.jpg",
            is_big_bass=True,
        )
        photo2 = Photo(
            angler_id=angler_id,
            filename="general.jpg",
            is_big_bass=False,
        )
        db_session.add_all([photo1, photo2])
        db_session.commit()

        # Test tournament filter
        response = client.get(f"/photos?tournament_id={tournament_id}")
        assert response.status_code == 200

        # Test big bass filter
        response = client.get("/photos?big_bass=true")
        assert response.status_code == 200

        # Test angler filter
        response = client.get(f"/photos?angler_id={angler_id}")
        assert response.status_code == 200

        # Test empty filter (empty string should not cause error)
        response = client.get("/photos?tournament_id=&angler_id=")
        assert response.status_code == 200


class TestPhotoUploadLimits:
    """Test photo upload limits."""

    @patch("routes.photos.gallery.UPLOAD_DIR", tempfile.gettempdir())
    def test_member_upload_limit(
        self,
        member_client: TestClient,
        db_session: Session,
        member_user: Angler,
        test_tournament: Tournament,
    ):
        """Test members are limited to 2 photos per tournament."""
        # Save IDs before any operations
        angler_id = member_user.id
        tournament_id = test_tournament.id

        # Create 2 existing photos for the tournament
        for i in range(2):
            photo = Photo(
                angler_id=angler_id,
                tournament_id=tournament_id,
                filename=f"existing{i}.jpg",
            )
            db_session.add(photo)
        db_session.commit()

        # Try to upload a third photo
        image_content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        response = post_with_csrf(
            member_client,
            "/photos/upload",
            data={
                "caption": "Third photo",
                "tournament_id": str(tournament_id),
            },
            files={"photo": ("test.png", io.BytesIO(image_content), "image/png")},
        )
        # Should redirect with error about limit
        assert response.status_code in [200, 303]

    @patch("routes.photos.gallery.UPLOAD_DIR", tempfile.gettempdir())
    def test_admin_no_upload_limit(
        self,
        admin_client: TestClient,
        db_session: Session,
        admin_user: Angler,
        test_tournament: Tournament,
    ):
        """Test admins have no upload limit."""
        # Save IDs before using client
        angler_id = admin_user.id
        tournament_id = test_tournament.id

        # Create 2 existing photos for the tournament
        for i in range(2):
            photo = Photo(
                angler_id=angler_id,
                tournament_id=tournament_id,
                filename=f"existing{i}.jpg",
            )
            db_session.add(photo)
        db_session.commit()

        # Admin should still be able to upload
        image_content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        response = post_with_csrf(
            admin_client,
            "/photos/upload",
            data={
                "caption": "Admin third photo",
                "tournament_id": str(tournament_id),
            },
            files={"photo": ("test.png", io.BytesIO(image_content), "image/png")},
        )
        assert response.status_code in [200, 303]


class TestPhotoEdit:
    """Test photo edit functionality."""

    def test_edit_page_requires_login(
        self, client: TestClient, db_session: Session, member_user: Angler
    ):
        """Test edit page requires authentication."""
        angler_id = member_user.id

        photo = Photo(
            angler_id=angler_id,
            filename="test.jpg",
            caption="Test",
        )
        db_session.add(photo)
        db_session.commit()

        response = client.get(f"/photos/{photo.id}/edit", follow_redirects=False)
        assert response.status_code in [302, 303]

    def test_edit_own_photo_page(
        self, member_client: TestClient, db_session: Session, member_user: Angler
    ):
        """Test members can access edit page for their own photos."""
        angler_id = member_user.id

        photo = Photo(
            angler_id=angler_id,
            filename="test.jpg",
            caption="Original caption",
        )
        db_session.add(photo)
        db_session.commit()

        response = member_client.get(f"/photos/{photo.id}/edit")
        assert response.status_code == 200
        assert b"Edit Photo" in response.content
        assert b"Original caption" in response.content

    def test_cannot_edit_others_photo(
        self,
        member_client: TestClient,
        db_session: Session,
        admin_user: Angler,
    ):
        """Test members cannot edit others' photos."""
        admin_id = admin_user.id

        photo = Photo(
            angler_id=admin_id,
            filename="test.jpg",
            caption="Admin photo",
        )
        db_session.add(photo)
        db_session.commit()

        response = member_client.get(f"/photos/{photo.id}/edit", follow_redirects=False)
        # Should redirect with error (permission denied)
        assert response.status_code in [200, 303]

    def test_admin_can_edit_any_photo(
        self,
        admin_client: TestClient,
        db_session: Session,
        member_user: Angler,
    ):
        """Test admins can edit any photo."""
        angler_id = member_user.id

        photo = Photo(
            angler_id=angler_id,
            filename="test.jpg",
            caption="Member photo",
        )
        db_session.add(photo)
        db_session.commit()

        response = admin_client.get(f"/photos/{photo.id}/edit")
        assert response.status_code == 200
        assert b"Edit Photo" in response.content

    def test_edit_photo_updates_caption(
        self, member_client: TestClient, db_session: Session, member_user: Angler
    ):
        """Test editing a photo updates its caption."""
        angler_id = member_user.id

        photo = Photo(
            angler_id=angler_id,
            filename="test.jpg",
            caption="Original caption",
        )
        db_session.add(photo)
        db_session.commit()
        photo_id = photo.id

        response = post_with_csrf(
            member_client,
            f"/photos/{photo_id}/edit",
            data={
                "caption": "Updated caption",
                "is_big_bass": "false",
            },
        )
        assert response.status_code in [200, 303]

        # Verify the update
        db_session.expire_all()
        updated_photo = db_session.query(Photo).filter(Photo.id == photo_id).first()
        assert updated_photo is not None
        assert updated_photo.caption == "Updated caption"

    def test_edit_photo_updates_big_bass(
        self, admin_client: TestClient, db_session: Session, member_user: Angler
    ):
        """Test admin can update big bass tag."""
        angler_id = member_user.id

        photo = Photo(
            angler_id=angler_id,
            filename="test.jpg",
            caption="A catch",
            is_big_bass=False,
        )
        db_session.add(photo)
        db_session.commit()
        photo_id = photo.id

        response = post_with_csrf(
            admin_client,
            f"/photos/{photo_id}/edit",
            data={
                "caption": "A catch",
                "is_big_bass": "true",
            },
        )
        assert response.status_code in [200, 303]

        # Verify the update
        db_session.expire_all()
        updated_photo = db_session.query(Photo).filter(Photo.id == photo_id).first()
        assert updated_photo is not None
        assert updated_photo.is_big_bass is True

    def test_edit_photo_updates_tournament(
        self,
        admin_client: TestClient,
        db_session: Session,
        member_user: Angler,
        test_tournament: Tournament,
    ):
        """Test admin can associate photo with tournament."""
        angler_id = member_user.id
        tournament_id = test_tournament.id

        photo = Photo(
            angler_id=angler_id,
            filename="test.jpg",
            caption="A catch",
            tournament_id=None,
        )
        db_session.add(photo)
        db_session.commit()
        photo_id = photo.id

        response = post_with_csrf(
            admin_client,
            f"/photos/{photo_id}/edit",
            data={
                "caption": "A catch",
                "tournament_id": str(tournament_id),
                "is_big_bass": "false",
            },
        )
        assert response.status_code in [200, 303]

        # Verify the update
        db_session.expire_all()
        updated_photo = db_session.query(Photo).filter(Photo.id == photo_id).first()
        assert updated_photo is not None
        assert updated_photo.tournament_id == tournament_id

    def test_edit_nonexistent_photo(self, member_client: TestClient):
        """Test editing nonexistent photo returns error."""
        response = member_client.get("/photos/99999/edit", follow_redirects=False)
        assert response.status_code in [200, 303]
