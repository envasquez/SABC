# URL patterns for core functionality (health checks, monitoring)
from django.urls import path

from . import health_checks

urlpatterns = [
    # Health check endpoints
    path("health/", health_checks.HealthCheckView.as_view(), name="health_check"),
    path(
        "health/readiness/",
        health_checks.ReadinessCheckView.as_view(),
        name="readiness_check",
    ),
    path(
        "health/liveness/",
        health_checks.LivenessCheckView.as_view(),
        name="liveness_check",
    ),
]
