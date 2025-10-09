"""Sentry error monitoring integration for SABC application."""

import os
from typing import Optional

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration


def init_sentry() -> None:
    """
    Initialize Sentry error monitoring.

    Sentry will only be enabled if SENTRY_DSN environment variable is set.
    This allows running without Sentry in development/test environments.
    """
    sentry_dsn = os.environ.get("SENTRY_DSN")

    if not sentry_dsn:
        # Sentry disabled - no DSN configured
        return

    environment = os.environ.get("ENVIRONMENT", "development")

    # Determine sample rate based on environment
    traces_sample_rate = 0.1 if environment == "production" else 0.0

    sentry_sdk.init(
        dsn=sentry_dsn,
        environment=environment,
        # Set traces_sample_rate to capture performance monitoring data
        # 0.1 = 10% of transactions in production, 0% in dev/test
        traces_sample_rate=traces_sample_rate,
        # Integrations for FastAPI and SQLAlchemy
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
        ],
        # Send default PII (Personally Identifiable Information)
        send_default_pii=False,  # Don't send user data by default for privacy
        # Release tracking (for deployment tracking)
        release=os.environ.get("RELEASE_VERSION", "unknown"),
        # Attach stack traces to all messages
        attach_stacktrace=True,
        # Before send hook to filter sensitive data
        before_send=filter_sensitive_data,
    )


def filter_sensitive_data(event: dict, hint: dict) -> Optional[dict]:
    """
    Filter sensitive data from Sentry events before sending.

    Args:
        event: Sentry event dictionary
        hint: Additional context about the event

    Returns:
        Modified event or None to drop the event
    """
    # Remove sensitive request data
    if "request" in event:
        request = event["request"]

        # Remove authentication headers
        if "headers" in request:
            headers = request["headers"]
            sensitive_headers = ["authorization", "cookie", "x-csrf-token"]
            for header in sensitive_headers:
                if header in headers:
                    headers[header] = "[Filtered]"

        # Remove sensitive query parameters
        if "query_string" in request:
            # Don't send query strings that might contain tokens/passwords
            request["query_string"] = "[Filtered]"

        # Remove form data (might contain passwords)
        if "data" in request:
            request["data"] = "[Filtered]"

    # Remove sensitive environment variables
    if "contexts" in event and "runtime" in event["contexts"]:
        runtime = event["contexts"]["runtime"]
        if "env" in runtime:
            env = runtime["env"]
            sensitive_env_vars = [
                "DATABASE_URL",
                "SECRET_KEY",
                "SENTRY_DSN",
                "SMTP_PASSWORD",
            ]
            for var in sensitive_env_vars:
                if var in env:
                    env[var] = "[Filtered]"

    return event
