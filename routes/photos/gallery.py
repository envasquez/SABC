"""Photo gallery routes."""

import os
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse

from core.db_schema import Angler, Photo, Tournament, get_session
from core.helpers.auth import get_current_user, require_member
from core.helpers.logging import get_logger
from core.helpers.response import error_redirect, success_redirect
from routes.dependencies import templates

router = APIRouter()
logger = get_logger(__name__)

# Upload directory configuration
UPLOAD_DIR = "uploads/photos"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


def ensure_upload_dir() -> None:
    """Create upload directory if it doesn't exist."""
    os.makedirs(UPLOAD_DIR, exist_ok=True)


def get_photo_url(filename: str) -> str:
    """Get the URL for a photo."""
    return f"/uploads/photos/{filename}"


def can_upload_photo(user: Dict[str, Any], tournament_id: Optional[int]) -> bool:
    """Check if user can upload a photo for a tournament."""
    if user.get("is_admin"):
        return True
    if tournament_id is None:
        return True  # No limit for non-tournament photos
    with get_session() as session:
        count = (
            session.query(Photo)
            .filter(Photo.angler_id == user["id"], Photo.tournament_id == tournament_id)
            .count()
        )
        return count < 2


def can_delete_photo(user: Dict[str, Any], photo: Photo) -> bool:
    """Check if user can delete a photo."""
    return user.get("is_admin") or photo.angler_id == user["id"]


def can_edit_photo(user: Dict[str, Any], photo: Photo) -> bool:
    """Check if user can edit a photo."""
    return user.get("is_admin") or photo.angler_id == user["id"]


@router.get("/photos")
async def gallery(
    request: Request,
    tournament_id: Optional[int] = None,
    angler_id: Optional[int] = None,
    big_bass: Optional[bool] = None,
) -> Any:
    """Display the photo gallery with optional filters."""
    user = get_current_user(request)

    with get_session() as session:
        query = (
            session.query(Photo, Angler, Tournament)
            .join(Angler, Photo.angler_id == Angler.id)
            .outerjoin(Tournament, Photo.tournament_id == Tournament.id)
        )

        if tournament_id:
            query = query.filter(Photo.tournament_id == tournament_id)
        if angler_id:
            query = query.filter(Photo.angler_id == angler_id)
        if big_bass:
            query = query.filter(Photo.is_big_bass.is_(True))

        results = query.order_by(Photo.uploaded_at.desc()).all()

        photos: List[Dict[str, Any]] = []
        for photo, angler, tournament in results:
            photos.append(
                {
                    "id": photo.id,
                    "url": get_photo_url(photo.filename),
                    "caption": photo.caption,
                    "is_big_bass": photo.is_big_bass,
                    "uploaded_at": photo.uploaded_at,
                    "angler_id": angler.id,
                    "angler_name": angler.name,
                    "tournament_id": tournament.id if tournament else None,
                    "tournament_name": tournament.name if tournament else None,
                    "can_delete": can_delete_photo(user, photo) if user else False,
                    "can_edit": can_edit_photo(user, photo) if user else False,
                }
            )

        # Get filter options
        tournaments = (
            session.query(Tournament)
            .join(Photo, Tournament.id == Photo.tournament_id)
            .distinct()
            .order_by(Tournament.name.desc())
            .all()
        )
        tournament_options = [{"id": t.id, "name": t.name} for t in tournaments]

        anglers = (
            session.query(Angler)
            .join(Photo, Angler.id == Photo.angler_id)
            .distinct()
            .order_by(Angler.name)
            .all()
        )
        angler_options = [{"id": a.id, "name": a.name} for a in anglers]

    return templates.TemplateResponse(
        "photos/gallery.html",
        {
            "request": request,
            "user": user,
            "photos": photos,
            "tournament_options": tournament_options,
            "angler_options": angler_options,
            "selected_tournament": tournament_id,
            "selected_angler": angler_id,
            "selected_big_bass": big_bass,
        },
    )


@router.get("/photos/upload")
async def upload_form(request: Request) -> Any:
    """Display the photo upload form."""
    user = require_member(request)

    with get_session() as session:
        tournaments = (
            session.query(Tournament)
            .filter(Tournament.complete.is_(True))
            .order_by(Tournament.name.desc())
            .all()
        )
        tournament_options = [{"id": t.id, "name": t.name} for t in tournaments]

    return templates.TemplateResponse(
        "photos/upload.html",
        {
            "request": request,
            "user": user,
            "tournament_options": tournament_options,
        },
    )


@router.post("/photos/upload")
async def upload_photo(
    request: Request,
    photo: UploadFile = File(...),
    caption: str = Form(default=""),
    tournament_id: Optional[int] = Form(default=None),
    is_big_bass: bool = Form(default=False),
) -> RedirectResponse:
    """Handle photo upload."""
    user = require_member(request)

    # Validate file extension
    ext = os.path.splitext(photo.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return error_redirect(
            "/photos/upload",
            f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Check upload limit
    if not can_upload_photo(user, tournament_id):
        return error_redirect(
            "/photos/upload",
            "You have reached the upload limit (2 photos per tournament).",
        )

    # Read and validate file size
    contents = await photo.read()
    if len(contents) > MAX_FILE_SIZE:
        return error_redirect(
            "/photos/upload",
            f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)}MB.",
        )

    # Generate unique filename
    filename = f"{uuid.uuid4()}{ext}"
    ensure_upload_dir()
    filepath = os.path.join(UPLOAD_DIR, filename)

    # Save file
    try:
        with open(filepath, "wb") as f:
            f.write(contents)
    except Exception as e:
        logger.error(f"Failed to save photo: {e}")
        return error_redirect("/photos/upload", "Failed to save photo. Please try again.")

    # Create database record
    try:
        with get_session() as session:
            photo_record = Photo(
                angler_id=user["id"],
                tournament_id=tournament_id if tournament_id else None,
                filename=filename,
                caption=caption[:200] if caption else None,
                is_big_bass=is_big_bass,
            )
            session.add(photo_record)
            session.commit()
    except Exception as e:
        logger.error(f"Failed to create photo record: {e}")
        # Clean up file if database insert fails
        if os.path.exists(filepath):
            os.remove(filepath)
        return error_redirect("/photos/upload", "Failed to save photo. Please try again.")

    return success_redirect("/photos", "Photo uploaded successfully!")


@router.post("/photos/{photo_id}/delete")
async def delete_photo(request: Request, photo_id: int) -> RedirectResponse:
    """Delete a photo."""
    user = require_member(request)

    with get_session() as session:
        photo = session.query(Photo).filter(Photo.id == photo_id).first()
        if not photo:
            return error_redirect("/photos", "Photo not found.")

        if not can_delete_photo(user, photo):
            return error_redirect("/photos", "You don't have permission to delete this photo.")

        # Delete file
        filepath = os.path.join(UPLOAD_DIR, photo.filename)
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception as e:
                logger.error(f"Failed to delete photo file: {e}")

        # Delete database record
        session.delete(photo)
        session.commit()

    return success_redirect("/photos", "Photo deleted successfully!")


@router.get("/photos/{photo_id}/edit")
async def edit_photo_form(request: Request, photo_id: int) -> Any:
    """Display the photo edit form."""
    user = require_member(request)

    with get_session() as session:
        photo = session.query(Photo).filter(Photo.id == photo_id).first()
        if not photo:
            return error_redirect("/photos", "Photo not found.")

        if not can_edit_photo(user, photo):
            return error_redirect("/photos", "You don't have permission to edit this photo.")

        tournaments = (
            session.query(Tournament)
            .filter(Tournament.complete.is_(True))
            .order_by(Tournament.name.desc())
            .all()
        )
        tournament_options = [{"id": t.id, "name": t.name} for t in tournaments]

        photo_data = {
            "id": photo.id,
            "url": get_photo_url(photo.filename),
            "caption": photo.caption or "",
            "tournament_id": photo.tournament_id,
            "is_big_bass": photo.is_big_bass,
        }

    return templates.TemplateResponse(
        "photos/edit.html",
        {
            "request": request,
            "user": user,
            "photo": photo_data,
            "tournament_options": tournament_options,
        },
    )


@router.post("/photos/{photo_id}/edit")
async def edit_photo(
    request: Request,
    photo_id: int,
    caption: str = Form(default=""),
    tournament_id: Optional[int] = Form(default=None),
    is_big_bass: bool = Form(default=False),
) -> RedirectResponse:
    """Handle photo edit."""
    user = require_member(request)

    with get_session() as session:
        photo = session.query(Photo).filter(Photo.id == photo_id).first()
        if not photo:
            return error_redirect("/photos", "Photo not found.")

        if not can_edit_photo(user, photo):
            return error_redirect("/photos", "You don't have permission to edit this photo.")

        # Update photo fields
        photo.caption = caption[:200] if caption else None
        photo.tournament_id = tournament_id if tournament_id else None
        photo.is_big_bass = is_big_bass

        session.commit()

    return success_redirect("/photos", "Photo updated successfully!")
