"""Prometheus metrics for SABC application monitoring."""

try:
    from prometheus_client import Counter, Gauge, Histogram, generate_latest
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

    class Gauge:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            pass

        def set(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            pass

        def inc(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            pass

        def dec(self, *args, **kwargs):  # type: ignore[no-untyped-def]
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

# Database metrics
db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query latency in seconds",
    ["query_type"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
    registry=registry,
)

db_connections_active = Gauge(
    "db_connections_active",
    "Number of active database connections",
    registry=registry,
)

# Application metrics
active_sessions = Gauge(
    "active_sessions",
    "Number of active user sessions",
    registry=registry,
)

poll_votes_total = Counter(
    "poll_votes_total",
    "Total poll votes submitted",
    ["poll_type"],
    registry=registry,
)

failed_logins_total = Counter(
    "failed_logins_total",
    "Total failed login attempts",
    registry=registry,
)

email_sent_total = Counter(
    "email_sent_total",
    "Total emails sent",
    ["email_type", "status"],
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
