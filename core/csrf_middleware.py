"""Custom CSRF middleware that supports both headers and form data."""

import functools

from starlette.requests import Request
from starlette.types import Receive, Scope, Send
from starlette_csrf.middleware import CSRFMiddleware as BaseCSRFMiddleware


class CSRFMiddleware(BaseCSRFMiddleware):
    """Extended CSRF middleware that checks both headers and form data.

    This middleware extends starlette-csrf to support CSRF tokens in form data,
    not just headers. This is necessary for traditional HTML form submissions.

    The key challenge is that reading the request body in middleware consumes it,
    so we need to cache and replay it for downstream handlers.
    """

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Override to handle form-based CSRF token checking."""
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        csrf_cookie = request.cookies.get(self.cookie_name)

        # Check if CSRF validation is required
        should_validate = self._url_is_required(request.url) or (
            request.method not in self.safe_methods
            and not self._url_is_exempt(request.url)
            and self._has_sensitive_cookies(request.cookies)
        )

        if should_validate:
            # Try to get token from headers first (for AJAX requests)
            submitted_csrf_token = request.headers.get(self.header_name)

            # If not in headers and it's a form POST, check the body
            if not submitted_csrf_token and request.method == "POST":
                content_type = request.headers.get("content-type", "")
                if "application/x-www-form-urlencoded" in content_type:
                    # Read and cache the entire body
                    body_parts = []
                    async for chunk in request.stream():
                        body_parts.append(chunk)
                    body = b"".join(body_parts)

                    # Parse form data to extract CSRF token
                    from urllib.parse import parse_qs

                    form_data = parse_qs(body.decode("utf-8"))
                    submitted_csrf_token = form_data.get("csrf_token", [None])[0]

                    # Create a new receive callable that replays the cached body
                    async def receive_with_cached_body():
                        return {"type": "http.request", "body": body, "more_body": False}

                    receive = receive_with_cached_body

            # Validate CSRF token
            if (
                not csrf_cookie
                or not submitted_csrf_token
                or not self._csrf_tokens_match(csrf_cookie, submitted_csrf_token)
            ):
                response = self._get_error_response(request)
                await response(scope, receive, send)
                return

        # Continue processing with cached body if we read it
        send = functools.partial(self.send, send=send, scope=scope)
        await self.app(scope, receive, send)
