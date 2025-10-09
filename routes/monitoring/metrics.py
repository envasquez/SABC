"""Prometheus metrics endpoint for monitoring."""

from fastapi import Response

from core.monitoring.metrics import get_metrics
from routes.monitoring import router


@router.get("/metrics")
async def metrics_endpoint() -> Response:
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus text format for scraping.

    Returns:
        Response with metrics data in Prometheus format
    """
    metrics_data = get_metrics()
    return Response(content=metrics_data, media_type="text/plain; charset=utf-8")
