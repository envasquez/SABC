# Query Performance Monitoring for SABC
# Phase 2: Performance & Reliability

import logging
import time

from django.conf import settings
from django.core.signals import request_finished, request_started
from django.db import connection
from django.dispatch import receiver

logger = logging.getLogger("sabc.performance")


class QueryCountDebugMiddleware:
    """
    Middleware to monitor and log database query performance.
    Tracks query counts, execution times, and identifies slow queries.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.db import reset_queries

        # Only monitor in debug mode or if explicitly enabled
        if settings.DEBUG or getattr(settings, "MONITOR_QUERIES", False):
            reset_queries()
            start_time = time.time()

            response = self.get_response(request)

            # Calculate metrics
            execution_time = time.time() - start_time
            num_queries = len(connection.queries)

            # Log performance metrics
            self._log_performance_metrics(
                request.path, num_queries, execution_time, connection.queries
            )

            # Add metrics to response headers (for debugging)
            if settings.DEBUG:
                response["X-DB-Query-Count"] = str(num_queries)
                response["X-Execution-Time"] = f"{execution_time:.3f}s"

            return response

        return self.get_response(request)

    def _log_performance_metrics(self, path, num_queries, execution_time, queries):
        """Log performance metrics based on thresholds."""

        # Thresholds for warnings
        QUERY_COUNT_WARNING = 20  # Warn if more than 20 queries
        SLOW_QUERY_THRESHOLD = 0.1  # 100ms
        SLOW_REQUEST_THRESHOLD = 1.0  # 1 second

        # Log high query count
        if num_queries > QUERY_COUNT_WARNING:
            logger.warning(
                f"High query count on {path}: {num_queries} queries in {execution_time:.3f}s"
            )

            # Log top 5 slowest queries
            slow_queries = sorted(
                queries, key=lambda q: float(q["time"]), reverse=True
            )[:5]

            for i, query in enumerate(slow_queries, 1):
                logger.warning(
                    f"  Slow query #{i} ({query['time']}s): {query['sql'][:200]}..."
                )

        # Log slow requests
        elif execution_time > SLOW_REQUEST_THRESHOLD:
            logger.warning(
                f"Slow request on {path}: {execution_time:.3f}s with {num_queries} queries"
            )

        # Log individual slow queries
        for query in queries:
            if float(query["time"]) > SLOW_QUERY_THRESHOLD:
                logger.warning(
                    f"Slow query detected ({query['time']}s): {query['sql'][:300]}..."
                )


class DatabasePerformanceLogger:
    """
    Utility class for logging database performance metrics.
    Can be used to track specific operations.
    """

    @staticmethod
    def log_operation(operation_name, start_time=None):
        """Log the performance of a database operation."""
        if start_time:
            execution_time = time.time() - start_time
            if execution_time > 0.5:
                logger.warning(
                    f"Slow operation '{operation_name}': {execution_time:.3f}s"
                )
            else:
                logger.debug(
                    f"Operation '{operation_name}' completed in {execution_time:.3f}s"
                )
            return execution_time
        return time.time()

    @staticmethod
    def track_queries(func):
        """Decorator to track queries for a specific function."""
        from functools import wraps

        @wraps(func)
        def wrapper(*args, **kwargs):
            from django.db import reset_queries

            if settings.DEBUG or getattr(settings, "MONITOR_QUERIES", False):
                reset_queries()
                start_time = time.time()

                result = func(*args, **kwargs)

                execution_time = time.time() - start_time
                num_queries = len(connection.queries)

                if num_queries > 10 or execution_time > 0.5:
                    logger.warning(
                        f"{func.__name__}: {num_queries} queries in {execution_time:.3f}s"
                    )

                return result

            return func(*args, **kwargs)

        return wrapper


# Signal receivers for request monitoring
@receiver(request_started)
def log_request_started(sender, environ, **kwargs):
    """Log when a request starts."""
    if settings.DEBUG:
        path = environ.get("PATH_INFO", "unknown")
        method = environ.get("REQUEST_METHOD", "unknown")
        logger.debug(f"Request started: {method} {path}")


@receiver(request_finished)
def log_request_finished(sender, **kwargs):
    """Log when a request finishes."""
    if settings.DEBUG:
        logger.debug("Request finished")


# Performance monitoring configuration
PERFORMANCE_CONFIG = {
    "ENABLE_MONITORING": True,
    "LOG_SLOW_QUERIES": True,
    "SLOW_QUERY_THRESHOLD": 0.1,  # 100ms
    "HIGH_QUERY_COUNT_THRESHOLD": 20,
    "SLOW_REQUEST_THRESHOLD": 1.0,  # 1 second
    "CACHE_TIMEOUT": 300,  # 5 minutes default cache
}


def get_query_statistics():
    """
    Get current query statistics for the request.
    Useful for debugging and performance analysis.
    """
    if not settings.DEBUG:
        return None

    total_time = sum(float(q["time"]) for q in connection.queries)

    return {
        "total_queries": len(connection.queries),
        "total_time": total_time,
        "average_time": total_time / len(connection.queries)
        if connection.queries
        else 0,
        "slowest_query": max((float(q["time"]) for q in connection.queries), default=0),
        "queries": connection.queries if settings.DEBUG else [],
    }
