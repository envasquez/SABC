from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        # Check if request is HTTPS (directly or via reverse proxy)
        is_https = (
            request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
        )

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "0"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        if is_https:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # script-src omits 'unsafe-inline': every inline on*= handler and
        # inline <script> block has been migrated to addEventListener and
        # external files (Phase 4+5+6 of the audit). This closes the single
        # biggest XSS amplifier — any future escape gap is now blocked by
        # the browser rather than fully exploitable.
        # style-src still allows 'unsafe-inline' because templates carry
        # inline style="" attributes (Tabler card layouts, photo-grid
        # positioning, etc.). Migrating those to classes is a follow-up.
        csp = (
            "default-src 'self'; "
            "script-src 'self' "
            "https://cdn.jsdelivr.net https://unpkg.com https://challenges.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            "font-src 'self' https://cdn.jsdelivr.net https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "frame-src https://www.google.com https://maps.google.com https://challenges.cloudflare.com; "
            "connect-src 'self' https://challenges.cloudflare.com"
        )
        # Only upgrade insecure requests in production (HTTPS)
        if is_https:
            csp += "; upgrade-insecure-requests"
        response.headers["Content-Security-Policy"] = csp

        return response
