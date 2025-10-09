"""Middleware for tracking metrics and monitoring."""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from core.monitoring.metrics import http_request_duration_seconds, http_requests_total


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to track HTTP request metrics."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Track request metrics for each HTTP request.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/route handler

        Returns:
            HTTP response
        """
        # Record start time
        start_time = time.time()

        # Get endpoint path (strip query params for cleaner metrics)
        path = request.url.path
        method = request.method

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Record metrics
        http_requests_total.labels(method=method, endpoint=path, status=response.status_code).inc()

        http_request_duration_seconds.labels(method=method, endpoint=path).observe(duration)

        return response
