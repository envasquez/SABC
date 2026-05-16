"""Test endpoint to verify Sentry error capture.

These endpoints are intentionally disabled in production. They are only
registered when ENVIRONMENT is not "production" to avoid exposing debug
surface (and configuration details) on the live site.
"""

import os

import sentry_sdk
from fastapi import HTTPException

from routes.monitoring import router

# Only expose Sentry test/debug endpoints outside of production.
_IS_PRODUCTION = os.getenv("ENVIRONMENT", "").lower() == "production"

if not _IS_PRODUCTION:

    @router.get("/sentry-test")
    def sentry_test() -> dict[str, str]:
        """
        Test endpoint that manually captures a message to Sentry.

        This endpoint is used to verify that Sentry is properly capturing
        and reporting errors. When accessed, it will:
        1. Manually send a test message to Sentry
        2. Raise a ZeroDivisionError exception
        3. Both should appear in your Sentry dashboard

        Raises:
            ZeroDivisionError: Always raised to test Sentry integration
        """
        # First, manually capture a test message
        sentry_sdk.capture_message(
            "Sentry test endpoint was accessed - this is a manual test message",
            level="info",
        )
        # Flush to ensure it's sent immediately
        sentry_sdk.flush(timeout=2.0)

        # Then trigger a real exception that Sentry should also capture
        result = 1 / 0  # noqa: F841
        return {"status": "This line will never be reached"}

    @router.get("/sentry-debug")
    def sentry_debug() -> dict[str, str]:
        """
        Debug endpoint to check Sentry configuration status.

        Returns:
            Dictionary with Sentry configuration details (no secrets disclosed)
        """
        dsn = os.environ.get("SENTRY_DSN", "NOT SET")

        return {
            "sentry_sdk_installed": "True",
            "sentry_dsn_set": "Yes" if dsn != "NOT SET" else "No",
            "environment": os.environ.get("ENVIRONMENT", "NOT SET"),
            "sentry_initialized": str(dsn != "NOT SET"),
        }

    @router.get("/sentry-test-http")
    def sentry_test_http() -> None:
        """
        Test endpoint that raises an HTTP exception.

        HTTP exceptions are handled differently - they may or may not be
        captured by Sentry depending on your configuration.

        Raises:
            HTTPException: 500 Internal Server Error for testing
        """
        raise HTTPException(status_code=500, detail="This is a test error for Sentry")
