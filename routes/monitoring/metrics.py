"""Prometheus metrics endpoint for monitoring."""

from fastapi import Request, Response

from core.helpers.auth import require_admin
from core.monitoring.metrics import get_metrics
from routes.monitoring import router


@router.get("/metrics")
def metrics_endpoint(request: Request) -> Response:
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus text format for scraping. Requires admin
    privileges so the endpoint stays available for monitoring in production
    without exposing internal metrics to anonymous clients.

    Returns:
        Response with metrics data in Prometheus format
    """
    require_admin(request)
    metrics_data = get_metrics()
    return Response(content=metrics_data, media_type="text/plain; charset=utf-8")
