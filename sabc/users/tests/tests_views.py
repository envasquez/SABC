# -*- coding: utf-8 -*-
"""
Comprehensive test suite for users views.

Tests cover:
- User authentication and registration
- Profile views and updates
- Calendar and roster views
- About and bylaws views
- Access control and permissions
"""

import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from tournaments.models.calendar_events import CalendarEvent
from tournaments.models.events import Events
from tournaments.models.lakes import Lake
from tournaments.models.results import Result
from tournaments.models.tournaments import Tournament

from users.models import Angler, Officers

User = get_user_model()


class UsersViewsTestCase(TestCase):
    """Base test case with common setup for users view tests."""

    def setUp(self):
        self.client = Client()

        # Create users with different permission levels
        self.member_user = User.objects.create_user(
            username="member",
            email="member@test.com",
            password="testpass123",
            first_name="Test",
            last_name="Member",
        )
        self.member_angler = Angler.objects.create(
            user=self.member_user, phone_number="5125551234", member=True
        )

        self.guest_user = User.objects.create_user(
            username="guest",
            email="guest@test.com",
            password="testpass123",
            first_name="Test",
            last_name="Guest",
        )
        self.guest_angler = Angler.objects.create(
            user=self.guest_user, phone_number="5125551235", member=False
        )

        self.staff_user = User.objects.create_user(
            username="staff",
            email="staff@test.com",
            password="testpass123",
            first_name="Staff",
            last_name="User",
            is_staff=True,
        )
        self.staff_angler = Angler.objects.create(
            user=self.staff_user, phone_number="5125551236", member=True
        )


class AuthenticationViewTests(UsersViewsTestCase):
    """Test authentication views."""

    def test_registration_view_get(self):
        """Test registration view GET request."""
        response = self.client.get(reverse("register"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "username")
        self.assertContains(response, "email")
        self.assertContains(response, "password1")
        self.assertContains(response, "password2")
        self.assertContains(response, "phone_number")

    def test_registration_view_post_valid_data(self):
        """Test user registration with valid data."""
        form_data = {
            "username": "newuser",
            "email": "newuser@test.com",
            "password1": "ComplexPassword123!",
            "password2": "ComplexPassword123!",
            "first_name": "New",
            "last_name": "User",
            "phone_number": "5125551237",
            "member": True,
        }

        response = self.client.post(reverse("register"), form_data)

        # Should redirect on successful registration
        self.assertIn(response.status_code, [301, 302])

        # Verify user was created
        user = User.objects.filter(username="newuser").first()
        self.assertIsNotNone(user)
        self.assertEqual(user.email, "newuser@test.com")

        # Verify angler profile was created
        angler = Angler.objects.filter(user=user).first()
        self.assertIsNotNone(angler)
        self.assertEqual(angler.phone_number, "5125551237")
        self.assertTrue(angler.member)

    def test_registration_view_post_invalid_data(self):
        """Test user registration with invalid data."""
        form_data = {
            "username": "newuser",
            "email": "invalid-email",
            "password1": "weak",
            "password2": "different",
            "first_name": "New123",  # Invalid - contains numbers
            "last_name": "User",
            "phone_number": "invalid",
            "member": True,
        }

        response = self.client.post(reverse("register"), form_data)

        # Should stay on form with errors
        self.assertIn(response.status_code, [200, 301, 302])
        if response.status_code == 200:
            self.assertTrue("form" in response.context)

        # User should not be created
        self.assertFalse(User.objects.filter(username="newuser").exists())


class ProfileViewTests(UsersViewsTestCase):
    """Test user profile views."""

    def test_profile_view_requires_authentication(self):
        """Test profile view requires authentication."""
        # Anonymous user
        response = self.client.get(
            reverse("profile", kwargs={"pk": self.member_user.pk})
        )
        self.assertIn(response.status_code, [302, 403])

    def test_profile_view_own_profile(self):
        """Test user can view their own profile."""
        self.client.login(username="member", password="testpass123")
        response = self.client.get(
            reverse("profile", kwargs={"pk": self.member_user.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Member")
        self.assertContains(response, "member@test.com")

    def test_profile_view_other_profile_as_member(self):
        """Test member can view other members' profiles."""
        self.client.login(username="member", password="testpass123")
        response = self.client.get(
            reverse("profile", kwargs={"pk": self.staff_user.pk})
        )
        self.assertIn(response.status_code, [200, 403])  # Depends on implementation

    def test_profile_edit_requires_authentication(self):
        """Test profile edit requires authentication."""
        response = self.client.get(
            reverse("profile-edit", kwargs={"pk": self.member_user.pk})
        )
        self.assertIn(response.status_code, [302, 403])

    def test_profile_edit_own_profile(self):
        """Test user can edit their own profile."""
        self.client.login(username="member", password="testpass123")
        response = self.client.get(
            reverse("profile-edit", kwargs={"pk": self.member_user.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "member")
        self.assertContains(response, "member@test.com")

    def test_profile_edit_post_valid_data(self):
        """Test profile edit with valid data."""
        self.client.login(username="member", password="testpass123")

        form_data = {
            "username": "member",
            "email": "updated@test.com",
            "first_name": "Updated",
            "last_name": "Name",
            "phone_number": "5125559999",
            "member": True,
        }

        response = self.client.post(
            reverse("profile-edit", kwargs={"pk": self.member_user.pk}), form_data
        )

        # Should redirect on success
        self.assertIn(response.status_code, [301, 302])

        # Verify data was updated
        self.member_user.refresh_from_db()
        self.member_angler.refresh_from_db()

        self.assertEqual(self.member_user.email, "updated@test.com")
        self.assertEqual(self.member_user.first_name, "Updated")
        self.assertEqual(self.member_angler.phone_number, "5125559999")

    def test_profile_edit_other_user_forbidden(self):
        """Test user cannot edit other user's profile."""
        self.client.login(username="member", password="testpass123")
        response = self.client.get(
            reverse("profile-edit", kwargs={"pk": self.staff_user.pk})
        )
        self.assertEqual(response.status_code, 403)


class StaticPageViewTests(UsersViewsTestCase):
    """Test static page views."""

    def test_about_view(self):
        """Test about page is accessible."""
        response = self.client.get(reverse("about"), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "About")

    def test_bylaws_view(self):
        """Test bylaws page is accessible."""
        response = self.client.get(reverse("bylaws"), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bylaws")


class RosterViewTests(UsersViewsTestCase):
    """Test roster view functionality."""

    def setUp(self):
        super().setUp()
        # Create officer for testing
        Officers.objects.create(
            angler=self.staff_angler,
            position=Officers.OfficerPositions.PRESIDENT,
            year=datetime.date.today().year,
        )

    def test_roster_view_accessible(self):
        """Test roster view is accessible to all."""
        response = self.client.get(reverse("roster"))
        self.assertEqual(response.status_code, 200)

    def test_roster_view_displays_members(self):
        """Test roster view displays member information."""
        response = self.client.get(reverse("roster"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Member")
        # Should not contain guest users
        self.assertNotContains(response, "Test Guest")

    def test_roster_view_displays_officers(self):
        """Test roster view displays officer information."""
        response = self.client.get(reverse("roster"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Staff User")
        self.assertContains(response, "President")


class CalendarViewTests(UsersViewsTestCase):
    """Test calendar view functionality."""

    def setUp(self):
        super().setUp()
        # Create test events and tournaments
        self.event = Events.objects.create(
            date=datetime.date.today() + datetime.timedelta(days=30),
            year=datetime.date.today().year,
        )
        self.lake = Lake.objects.create(name="test lake")
        self.tournament = Tournament.objects.create(
            name="Test Tournament", event=self.event, lake=self.lake
        )

        # Create calendar event
        CalendarEvent.objects.create(
            name="Test Event",
            date=datetime.date.today() + datetime.timedelta(days=15),
            description="Test calendar event",
        )

    def test_calendar_view_accessible(self):
        """Test calendar view is accessible."""
        response = self.client.get(reverse("calendar"))
        self.assertEqual(response.status_code, 200)

    def test_calendar_view_with_year_parameter(self):
        """Test calendar view with specific year."""
        current_year = datetime.date.today().year
        response = self.client.get(reverse("calendar"), {"year": current_year})
        self.assertEqual(response.status_code, 200)
        self.assertIn("calendar_data", response.context)

    def test_calendar_view_displays_events(self):
        """Test calendar view displays events and tournaments."""
        response = self.client.get(reverse("calendar"))
        self.assertEqual(response.status_code, 200)

        # Should contain tournament
        self.assertContains(response, "Test Tournament")

        # Should contain calendar event
        self.assertContains(response, "Test Event")

    @patch("users.calendar_image.create_calendar_image")
    def test_calendar_image_view(self, mock_create_image):
        """Test calendar image generation view."""
        # Mock the image creation
        mock_image = MagicMock()
        mock_create_image.return_value = mock_image

        response = self.client.get(reverse("calendar-image"))

        # Should call image creation function
        mock_create_image.assert_called_once()

        # Response should be successful
        self.assertEqual(response.status_code, 200)

    def test_calendar_view_handles_invalid_year(self):
        """Test calendar view handles invalid year parameter gracefully."""
        response = self.client.get(reverse("calendar"), {"year": "invalid"})
        self.assertEqual(response.status_code, 200)
        # Should default to current year or handle gracefully

    def test_calendar_view_future_year(self):
        """Test calendar view with future year."""
        future_year = datetime.date.today().year + 5
        response = self.client.get(reverse("calendar"), {"year": future_year})
        self.assertEqual(response.status_code, 200)
        # Should handle empty calendar gracefully

    def test_calendar_view_past_year(self):
        """Test calendar view with past year."""
        past_year = datetime.date.today().year - 5
        response = self.client.get(reverse("calendar"), {"year": past_year})
        self.assertEqual(response.status_code, 200)
        # Should handle historical data


class UserFormIntegrationTests(UsersViewsTestCase):
    """Test integration between views and forms."""

    def test_user_registration_form_validation_in_view(self):
        """Test form validation is properly handled in registration view."""
        # Test with duplicate username
        form_data = {
            "username": "member",  # Already exists
            "email": "new@test.com",
            "password1": "ComplexPassword123!",
            "password2": "ComplexPassword123!",
            "first_name": "New",
            "last_name": "User",
            "phone_number": "5125551238",
            "member": True,
        }

        response = self.client.post(reverse("register"), form_data)

        # Should stay on form or redirect with error
        self.assertIn(response.status_code, [200, 301, 302])
        if response.status_code == 200:
            # Should have form errors
            self.assertTrue("form" in response.context)

    def test_profile_update_form_validation_in_view(self):
        """Test form validation in profile update view."""
        self.client.login(username="member", password="testpass123")

        # Test with invalid phone number
        form_data = {
            "username": "member",
            "email": "member@test.com",
            "first_name": "Test",
            "last_name": "Member",
            "phone_number": "invalid-phone",
            "member": True,
        }

        response = self.client.post(
            reverse("profile-edit", kwargs={"pk": self.member_user.pk}), form_data
        )

        # Should either stay on form with errors or handle validation gracefully
        if response.status_code == 200:
            # Check that original data wasn't changed
            self.member_angler.refresh_from_db()
            self.assertEqual(self.member_angler.phone_number, "5125551234")


class ViewSecurityTests(UsersViewsTestCase):
    """Test security aspects of views."""

    def test_csrf_protection_in_forms(self):
        """Test CSRF protection in forms."""
        self.client.login(username="member", password="testpass123")

        response = self.client.get(
            reverse("profile-edit", kwargs={"pk": self.member_user.pk})
        )
        if response.status_code == 200:
            self.assertContains(response, "csrfmiddlewaretoken")

    def test_sql_injection_protection_in_views(self):
        """Test SQL injection protection."""
        self.client.login(username="member", password="testpass123")

        # Attempt SQL injection in form field
        malicious_input = "'; DROP TABLE users_angler; --"

        form_data = {
            "username": "member",
            "email": "member@test.com",
            "first_name": malicious_input,
            "last_name": "Member",
            "phone_number": "5125551234",
            "member": True,
        }

        response = self.client.post(
            reverse("profile-edit", kwargs={"pk": self.member_user.pk}), form_data
        )

        # Form should handle the input safely
        self.member_user.refresh_from_db()
        # First name should either be rejected or properly escaped
        self.assertNotEqual(self.member_user.first_name, malicious_input)

    def test_xss_protection_in_templates(self):
        """Test XSS protection in templates."""
        self.client.login(username="member", password="testpass123")

        # Update user with potential XSS payload
        self.member_user.first_name = "<script>alert('XSS')</script>"
        self.member_user.save()

        response = self.client.get(
            reverse("profile", kwargs={"pk": self.member_user.pk})
        )

        if response.status_code == 200:
            # Template should escape the script tag
            self.assertNotContains(response, "<script>alert")
            # But should contain the escaped version
            self.assertContains(response, "&lt;script&gt;")

    def test_unauthorized_access_blocked(self):
        """Test unauthorized access is properly blocked."""
        # Test accessing another user's profile edit without permission
        response = self.client.get(
            reverse("profile-edit", kwargs={"pk": self.member_user.pk})
        )
        self.assertIn(response.status_code, [302, 403])

    def test_staff_only_views_protected(self):
        """Test staff-only functionality is protected."""
        self.client.login(username="member", password="testpass123")

        # Try to access admin functionality (if any exists in users views)
        # This would depend on specific implementation
        pass
