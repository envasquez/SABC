"""Monitoring and metrics endpoints."""

from fastapi import APIRouter

router = APIRouter()

# Import routes to register them with the router
from routes.monitoring import metrics, sentry_test  # noqa: F401, E402
