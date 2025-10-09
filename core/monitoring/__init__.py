"""Monitoring and observability modules for SABC application."""

from core.monitoring.sentry import init_sentry

__all__ = ["init_sentry"]
