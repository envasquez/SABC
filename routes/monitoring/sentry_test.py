"""Test endpoint to verify Sentry error capture."""

from fastapi import HTTPException

from routes.monitoring import router


@router.get("/sentry-test")
async def sentry_test() -> None:
    """
    Test endpoint that always raises an exception.

    This endpoint is used to verify that Sentry is properly capturing
    and reporting errors in production. When accessed, it will:
    1. Raise a ZeroDivisionError exception
    2. Sentry should capture it and send it to your dashboard
    3. You should see the error in your Sentry project

    Usage:
        Visit https://yourdomain.com/sentry-test in your browser
        Then check your Sentry dashboard for the captured error

    Raises:
        ZeroDivisionError: Always raised to test Sentry integration
    """
    # This will trigger a real exception that Sentry should capture
    result = 1 / 0  # noqa: F841
    return None  # This line will never be reached


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
