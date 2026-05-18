"""Tests for the custom CSRF middleware.

Regression coverage for the cookie-less-first-visit bug: the form's hidden
csrf_token field used to render empty on a request that arrived without a
csrf_token cookie (e.g. a first-ever GET /login), so the first POST failed
CSRF validation with a 403.

The app disables CSRF in the test environment, so these tests wire the
middleware onto a minimal standalone app and exercise the real
get_csrf_token() helper used by templates.
"""

import re

from starlette.applications import Starlette
from starlette.responses import HTMLResponse, PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from app_setup import get_csrf_token
from core.csrf_middleware import CSRFMiddleware

_FORM_TOKEN = re.compile(r'value="([^"]*)"')


def _make_client() -> TestClient:
    async def form_page(request):
        # Mirrors how templates embed the token via the csrf_token() macro.
        return HTMLResponse(f'<input name="csrf_token" value="{get_csrf_token(request)}">')

    async def submit(request):
        return PlainTextResponse("ok")

    app = Starlette(
        routes=[
            Route("/form", form_page),
            Route("/submit", submit, methods=["POST"]),
        ]
    )
    app.add_middleware(
        CSRFMiddleware,
        secret="test-secret-key-for-csrf",
        cookie_name="csrf_token",
        header_name="x-csrf-token",
    )
    return TestClient(app)


def test_form_token_populated_on_cookieless_first_visit():
    """The form's csrf_token must be non-empty even with no prior cookie."""
    client = _make_client()  # fresh client => no cookies sent on the first GET

    response = client.get("/form")

    match = _FORM_TOKEN.search(response.text)
    assert match is not None
    assert match.group(1), "form CSRF token is empty on a cookie-less first visit"


def test_first_visit_response_cookie_matches_form_token():
    """The cookie set on the first response must equal the rendered form token."""
    client = _make_client()

    response = client.get("/form")

    form_token = _FORM_TOKEN.search(response.text).group(1)
    assert client.cookies.get("csrf_token") == form_token


def test_post_succeeds_immediately_after_first_visit():
    """A GET then POST with the first-visit token must pass CSRF validation."""
    client = _make_client()

    form_token = _FORM_TOKEN.search(client.get("/form").text).group(1)
    response = client.post("/submit", data={"csrf_token": form_token})

    assert response.status_code == 200
    assert response.text == "ok"


def test_post_without_token_is_rejected():
    """A POST with no CSRF token is still rejected with a 403."""
    client = _make_client()
    client.get("/form")  # establish the cookie

    response = client.post("/submit", data={})

    assert response.status_code == 403
