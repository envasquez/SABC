"""Custom CSRF middleware that supports both headers and form data."""

import functools
import os
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from typing import Optional

from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.types import Receive, Scope, Send
from starlette_csrf.middleware import CSRFMiddleware as BaseCSRFMiddleware

# Cap the request body we'll drain into memory looking for the CSRF token.
# nginx already enforces client_max_body_size 15m upstream; we leave a small
# margin so legitimate at-cap requests don't get rejected at this layer too.
# Override via CSRF_MAX_BODY_BYTES if a deployment needs a different ceiling.
_MAX_BODY_BYTES = int(os.environ.get("CSRF_MAX_BODY_BYTES", str(16 * 1024 * 1024)))


def _extract_multipart_csrf_token(body: bytes, content_type: str) -> Optional[str]:
    """Extract csrf_token from a multipart/form-data body using stdlib MIME parsing.

    Returns the token if a part named "csrf_token" is found, else None. Returns
    None on any parse failure so the middleware falls through to CSRF rejection
    rather than crashing on malformed scanner payloads.
    """
    try:
        header_bytes = f"Content-Type: {content_type}\r\n\r\n".encode("utf-8")
        parser = BytesParser(EmailMessage, policy=policy.default)
        msg = parser.parsebytes(header_bytes + body)
        if not msg.is_multipart():
            return None
        for part in msg.iter_parts():
            cd = part.get("Content-Disposition", "")
            if 'name="csrf_token"' not in cd:
                continue
            content = part.get_content()
            if isinstance(content, bytes):
                content = content.decode("utf-8", errors="replace")
            return str(content).strip() or None
    except Exception:
        return None
    return None


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
                if (
                    "application/x-www-form-urlencoded" in content_type
                    or "multipart/form-data" in content_type
                ):
                    # Reject oversized bodies up front via Content-Length, before
                    # we drain anything into Python memory. nginx normally
                    # enforces this, but we don't want the middleware to be the
                    # single point of failure if it's ever fronted differently
                    # (e.g. local dev without nginx).
                    cl_header = request.headers.get("content-length")
                    if cl_header is not None:
                        try:
                            if int(cl_header) > _MAX_BODY_BYTES:
                                too_large: Response = PlainTextResponse(
                                    "Request body too large", status_code=413
                                )
                                await too_large(scope, receive, send)
                                return
                        except ValueError:
                            pass

                    # Read and cache the entire body, but bound it: if a chunked
                    # request lies about its size (or omits Content-Length),
                    # we still won't grow the buffer past the cap.
                    body_parts = []
                    total = 0
                    async for chunk in request.stream():
                        total += len(chunk)
                        if total > _MAX_BODY_BYTES:
                            too_large_streamed: Response = PlainTextResponse(
                                "Request body too large", status_code=413
                            )
                            await too_large_streamed(scope, receive, send)
                            return
                        body_parts.append(chunk)
                    body = b"".join(body_parts)

                    # Parse form data to extract CSRF token. Non-UTF-8 bodies
                    # (typically scanner probes posting binary payloads to URLs
                    # that advertise a form content-type) fall through to CSRF
                    # rejection rather than crashing the middleware.
                    if "application/x-www-form-urlencoded" in content_type:
                        from urllib.parse import parse_qs

                        try:
                            decoded_body = body.decode("utf-8")
                        except UnicodeDecodeError:
                            decoded_body = ""
                        form_data = parse_qs(decoded_body)
                        submitted_csrf_token = form_data.get("csrf_token", [None])[0]
                    elif "multipart/form-data" in content_type:
                        submitted_csrf_token = _extract_multipart_csrf_token(body, content_type)

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
