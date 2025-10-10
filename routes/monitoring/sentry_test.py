"""Test endpoint to verify Sentry error capture."""

import os

from fastapi import HTTPException

from routes.monitoring import router

try:
    import sentry_sdk

    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False


@router.get("/sentry-test")
async def sentry_test() -> dict[str, str]:
    """
    Test endpoint that manually captures a message to Sentry.

    This endpoint is used to verify that Sentry is properly capturing
    and reporting errors in production. When accessed, it will:
    1. Manually send a test message to Sentry
    2. Raise a ZeroDivisionError exception
    3. Both should appear in your Sentry dashboard

    Usage:
        Visit https://yourdomain.com/sentry-test in your browser
        Then check your Sentry dashboard for the captured events

    Raises:
        ZeroDivisionError: Always raised to test Sentry integration
    """
    # First, manually capture a test message
    if SENTRY_AVAILABLE:
        sentry_sdk.capture_message(  # type: ignore[attr-defined]
            "Sentry test endpoint was accessed - this is a manual test message",
            level="info",
        )
        # Flush to ensure it's sent immediately
        sentry_sdk.flush(timeout=2.0)  # type: ignore[attr-defined]

    # Then trigger a real exception that Sentry should also capture
    result = 1 / 0  # noqa: F841
    return {"status": "This line will never be reached"}


@router.get("/sentry-debug")
async def sentry_debug() -> dict[str, str]:
    """
    Debug endpoint to check Sentry configuration status.

    Returns:
        Dictionary with Sentry configuration details
    """
    dsn = os.environ.get("SENTRY_DSN", "NOT SET")
    dsn_masked = dsn[:30] + "..." if len(dsn) > 30 else dsn

    return {
        "sentry_sdk_installed": str(SENTRY_AVAILABLE),
        "sentry_dsn_set": "Yes" if dsn != "NOT SET" else "No",
        "sentry_dsn_masked": dsn_masked,
        "environment": os.environ.get("ENVIRONMENT", "NOT SET"),
        "sentry_initialized": str(SENTRY_AVAILABLE and dsn != "NOT SET"),
    }


@router.get("/sentry-test-http")
async def sentry_test_http() -> None:
    """
    Test endpoint that raises an HTTP exception.

    HTTP exceptions are handled differently - they may or may not be
    captured by Sentry depending on your configuration.

    Raises:
        HTTPException: 500 Internal Server Error for testing
    """
    raise HTTPException(status_code=500, detail="This is a test error for Sentry")
