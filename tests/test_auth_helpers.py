"""Tests for authentication helpers."""

from unittest.mock import Mock

import pytest
from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse

from core.helpers.auth import admin, require_admin, require_auth, require_member, u


class TestAuthHelpers:
    """Test authentication helper functions."""

    def test_u_with_logged_in_user(self, db_conn, member_user):
        """Test u() returns user data when user is logged in."""
        # Create mock request with session
        request = Mock(spec=Request)
        request.session = {"user_id": member_user["id"]}

        user = u(request)

        assert user is not None
        assert user["id"] == member_user["id"]
        assert user["name"] == member_user["name"]
        assert user["email"] == member_user["email"]
        assert user["member"] == member_user["member"]
        assert user["is_admin"] == member_user["is_admin"]

    def test_u_without_session(self):
        """Test u() returns None when no session."""
        request = Mock(spec=Request)
        request.session = {}

        user = u(request)

        assert user is None

    def test_u_with_invalid_user_id(self):
        """Test u() returns None when user ID doesn't exist."""
        request = Mock(spec=Request)
        request.session = {"user_id": 999999}  # Non-existent user

        user = u(request)

        assert user is None

    def test_admin_with_admin_user(self, db_conn, admin_user):
        """Test admin() returns user data for admin users."""
        request = Mock(spec=Request)
        request.session = {"user_id": admin_user["id"]}

        result = admin(request)

        assert not isinstance(result, RedirectResponse)
        assert result["id"] == admin_user["id"]
        assert result["is_admin"] is True

    def test_admin_with_non_admin_user(self, db_conn, member_user):
        """Test admin() returns redirect for non-admin users."""
        request = Mock(spec=Request)
        request.session = {"user_id": member_user["id"]}

        result = admin(request)

        assert isinstance(result, RedirectResponse)
        assert result.status_code == 302

    def test_admin_without_session(self):
        """Test admin() returns redirect when no session."""
        request = Mock(spec=Request)
        request.session = {}

        result = admin(request)

        assert isinstance(result, RedirectResponse)
        assert result.headers["location"] == "/login"

    def test_require_auth_with_logged_in_user(self, db_conn, member_user):
        """Test require_auth() returns user for logged in users."""
        request = Mock(spec=Request)
        request.session = {"user_id": member_user["id"]}

        user = require_auth(request)

        assert user["id"] == member_user["id"]

    def test_require_auth_without_session(self):
        """Test require_auth() raises exception when not logged in."""
        request = Mock(spec=Request)
        request.session = {}

        with pytest.raises(HTTPException) as exc_info:
            require_auth(request)

        assert exc_info.value.status_code == 303

    def test_require_admin_with_admin_user(self, db_conn, admin_user):
        """Test require_admin() returns user for admin users."""
        request = Mock(spec=Request)
        request.session = {"user_id": admin_user["id"]}

        result = require_admin(request)

        assert not isinstance(result, RedirectResponse)
        assert result["id"] == admin_user["id"]

    def test_require_admin_with_non_admin_user(self, db_conn, member_user):
        """Test require_admin() returns redirect for non-admin users."""
        request = Mock(spec=Request)
        request.session = {"user_id": member_user["id"]}

        result = require_admin(request)

        assert isinstance(result, RedirectResponse)

    def test_require_member_with_member(self, db_conn, member_user):
        """Test require_member() returns user for members."""
        request = Mock(spec=Request)
        request.session = {"user_id": member_user["id"]}

        user = require_member(request)

        assert user["id"] == member_user["id"]
        assert user["member"] is True

    def test_require_member_with_guest(self, db_conn, guest_user):
        """Test require_member() raises exception for guests."""
        request = Mock(spec=Request)
        request.session = {"user_id": guest_user["id"]}

        with pytest.raises(HTTPException) as exc_info:
            require_member(request)

        assert exc_info.value.status_code == 403
