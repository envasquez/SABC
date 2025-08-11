# Static file serving middleware with caching and optimization
import mimetypes
import os
import time
from urllib.parse import unquote

from django.conf import settings
from django.core.files.storage import default_storage
from django.http import Http404, HttpResponse
from django.utils.deprecation import MiddlewareMixin


class StaticFileOptimizationMiddleware(MiddlewareMixin):
    """
    Middleware to optimize static file serving with proper caching headers.
    Only active in production (when DEBUG=False).
    """

    def __init__(self, get_response):
        super().__init__(get_response)
        self.static_url = getattr(settings, "STATIC_URL", "/static/")
        self.media_url = getattr(settings, "MEDIA_URL", "/media/")
        self.cache_max_age = 86400 * 30  # 30 days for static files
        self.media_cache_max_age = 86400 * 7  # 7 days for media files

    def process_response(self, request, response):
        """Add caching headers for static and media files."""
        if getattr(settings, "DEBUG", True):
            return response

        path = request.path

        # Handle static files
        if path.startswith(self.static_url):
            self._add_static_headers(response, path)

        # Handle media files
        elif path.startswith(self.media_url):
            self._add_media_headers(response, path)

        return response

    def _add_static_headers(self, response, path):
        """Add caching headers for static files."""
        # Static files should be cached aggressively
        response["Cache-Control"] = f"public, max-age={self.cache_max_age}, immutable"
        response["Expires"] = self._get_expires_header(self.cache_max_age)

        # Add compression hint
        if path.endswith((".css", ".js", ".json")):
            response["Vary"] = "Accept-Encoding"

        # Security headers for static files
        if path.endswith(".js"):
            response["X-Content-Type-Options"] = "nosniff"

    def _add_media_headers(self, response, path):
        """Add caching headers for media files."""
        # Media files cached for shorter period (they may be updated)
        response["Cache-Control"] = f"public, max-age={self.media_cache_max_age}"
        response["Expires"] = self._get_expires_header(self.media_cache_max_age)

        # Add MIME type if not set
        if not response.get("Content-Type"):
            mime_type, _ = mimetypes.guess_type(path)
            if mime_type:
                response["Content-Type"] = mime_type

        # Security for images
        if path.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
            response["X-Content-Type-Options"] = "nosniff"

    def _get_expires_header(self, max_age):
        """Generate Expires header."""
        expires_time = time.time() + max_age
        return time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(expires_time))


class CompressedStaticFilesMiddleware(MiddlewareMixin):
    """
    Middleware to serve pre-compressed static files if available.
    Looks for .gz and .br (Brotli) versions of static files.
    """

    def __init__(self, get_response):
        super().__init__(get_response)
        self.static_url = getattr(settings, "STATIC_URL", "/static/")
        self.static_root = getattr(settings, "STATIC_ROOT", "")

    def process_request(self, request):
        """Check for compressed versions of static files."""
        if getattr(settings, "DEBUG", True) or not self.static_root:
            return None

        path = request.path
        if not path.startswith(self.static_url):
            return None

        # Only compress certain file types
        if not path.endswith((".css", ".js", ".json", ".svg", ".xml")):
            return None

        # Get file path
        relative_path = path[len(self.static_url) :]
        file_path = os.path.join(self.static_root, relative_path)

        # Check for compressed versions
        compressed_file = None
        encoding = None

        # Check for Brotli first (better compression)
        if "br" in request.headers.get("Accept-Encoding", ""):
            br_path = f"{file_path}.br"
            if os.path.exists(br_path):
                compressed_file = br_path
                encoding = "br"

        # Fall back to gzip
        if not compressed_file and "gzip" in request.headers.get("Accept-Encoding", ""):
            gz_path = f"{file_path}.gz"
            if os.path.exists(gz_path):
                compressed_file = gz_path
                encoding = "gzip"

        # Serve compressed file if available
        if compressed_file:
            try:
                with open(compressed_file, "rb") as f:
                    content = f.read()

                # Determine content type
                content_type, _ = mimetypes.guess_type(file_path)
                if not content_type:
                    content_type = "application/octet-stream"

                response = HttpResponse(content, content_type=content_type)
                response["Content-Encoding"] = encoding
                response["Vary"] = "Accept-Encoding"

                return response

            except (IOError, OSError):
                # Fall back to normal serving
                pass

        return None


def create_compressed_static_files():
    """
    Utility function to create compressed versions of static files.
    This should be run as part of the deployment process.
    """
    import gzip
    import subprocess

    static_root = getattr(settings, "STATIC_ROOT", "")
    if not static_root or not os.path.exists(static_root):
        return

    compressible_extensions = (".css", ".js", ".json", ".svg", ".xml")

    for root, dirs, files in os.walk(static_root):
        for file in files:
            if file.endswith(compressible_extensions):
                file_path = os.path.join(root, file)

                # Create gzip version
                gz_path = f"{file_path}.gz"
                if not os.path.exists(gz_path):
                    try:
                        with open(file_path, "rb") as f_in:
                            with gzip.open(gz_path, "wb") as f_out:
                                f_out.writelines(f_in)
                    except Exception as e:
                        print(f"Error creating gzip for {file_path}: {e}")

                # Create brotli version if brotli is available
                br_path = f"{file_path}.br"
                if not os.path.exists(br_path):
                    try:
                        result = subprocess.run(
                            ["brotli", "-f", "-q", "11", "-o", br_path, file_path],
                            capture_output=True,
                        )
                        if result.returncode != 0:
                            # Fall back to Python brotli if available
                            try:
                                import brotli  # type: ignore[import-untyped]

                                with open(file_path, "rb") as f_in:
                                    with open(br_path, "wb") as f_out:
                                        f_out.write(
                                            brotli.compress(f_in.read(), quality=11)
                                        )
                            except ImportError:
                                pass
                    except (FileNotFoundError, subprocess.SubprocessError):
                        pass
