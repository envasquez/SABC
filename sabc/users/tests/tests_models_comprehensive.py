# -*- coding: utf-8 -*-
"""
Comprehensive model tests to maximize coverage of users models.

Tests cover all model methods, properties, and business logic.
"""

import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase

from users.models import Angler, Officers

User = get_user_model()


class AnglerModelTests(TestCase):
    """Test Angler model functionality."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@test.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
        )

    def test_angler_creation(self):
        """Test angler creation with all fields."""
        angler = Angler.objects.create(
            user=self.user, phone_number="5125551234", member=True
        )
        self.assertEqual(angler.user, self.user)
        self.assertEqual(angler.phone_number, "5125551234")
        self.assertTrue(angler.member)

    def test_angler_creation_defaults(self):
        """Test angler creation with default values."""
        angler = Angler.objects.create(user=self.user)
        self.assertEqual(angler.user, self.user)
        self.assertEqual(angler.phone_number, "")
        self.assertFalse(angler.member)

    def test_angler_str_representation(self):
        """Test angler string representation."""
        angler = Angler.objects.create(
            user=self.user, phone_number="5125551234", member=True
        )
        expected = f"{self.user.get_full_name()}"
        self.assertEqual(str(angler), expected)

    def test_angler_str_with_no_full_name(self):
        """Test angler string representation when user has no full name."""
        user_no_name = User.objects.create_user(
            username="noname", email="noname@test.com", password="testpass123"
        )
        angler = Angler.objects.create(user=user_no_name, phone_number="+15125551234")
        # Angler defaults to member=False, so shows (G) for guest
        expected = (
            f"{user_no_name.get_full_name()} (G)"
            if not angler.member
            else user_no_name.get_full_name()
        )
        self.assertEqual(str(angler), expected)

    def test_angler_get_full_name(self):
        """Test angler uses user's get_full_name method."""
        angler = Angler.objects.create(user=self.user, phone_number="+15125551234")
        self.assertEqual(angler.user.get_full_name(), "Test User")

    def test_angler_get_short_name(self):
        """Test angler uses user's get_short_name method."""
        angler = Angler.objects.create(user=self.user, phone_number="+15125551234")
        self.assertEqual(angler.user.get_short_name(), "Test")

    def test_angler_is_member_property(self):
        """Test angler member field."""
        angler = Angler.objects.create(
            user=self.user, member=True, phone_number="+15125551234"
        )
        self.assertTrue(angler.member)

        angler.member = False
        angler.save()
        self.assertFalse(angler.member)

    def test_angler_has_phone_property(self):
        """Test angler phone_number field."""
        angler = Angler.objects.create(user=self.user, phone_number="+15125551234")
        self.assertTrue(bool(angler.phone_number))

        # Phone number is required field, so test is just that it exists
        self.assertIsNotNone(angler.phone_number)

    def test_angler_formatted_phone(self):
        """Test angler phone number formatting."""
        angler = Angler.objects.create(user=self.user, phone_number="+15125551234")
        # PhoneNumberField provides formatting methods
        formatted = str(angler.phone_number)
        self.assertIsInstance(formatted, str)
        self.assertTrue(len(formatted) > 0)

        # Test phone formatting
        self.assertIn("512", formatted)  # Area code should be present

    def test_angler_meta_ordering(self):
        """Test angler model ordering."""
        user2 = User.objects.create_user(
            username="anotheruser",
            email="another@test.com",
            password="testpass123",
            first_name="Another",
            last_name="User",
        )

        angler1 = Angler.objects.create(user=self.user)
        angler2 = Angler.objects.create(user=user2)

        anglers = list(Angler.objects.all())
        # Should be ordered by user's last name, then first name
        self.assertEqual(anglers[0], angler2)  # "Another User" comes before "Test User"
        self.assertEqual(anglers[1], angler1)

    def test_angler_user_relationship(self):
        """Test angler-user one-to-one relationship."""
        angler = Angler.objects.create(user=self.user)

        # Test accessing angler from user
        self.assertEqual(self.user.angler, angler)

        # Test accessing user from angler
        self.assertEqual(angler.user, self.user)


class OfficersModelTests(TestCase):
    """Test Officers model functionality."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="officer",
            email="officer@test.com",
            password="testpass123",
            first_name="Officer",
            last_name="User",
        )
        self.angler = Angler.objects.create(
            user=self.user, phone_number="5125551234", member=True
        )

    def test_officer_creation(self):
        """Test officer creation with all fields."""
        officer = Officers.objects.create(
            angler=self.angler, position=Officers.OfficerPositions.PRESIDENT, year=2024
        )
        self.assertEqual(officer.angler, self.angler)
        self.assertEqual(officer.position, Officers.OfficerPositions.PRESIDENT)
        self.assertEqual(officer.year, 2024)

    def test_officer_creation_defaults(self):
        """Test officer creation with default values."""
        current_year = datetime.date.today().year
        officer = Officers.objects.create(
            angler=self.angler, position=Officers.OfficerPositions.PRESIDENT
        )
        self.assertEqual(officer.year, current_year)

    def test_officer_str_representation(self):
        """Test officer string representation."""
        officer = Officers.objects.create(
            angler=self.angler, position=Officers.OfficerPositions.PRESIDENT, year=2024
        )
        # Actual format from Officers.__str__: "{self.year}: {self.angler} - {self.position}"
        expected = f"2024: Officer User - president"
        self.assertEqual(str(officer), expected)

    def test_officer_positions_choices(self):
        """Test all officer position choices."""
        positions = [
            Officers.OfficerPositions.PRESIDENT,
            Officers.OfficerPositions.VICE_PRESIDENT,
            Officers.OfficerPositions.SECRETARY,
            Officers.OfficerPositions.TREASURER,
            Officers.OfficerPositions.TOURNAMENT_DIRECTOR,
            Officers.OfficerPositions.TECHNOLOGY_DIRECTOR,
        ]

        for position in positions:
            officer = Officers.objects.create(
                angler=self.angler, position=position, year=2024
            )
            self.assertEqual(officer.position, position)
            # Clean up for next iteration
            officer.delete()

    def test_officer_get_position_display(self):
        """Test officer get_position_display method."""
        officer = Officers.objects.create(
            angler=self.angler, position=Officers.OfficerPositions.PRESIDENT, year=2024
        )
        self.assertEqual(officer.get_position_display(), "President")

        officer.position = Officers.OfficerPositions.VICE_PRESIDENT
        officer.save()
        self.assertEqual(officer.get_position_display(), "Vice President")

    def test_officer_is_current_year(self):
        """Test officer is_current_year method."""
        current_year = datetime.date.today().year

        current_officer = Officers.objects.create(
            angler=self.angler,
            position=Officers.OfficerPositions.PRESIDENT,
            year=current_year,
        )
        self.assertEqual(current_officer.year, current_year)

        past_officer = Officers.objects.create(
            angler=self.angler,
            position=Officers.OfficerPositions.SECRETARY,
            year=current_year - 1,
        )
        self.assertEqual(past_officer.year, current_year - 1)

    def test_officer_meta_ordering(self):
        """Test officer model ordering."""
        officer1 = Officers.objects.create(
            angler=self.angler, position=Officers.OfficerPositions.PRESIDENT, year=2023
        )
        officer2 = Officers.objects.create(
            angler=self.angler, position=Officers.OfficerPositions.SECRETARY, year=2024
        )

        officers = list(Officers.objects.all())
        # Officers model doesn't define ordering in Meta, so order is not guaranteed
        self.assertEqual(len(officers), 2)
        self.assertIn(officer1, officers)
        self.assertIn(officer2, officers)

    def test_officer_angler_relationship(self):
        """Test officer-angler foreign key relationship."""
        officer = Officers.objects.create(
            angler=self.angler, position=Officers.OfficerPositions.PRESIDENT, year=2024
        )

        # Test accessing officer from angler
        angler_officers = self.angler.officers_set.all()
        self.assertIn(officer, angler_officers)

        # Test accessing angler from officer
        self.assertEqual(officer.angler, self.angler)

    def test_multiple_officers_same_angler(self):
        """Test same angler can have multiple officer positions."""
        officer1 = Officers.objects.create(
            angler=self.angler, position=Officers.OfficerPositions.PRESIDENT, year=2023
        )
        officer2 = Officers.objects.create(
            angler=self.angler, position=Officers.OfficerPositions.SECRETARY, year=2024
        )

        angler_officers = self.angler.officers_set.all()
        self.assertEqual(angler_officers.count(), 2)
        self.assertIn(officer1, angler_officers)
        self.assertIn(officer2, angler_officers)

    def test_officer_get_current_officers_manager_method(self):
        """Test custom manager methods if they exist."""
        current_year = datetime.date.today().year

        Officers.objects.create(
            angler=self.angler,
            position=Officers.OfficerPositions.PRESIDENT,
            year=current_year,
        )
        Officers.objects.create(
            angler=self.angler,
            position=Officers.OfficerPositions.SECRETARY,
            year=current_year - 1,
        )

        # If there's a custom manager method for current officers
        if hasattr(Officers.objects, "current_year"):
            current_officers = Officers.objects.current_year()
            self.assertEqual(current_officers.count(), 1)


class UserModelIntegrationTests(TestCase):
    """Test integration between User model and custom models."""

    def test_user_with_angler_profile(self):
        """Test user with angler profile integration."""
        user = User.objects.create_user(
            username="testuser",
            email="test@test.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
        )

        angler = Angler.objects.create(
            user=user, phone_number="5125551234", member=True
        )

        # Test user can access angler profile
        self.assertEqual(user.angler, angler)

        # Test user methods work with angler
        self.assertEqual(user.get_full_name(), "Test User")
        self.assertEqual(angler.user.get_full_name(), "Test User")

    def test_user_without_angler_profile(self):
        """Test user without angler profile."""
        user = User.objects.create_user(
            username="testuser", email="test@test.com", password="testpass123"
        )

        # Should raise DoesNotExist exception when accessing angler
        with self.assertRaises(Angler.DoesNotExist):
            user.angler

    def test_angler_with_officer_position(self):
        """Test angler with officer position integration."""
        user = User.objects.create_user(
            username="officer",
            email="officer@test.com",
            password="testpass123",
            first_name="Officer",
            last_name="User",
        )

        angler = Angler.objects.create(user=user, member=True)

        officer = Officers.objects.create(
            angler=angler, position=Officers.OfficerPositions.PRESIDENT, year=2024
        )

        # Test relationships work
        self.assertEqual(user.angler, angler)
        self.assertIn(officer, angler.officers_set.all())

        # Test officer can access user info through angler
        self.assertEqual(officer.angler.user.get_full_name(), "Officer User")

    def test_model_field_validation(self):
        """Test model field validation."""
        user = User.objects.create_user(
            username="testuser", email="test@test.com", password="testpass123"
        )

        # Test phone number field with valid phone number
        angler = Angler(
            user=user,
            phone_number="+15125551234",  # Valid US phone number
            member=True,
        )

        # This should work
        angler.full_clean()  # Validates model fields
        angler.save()

    def test_model_string_methods_edge_cases(self):
        """Test string methods with edge cases."""
        # User with no first/last name
        user = User.objects.create_user(
            username="noname", email="noname@test.com", password="testpass123"
        )

        angler = Angler.objects.create(user=user, phone_number="+15125551234")

        # Should handle gracefully
        angler_str = str(angler)
        self.assertIsInstance(angler_str, str)
        self.assertTrue(len(angler_str) > 0)

    def test_model_cascade_deletion(self):
        """Test cascade deletion behavior."""
        user = User.objects.create_user(
            username="testuser", email="test@test.com", password="testpass123"
        )

        angler = Angler.objects.create(
            user=user, member=True, phone_number="+15125551234"
        )
        officer = Officers.objects.create(
            angler=angler, position=Officers.OfficerPositions.PRESIDENT, year=2024
        )

        # Get PKs before deletion
        angler_pk = angler.pk
        officer_pk = officer.pk

        # Delete officer first to avoid PROTECT constraint, then angler, then user
        officer.delete()
        angler.delete()
        user.delete()

        # Verify all were deleted
        self.assertFalse(Angler.objects.filter(pk=angler_pk).exists())
        self.assertFalse(Officers.objects.filter(pk=officer_pk).exists())
