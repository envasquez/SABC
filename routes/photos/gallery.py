"""Photo gallery routes."""

import io
import os
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse
from PIL import Image, ImageOps
from sqlalchemy import or_

from core.db_schema import Angler, Event, Photo, TeamResult, Tournament, get_session
from core.helpers.auth import get_current_user, require_member
from core.helpers.logging import get_logger
from core.helpers.response import error_redirect, success_redirect
from routes.dependencies import templates

router = APIRouter()
logger = get_logger(__name__)

# Upload directory configuration
UPLOAD_DIR = "uploads/photos"
THUMBNAIL_DIR = "uploads/photos/thumbnails"
PLACEHOLDER_DIR = "uploads/photos/placeholders"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
THUMBNAIL_SIZE = (200, 200)  # Match display size for optimal performance
PLACEHOLDER_SIZE = (20, 20)  # Tiny blur placeholder for instant loading
WEBP_QUALITY = 80  # Quality for WebP compression (smaller than JPEG at same quality)
PHOTOS_PER_PAGE = 24  # Photos per page for pagination


def ensure_upload_dir() -> None:
    """Create upload directories if they don't exist."""
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(THUMBNAIL_DIR, exist_ok=True)
    os.makedirs(PLACEHOLDER_DIR, exist_ok=True)


def get_photo_url(filename: str) -> str:
    """Get the URL for a photo."""
    return f"/uploads/photos/{filename}"


def get_thumbnail_url(filename: str) -> str:
    """Get the URL for a photo thumbnail."""
    return f"/uploads/photos/thumbnails/{filename}"


def get_placeholder_url(filename: str) -> str:
    """Get the URL for a blur placeholder."""
    return f"/uploads/photos/placeholders/{filename}"


def generate_placeholder(contents: bytes, filename: str) -> Optional[str]:
    """
    Generate a tiny blur placeholder for instant loading.

    Args:
        contents: Original image bytes
        filename: Target filename for placeholder

    Returns:
        Placeholder filename if successful, None otherwise
    """
    try:
        original = Image.open(io.BytesIO(contents))

        # Apply EXIF orientation (fixes rotated phone photos)
        transposed = ImageOps.exif_transpose(original)
        if transposed is not original:
            original.close()

        # Convert to RGB if necessary
        if transposed.mode in ("RGBA", "P"):
            img = transposed.convert("RGB")
            transposed.close()
        else:
            img = transposed

        # Create tiny placeholder (will be scaled up with CSS blur)
        img.thumbnail(PLACEHOLDER_SIZE, Image.Resampling.LANCZOS)

        # Save as WebP with low quality (tiny file, ~500 bytes)
        placeholder_filename = os.path.splitext(filename)[0] + ".webp"
        placeholder_path = os.path.join(PLACEHOLDER_DIR, placeholder_filename)

        img.save(placeholder_path, "WEBP", quality=20, method=6)
        logger.debug(f"Placeholder generated: {placeholder_filename}")

        return placeholder_filename
    except Exception as e:
        logger.error(f"Failed to generate placeholder: {e}")
        return None


def generate_thumbnail(contents: bytes, filename: str) -> tuple[Optional[str], Optional[str]]:
    """
    Generate a WebP thumbnail and blur placeholder from image contents.

    Args:
        contents: Original image bytes
        filename: Target filename for thumbnail

    Returns:
        Tuple of (thumbnail_filename, placeholder_filename) - either may be None
    """
    thumb_filename = None
    placeholder_filename = None

    try:
        # Open image from bytes
        original = Image.open(io.BytesIO(contents))

        # Apply EXIF orientation (fixes rotated phone photos)
        transposed = ImageOps.exif_transpose(original)
        if transposed is not original:
            original.close()

        # Convert to RGB if necessary (for PNG with transparency, etc.)
        if transposed.mode in ("RGBA", "P"):
            img = transposed.convert("RGB")
            transposed.close()
        else:
            img = transposed

        # Calculate thumbnail size maintaining aspect ratio
        img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

        # Save thumbnail as WebP (30% smaller than JPEG at same quality)
        thumb_filename = os.path.splitext(filename)[0] + ".webp"
        thumb_path = os.path.join(THUMBNAIL_DIR, thumb_filename)

        img.save(thumb_path, "WEBP", quality=WEBP_QUALITY, method=4)
        logger.info(f"Thumbnail generated: {thumb_filename}")

        # Generate blur placeholder
        placeholder_filename = generate_placeholder(contents, filename)

    except Exception as e:
        logger.error(f"Failed to generate thumbnail: {e}")

    return thumb_filename, placeholder_filename


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


def build_photo_query(
    session: Any,
    tournament_id_int: Optional[int],
    angler_id_int: Optional[int],
    big_bass_bool: Optional[bool],
) -> Any:
    """Build the base query for photos with filters."""
    query = (
        session.query(Photo, Angler, Tournament)
        .join(Angler, Photo.angler_id == Angler.id)
        .outerjoin(Tournament, Photo.tournament_id == Tournament.id)
    )

    if tournament_id_int:
        query = query.filter(Photo.tournament_id == tournament_id_int)
    if angler_id_int:
        query = query.filter(Photo.angler_id == angler_id_int)
    if big_bass_bool:
        query = query.filter(Photo.is_big_bass.is_(True))

    return query.order_by(Photo.uploaded_at.desc())


def photo_to_dict(
    photo: Photo,
    angler: Angler,
    tournament: Optional[Tournament],
    user: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Convert photo model to dict for template."""
    # Use thumbnail if available, otherwise fall back to original
    thumb_filename = photo.thumbnail_filename
    if thumb_filename:
        thumbnail_url = get_thumbnail_url(thumb_filename)
    else:
        thumbnail_url = get_photo_url(photo.filename)

    # Get placeholder URL for blur-up loading
    placeholder_url = None
    if photo.placeholder_filename:
        placeholder_url = get_placeholder_url(photo.placeholder_filename)

    return {
        "id": photo.id,
        "url": get_photo_url(photo.filename),
        "thumbnail_url": thumbnail_url,
        "placeholder_url": placeholder_url,
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


@router.get("/photos")
async def gallery(
    request: Request,
    tournament_id: Optional[str] = None,
    angler_id: Optional[str] = None,
    big_bass: Optional[str] = None,
    page: int = 1,
) -> Any:
    """Display the photo gallery with optional filters and pagination."""
    user = get_current_user(request)

    # Parse filter parameters (empty strings become None)
    tournament_id_int: Optional[int] = None
    angler_id_int: Optional[int] = None
    big_bass_bool: Optional[bool] = None

    if tournament_id and tournament_id.strip():
        try:
            tournament_id_int = int(tournament_id)
        except ValueError:
            pass

    if angler_id and angler_id.strip():
        try:
            angler_id_int = int(angler_id)
        except ValueError:
            pass

    if big_bass and big_bass.strip().lower() == "true":
        big_bass_bool = True

    # Ensure page is valid
    if page < 1:
        page = 1

    offset = (page - 1) * PHOTOS_PER_PAGE

    with get_session() as session:
        query = build_photo_query(session, tournament_id_int, angler_id_int, big_bass_bool)

        # Get total count for pagination
        total_photos = query.count()
        total_pages = (total_photos + PHOTOS_PER_PAGE - 1) // PHOTOS_PER_PAGE
        has_more = page < total_pages

        # Get paginated results
        results = query.limit(PHOTOS_PER_PAGE).offset(offset).all()

        photos: List[Dict[str, Any]] = [
            photo_to_dict(photo, angler, tournament, user) for photo, angler, tournament in results
        ]

        # Check if this is an HTMX request for infinite scroll
        is_htmx = request.headers.get("HX-Request") == "true"

        if is_htmx:
            # Return just the photo grid items for infinite scroll
            return templates.TemplateResponse(
                "photos/_photo_grid.html",
                {
                    "request": request,
                    "user": user,
                    "photos": photos,
                    "page": page,
                    "has_more": has_more,
                    "tournament_id": tournament_id_int,
                    "angler_id": angler_id_int,
                    "big_bass": big_bass_bool,
                },
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
            "selected_tournament": tournament_id_int,
            "selected_angler": angler_id_int,
            "selected_big_bass": big_bass_bool,
            "page": page,
            "has_more": has_more,
            "total_photos": total_photos,
        },
    )


@router.get("/photos/upload")
async def upload_form(request: Request) -> Any:
    """Display the photo upload form."""
    user = require_member(request)

    with get_session() as session:
        # Get tournament IDs that have team_results
        team_result_tournament_ids = session.query(TeamResult.tournament_id).distinct().subquery()
        # Show tournaments that are complete OR have team_results
        # Sort by event date (most recent first)
        tournaments = (
            session.query(Tournament)
            .join(Event, Tournament.event_id == Event.id)
            .filter(
                or_(
                    Tournament.complete.is_(True),
                    Tournament.id.in_(session.query(team_result_tournament_ids)),
                )
            )
            .order_by(Event.date.desc())
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
    tournament_id: str = Form(default=""),
    is_big_bass: bool = Form(default=False),
) -> RedirectResponse:
    """Handle photo upload."""
    logger.info(f"Photo upload started: filename={photo.filename}, tournament_id={tournament_id}")
    user = require_member(request)
    logger.info(f"Photo upload auth passed: user_id={user.get('id')}, user_name={user.get('name')}")

    # Parse tournament_id (empty string from form select becomes None)
    tournament_id_int: Optional[int] = None
    if tournament_id and tournament_id.strip():
        try:
            tournament_id_int = int(tournament_id)
        except ValueError:
            return error_redirect("/photos/upload", "Invalid tournament selected.")

    # Validate file extension
    ext = os.path.splitext(photo.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return error_redirect(
            "/photos/upload",
            f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Check upload limit
    if not can_upload_photo(user, tournament_id_int):
        return error_redirect(
            "/photos/upload",
            "You have reached the upload limit (2 photos per tournament).",
        )

    # Read and validate file size
    logger.info("Photo upload: reading file contents...")
    contents = await photo.read()
    logger.info(f"Photo upload: file read complete, size={len(contents)} bytes")
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
    logger.info(f"Photo upload: saving to {filepath}...")
    try:
        with open(filepath, "wb") as f:
            f.write(contents)
        logger.info("Photo upload: file saved successfully")
    except Exception as e:
        logger.error(f"Failed to save photo: {e}")
        return error_redirect("/photos/upload", "Failed to save photo. Please try again.")

    # Generate thumbnail and blur placeholder
    logger.info("Photo upload: generating thumbnail and placeholder...")
    thumbnail_filename, placeholder_filename = generate_thumbnail(contents, filename)

    # Create database record
    logger.info("Photo upload: creating database record...")
    try:
        with get_session() as session:
            photo_record = Photo(
                angler_id=user["id"],
                tournament_id=tournament_id_int,
                filename=filename,
                thumbnail_filename=thumbnail_filename,
                placeholder_filename=placeholder_filename,
                caption=caption[:200] if caption else None,
                is_big_bass=is_big_bass,
            )
            session.add(photo_record)
            session.commit()
        logger.info(
            f"Photo upload: success! filename={filename}, "
            f"thumbnail={thumbnail_filename}, placeholder={placeholder_filename}"
        )
    except Exception as e:
        logger.error(f"Failed to create photo record: {e}")
        # Clean up files if database insert fails
        if os.path.exists(filepath):
            os.remove(filepath)
        if thumbnail_filename:
            thumb_path = os.path.join(THUMBNAIL_DIR, thumbnail_filename)
            if os.path.exists(thumb_path):
                os.remove(thumb_path)
        if placeholder_filename:
            placeholder_path = os.path.join(PLACEHOLDER_DIR, placeholder_filename)
            if os.path.exists(placeholder_path):
                os.remove(placeholder_path)
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

        # Delete original file
        filepath = os.path.join(UPLOAD_DIR, photo.filename)
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception as e:
                logger.error(f"Failed to delete photo file: {e}")

        # Delete thumbnail if exists
        if photo.thumbnail_filename:
            thumb_path = os.path.join(THUMBNAIL_DIR, photo.thumbnail_filename)
            if os.path.exists(thumb_path):
                try:
                    os.remove(thumb_path)
                except Exception as e:
                    logger.error(f"Failed to delete thumbnail: {e}")

        # Delete placeholder if exists
        if photo.placeholder_filename:
            placeholder_path = os.path.join(PLACEHOLDER_DIR, photo.placeholder_filename)
            if os.path.exists(placeholder_path):
                try:
                    os.remove(placeholder_path)
                except Exception as e:
                    logger.error(f"Failed to delete placeholder: {e}")

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
    tournament_id: str = Form(default=""),
    is_big_bass: bool = Form(default=False),
) -> RedirectResponse:
    """Handle photo edit."""
    user = require_member(request)

    # Parse tournament_id (empty string from form select becomes None)
    tournament_id_int: Optional[int] = None
    if tournament_id and tournament_id.strip():
        try:
            tournament_id_int = int(tournament_id)
        except ValueError:
            return error_redirect("/photos", "Invalid tournament selected.")

    with get_session() as session:
        photo = session.query(Photo).filter(Photo.id == photo_id).first()
        if not photo:
            return error_redirect("/photos", "Photo not found.")

        if not can_edit_photo(user, photo):
            return error_redirect("/photos", "You don't have permission to edit this photo.")

        # Update photo fields
        photo.caption = caption[:200] if caption else None
        photo.tournament_id = tournament_id_int
        photo.is_big_bass = is_big_bass

        session.commit()

    return success_redirect("/photos", "Photo updated successfully!")
