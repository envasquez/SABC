"""Regenerate optimized thumbnails for all existing photos.

This script converts existing thumbnails to WebP format and generates
blur placeholders for faster photo loading.

Usage:
    python scripts/regenerate_thumbnails.py
    python scripts/regenerate_thumbnails.py --dry-run
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Optional

from PIL import Image, ImageOps

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.db_schema import Photo, get_session  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Configuration matching gallery.py
UPLOAD_DIR = "uploads/photos"
THUMBNAIL_DIR = "uploads/photos/thumbnails"
PLACEHOLDER_DIR = "uploads/photos/placeholders"
THUMBNAIL_SIZE = (200, 200)
PLACEHOLDER_SIZE = (20, 20)
WEBP_QUALITY = 80


def ensure_dirs() -> None:
    """Create directories if they don't exist."""
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(THUMBNAIL_DIR, exist_ok=True)
    os.makedirs(PLACEHOLDER_DIR, exist_ok=True)


def generate_webp_thumbnail(original_path: str, filename: str) -> Optional[str]:
    """Generate a WebP thumbnail from the original image."""
    try:
        original = Image.open(original_path)

        # Apply EXIF orientation (fixes rotated phone photos)
        original = ImageOps.exif_transpose(original)

        if original.mode in ("RGBA", "P"):
            img = original.convert("RGB")
            original.close()
        else:
            img = original

        img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

        thumb_filename = os.path.splitext(filename)[0] + ".webp"
        thumb_path = os.path.join(THUMBNAIL_DIR, thumb_filename)

        img.save(thumb_path, "WEBP", quality=WEBP_QUALITY, method=4)
        logger.debug(f"Generated thumbnail: {thumb_filename}")

        return thumb_filename
    except Exception as e:
        logger.error(f"Failed to generate thumbnail for {filename}: {e}")
        return None


def generate_placeholder(original_path: str, filename: str) -> Optional[str]:
    """Generate a tiny blur placeholder."""
    try:
        original = Image.open(original_path)

        # Apply EXIF orientation (fixes rotated phone photos)
        original = ImageOps.exif_transpose(original)

        if original.mode in ("RGBA", "P"):
            img = original.convert("RGB")
            original.close()
        else:
            img = original

        img.thumbnail(PLACEHOLDER_SIZE, Image.Resampling.LANCZOS)

        placeholder_filename = os.path.splitext(filename)[0] + ".webp"
        placeholder_path = os.path.join(PLACEHOLDER_DIR, placeholder_filename)

        img.save(placeholder_path, "WEBP", quality=20, method=6)
        logger.debug(f"Generated placeholder: {placeholder_filename}")

        return placeholder_filename
    except Exception as e:
        logger.error(f"Failed to generate placeholder for {filename}: {e}")
        return None


def regenerate_thumbnails(dry_run: bool = False) -> int:
    """Regenerate thumbnails for all photos."""
    if not os.environ.get("DATABASE_URL"):
        logger.error("DATABASE_URL environment variable not set")
        return 1

    ensure_dirs()

    updated = 0
    skipped = 0
    errors = 0

    with get_session() as session:
        photos = session.query(Photo).all()
        total = len(photos)
        logger.info(f"Found {total} photos to process")

        for i, photo in enumerate(photos, 1):
            original_path = os.path.join(UPLOAD_DIR, photo.filename)

            if not os.path.exists(original_path):
                logger.warning(f"[{i}/{total}] Original not found: {photo.filename}")
                skipped += 1
                continue

            # Check if we need to regenerate
            needs_thumbnail = not photo.thumbnail_filename or not photo.thumbnail_filename.endswith(
                ".webp"
            )
            needs_placeholder = not photo.placeholder_filename

            if not needs_thumbnail and not needs_placeholder:
                logger.debug(f"[{i}/{total}] Skipping (already optimized): {photo.filename}")
                skipped += 1
                continue

            logger.info(f"[{i}/{total}] Processing: {photo.filename}")

            if dry_run:
                logger.info(f"  Would regenerate thumbnail: {needs_thumbnail}")
                logger.info(f"  Would generate placeholder: {needs_placeholder}")
                updated += 1
                continue

            try:
                if needs_thumbnail:
                    thumb = generate_webp_thumbnail(original_path, photo.filename)
                    if thumb:
                        # Clean up old thumbnail if different
                        if photo.thumbnail_filename and photo.thumbnail_filename != thumb:
                            old_thumb_path = os.path.join(THUMBNAIL_DIR, photo.thumbnail_filename)
                            if os.path.exists(old_thumb_path):
                                os.remove(old_thumb_path)
                        photo.thumbnail_filename = thumb

                if needs_placeholder:
                    placeholder = generate_placeholder(original_path, photo.filename)
                    if placeholder:
                        photo.placeholder_filename = placeholder

                session.commit()
                updated += 1
            except Exception as e:
                logger.error(f"  Error: {e}")
                session.rollback()
                errors += 1

    logger.info("")
    logger.info("=" * 50)
    logger.info(f"Total:   {total}")
    logger.info(f"Updated: {updated}")
    logger.info(f"Skipped: {skipped}")
    logger.info(f"Errors:  {errors}")

    if dry_run:
        logger.info("")
        logger.info("DRY RUN - no changes were made")

    return 0 if errors == 0 else 1


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Regenerate optimized thumbnails for all photos")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    return regenerate_thumbnails(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
