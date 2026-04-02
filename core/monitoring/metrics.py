"""Prometheus metrics for SABC application monitoring."""

try:
    from prometheus_client import Counter, Histogram, generate_latest
    from prometheus_client.core import CollectorRegistry

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

    # Create no-op classes for when prometheus is not available
    class Counter:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            pass

        def labels(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            return self

        def inc(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            pass

    class Histogram:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            pass

        def labels(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            return self

        def observe(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            pass

    class CollectorRegistry:  # type: ignore[no-redef]
        pass


# Create a custom registry to avoid conflicts (or no-op if prometheus not available)
registry = CollectorRegistry()

# Request metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
    registry=registry,
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0),
    registry=registry,
)


def get_metrics() -> bytes:
    """
    Get current metrics in Prometheus format.

    Returns:
        Metrics data in Prometheus text format (or empty bytes if prometheus not available)
    """
    if not PROMETHEUS_AVAILABLE:
        return b"# Prometheus client not installed\n"

    return generate_latest(registry)  # type: ignore[name-defined]
