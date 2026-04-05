from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
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

        # CSP uses 'unsafe-inline' for script-src because the codebase relies heavily
        # on inline event handlers (onclick=, onchange=, etc.) across templates.
        # A nonce-based approach would require migrating all inline handlers to
        # addEventListener() first — otherwise CSP3 browsers silently ignore
        # 'unsafe-inline' when a nonce is present, breaking all onclick handlers.
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' "
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
