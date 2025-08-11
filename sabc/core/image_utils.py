# Image optimization and thumbnail generation utilities
import logging
import os
from io import BytesIO
from typing import Optional, Tuple

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

logger = logging.getLogger(__name__)

try:
    from PIL import Image, ImageOps

    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    logger.warning("PIL/Pillow not available - image optimization disabled")


class ImageProcessor:
    """
    Image processing utilities for SABC application.
    Handles image optimization, resizing, and thumbnail generation.
    """

    @classmethod
    def optimize_image(cls, image_file, quality: int = None) -> Optional[ContentFile]:
        """Optimize an uploaded image by reducing size and quality."""
        if not HAS_PIL:
            return image_file

        quality = quality or getattr(settings, "IMAGE_QUALITY", 85)
        max_width = getattr(settings, "MAX_IMAGE_WIDTH", 1920)
        max_height = getattr(settings, "MAX_IMAGE_HEIGHT", 1080)

        try:
            # Open and process the image
            with Image.open(image_file) as img:
                # Convert to RGB if necessary
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")

                # Resize if too large
                if img.width > max_width or img.height > max_height:
                    img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

                # Apply auto-orientation based on EXIF data
                img = ImageOps.exif_transpose(img)

                # Save to BytesIO buffer
                output = BytesIO()
                img.save(output, format="JPEG", quality=quality, optimize=True)
                output.seek(0)

                # Create Django ContentFile
                filename = os.path.splitext(image_file.name)[0] + ".jpg"
                return ContentFile(output.getvalue(), filename)

        except Exception as e:
            logger.error(f"Error optimizing image {image_file.name}: {e}")
            return image_file

    @classmethod
    def create_thumbnail(
        cls, image_path: str, size: Tuple[int, int], crop: bool = True
    ) -> Optional[str]:
        """Create a thumbnail for an image."""
        if not HAS_PIL:
            return None

        try:
            # Generate thumbnail path
            base, ext = os.path.splitext(image_path)
            thumbnail_path = f"{base}_thumb_{size[0]}x{size[1]}{ext}"

            # Check if thumbnail already exists
            if default_storage.exists(thumbnail_path):
                return thumbnail_path

            # Open original image
            with default_storage.open(image_path, "rb") as img_file:
                with Image.open(img_file) as img:
                    # Convert to RGB if necessary
                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")

                    if crop:
                        # Crop to exact size (center crop)
                        img = ImageOps.fit(img, size, Image.Resampling.LANCZOS)
                    else:
                        # Resize maintaining aspect ratio
                        img.thumbnail(size, Image.Resampling.LANCZOS)

                    # Save thumbnail
                    output = BytesIO()
                    img.save(output, format="JPEG", quality=85, optimize=True)
                    output.seek(0)

                    default_storage.save(thumbnail_path, ContentFile(output.getvalue()))
                    return thumbnail_path

        except Exception as e:
            logger.error(f"Error creating thumbnail for {image_path}: {e}")
            return None

    @classmethod
    def create_all_thumbnails(cls, image_path: str) -> dict:
        """Create all configured thumbnail sizes for an image."""
        thumbnails = {}
        thumbnail_sizes = getattr(settings, "THUMBNAIL_SIZES", {})

        for size_name, size_tuple in thumbnail_sizes.items():
            thumbnail_path = cls.create_thumbnail(image_path, size_tuple)
            if thumbnail_path:
                thumbnails[size_name] = thumbnail_path

        return thumbnails

    @classmethod
    def cleanup_thumbnails(cls, image_path: str):
        """Remove all thumbnails associated with an image."""
        thumbnail_sizes = getattr(settings, "THUMBNAIL_SIZES", {})
        base, ext = os.path.splitext(image_path)

        for size_name, size_tuple in thumbnail_sizes.items():
            thumbnail_path = f"{base}_thumb_{size_tuple[0]}x{size_tuple[1]}{ext}"
            try:
                if default_storage.exists(thumbnail_path):
                    default_storage.delete(thumbnail_path)
            except Exception as e:
                logger.warning(f"Error deleting thumbnail {thumbnail_path}: {e}")


def compress_css_js():
    """Compress CSS and JavaScript files for production."""
    # This would typically be handled by a tool like django-compressor
    # or during the build process with webpack/rollup
    pass


def optimize_uploaded_image(sender, instance, created, **kwargs):
    """
    Signal handler to automatically optimize uploaded images.
    Connect this to your model's post_save signal.
    """
    if created and hasattr(instance, "image") and instance.image:
        try:
            optimized = ImageProcessor.optimize_image(instance.image)
            if optimized and optimized != instance.image:
                # Save the optimized image
                instance.image.save(instance.image.name, optimized, save=False)
                instance.save(update_fields=["image"])

                # Create thumbnails
                ImageProcessor.create_all_thumbnails(instance.image.name)

        except Exception as e:
            logger.error(f"Error in image optimization signal: {e}")
