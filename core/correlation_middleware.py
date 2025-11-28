"""Request correlation ID middleware for request tracing.

Generates or extracts a unique correlation ID for each request to enable
tracing requests across logs and services.
"""

import uuid
from contextvars import ContextVar
from typing import Any, Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Context variable to store correlation ID for the current request
correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)

# Header name for correlation ID (standard header)
CORRELATION_ID_HEADER = "X-Request-ID"


def get_correlation_id() -> Optional[str]:
    """Get the correlation ID for the current request context.

    Returns:
        The correlation ID if set, None otherwise.
    """
    return correlation_id_var.get()


def generate_correlation_id() -> str:
    """Generate a new correlation ID.

    Returns:
        A unique correlation ID string.
    """
    return str(uuid.uuid4())


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Middleware that assigns a unique correlation ID to each request.

    The correlation ID is:
    - Extracted from the X-Request-ID header if present (for distributed tracing)
    - Generated as a new UUID if not present
    - Stored in a context variable for access throughout the request lifecycle
    - Added to the response headers for client correlation
    """

    async def dispatch(self, request: Request, call_next: Callable[[Request], Any]) -> Response:
        # Extract existing correlation ID from header or generate new one
        correlation_id = request.headers.get(CORRELATION_ID_HEADER)
        if not correlation_id:
            correlation_id = generate_correlation_id()

        # Store in context variable for logging and other uses
        token = correlation_id_var.set(correlation_id)

        # Store in request state for easy access in route handlers
        request.state.correlation_id = correlation_id

        try:
            response = await call_next(request)
            # Add correlation ID to response headers
            response.headers[CORRELATION_ID_HEADER] = correlation_id
            return response
        finally:
            # Reset context variable
            correlation_id_var.reset(token)
