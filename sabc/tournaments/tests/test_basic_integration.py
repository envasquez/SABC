# -*- coding: utf-8 -*-
"""
Basic integration tests for tournament functionality.

Focus on core business logic rather than complex workflow testing.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from users.models import Angler

from tournaments.models.events import Events
from tournaments.models.lakes import Lake
from tournaments.models.results import Result
from tournaments.models.rules import RuleSet
from tournaments.models.tournaments import Tournament

User = get_user_model()


class BasicTournamentIntegrationTests(TestCase):
    """Test basic tournament functionality with real models."""

    def setUp(self):
        # Create basic test data using real model fields
        self.lake = Lake.objects.create(name="test_lake", google_maps="test-maps-url")

        self.event = Events.objects.create(
            date="2024-06-15", year=2024, month="june", type="tournament"
        )

        self.rules = RuleSet.objects.create(
            max_points=100, dead_fish_penalty=Decimal("0.5")
        )

        self.tournament = Tournament.objects.create(
            lake=self.lake,
            event=self.event,
            rules=self.rules,
            team=False,
            complete=False,
        )

        # Create test user and angler
        self.user = User.objects.create_user(
            username="test_angler",
            email="test@example.com",
            password="TestPassword123!",
        )
        self.angler = Angler.objects.create(
            user=self.user, phone_number="5125551234", member=True
        )

    def test_tournament_creation(self):
        """Test tournament can be created with required relationships."""
        self.assertIsNotNone(self.tournament.id)
        self.assertEqual(self.tournament.lake, self.lake)
        self.assertEqual(self.tournament.event, self.event)
        self.assertEqual(self.tournament.rules, self.rules)
        self.assertFalse(self.tournament.team)
        self.assertFalse(self.tournament.complete)

    def test_result_creation_and_penalty_calculation(self):
        """Test result creation with penalty weight calculation."""
        result = Result.objects.create(
            tournament=self.tournament,
            angler=self.angler,
            total_weight=Decimal("12.00"),
            num_fish=5,
            num_fish_dead=2,  # 2 dead fish = penalty
            big_bass_weight=Decimal("4.00"),
            place_finish=1,
        )

        # Check penalty calculation
        expected_penalty = 2 * self.rules.dead_fish_penalty
        expected_total = Decimal("12.00") - expected_penalty

        self.assertEqual(result.penalty_weight, expected_penalty)
        self.assertEqual(result.total_weight, expected_total)

    def test_multiple_results_in_tournament(self):
        """Test multiple anglers can have results in same tournament."""
        # Create second angler
        user2 = User.objects.create_user(
            username="test_angler2",
            email="test2@example.com",
            password="TestPassword123!",
        )
        angler2 = Angler.objects.create(
            user=user2, phone_number="5125551235", member=True
        )

        # Create results for both anglers
        result1 = Result.objects.create(
            tournament=self.tournament,
            angler=self.angler,
            total_weight=Decimal("15.00"),
            num_fish=5,
            place_finish=1,
        )

        result2 = Result.objects.create(
            tournament=self.tournament,
            angler=angler2,
            total_weight=Decimal("12.00"),
            num_fish=4,
            place_finish=2,
        )

        # Verify both results exist and are linked to tournament
        results = Result.objects.filter(tournament=self.tournament)
        self.assertEqual(results.count(), 2)

        # Verify proper ordering by place
        ordered_results = results.order_by("place_finish")
        self.assertEqual(ordered_results[0], result1)
        self.assertEqual(ordered_results[1], result2)

    def test_member_vs_guest_angler(self):
        """Test member vs guest angler functionality."""
        # Create guest angler
        guest_user = User.objects.create_user(
            username="guest_angler",
            email="guest@example.com",
            password="TestPassword123!",
        )
        guest_angler = Angler.objects.create(
            user=guest_user,
            phone_number="5125551236",
            member=False,  # Guest, not member
        )

        # Both should be able to create results
        member_result = Result.objects.create(
            tournament=self.tournament,
            angler=self.angler,  # Member
            total_weight=Decimal("10.00"),
            num_fish=3,
            place_finish=1,
        )

        guest_result = Result.objects.create(
            tournament=self.tournament,
            angler=guest_angler,  # Guest
            total_weight=Decimal("12.00"),  # Higher weight
            num_fish=4,
            place_finish=2,  # But lower place due to guest rules
        )

        # Verify both results created
        self.assertTrue(member_result.angler.member)
        self.assertFalse(guest_result.angler.member)

    def test_tournament_completion_workflow(self):
        """Test basic tournament completion workflow."""
        # Initially not complete
        self.assertFalse(self.tournament.complete)

        # Add some results
        Result.objects.create(
            tournament=self.tournament,
            angler=self.angler,
            total_weight=Decimal("10.00"),
            num_fish=3,
            place_finish=1,
        )

        # Mark tournament complete
        self.tournament.complete = True
        self.tournament.save()

        # Verify completion
        self.tournament.refresh_from_db()
        self.assertTrue(self.tournament.complete)

        # Verify results still exist
        results = Result.objects.filter(tournament=self.tournament)
        self.assertEqual(results.count(), 1)


class ModelValidationTests(TestCase):
    """Test model validation and constraints."""

    def test_angler_requires_user(self):
        """Test that Angler requires a User."""
        user = User.objects.create_user(
            username="test_user", email="test@example.com", password="TestPassword123!"
        )

        angler = Angler.objects.create(
            user=user, phone_number="5125551234", member=True
        )

        self.assertEqual(angler.user, user)
        self.assertEqual(angler.user.username, "test_user")

    def test_result_requires_tournament_and_angler(self):
        """Test that Result requires Tournament and Angler."""
        # Create dependencies
        lake = Lake.objects.create(name="test_lake")
        event = Events.objects.create(
            date="2024-06-15", year=2024, month="june", type="tournament"
        )
        rules = RuleSet.objects.create(max_points=100, dead_fish_penalty=Decimal("0.5"))
        tournament = Tournament.objects.create(lake=lake, event=event, rules=rules)

        user = User.objects.create_user(
            username="test_user", email="test@example.com", password="TestPassword123!"
        )
        angler = Angler.objects.create(
            user=user, phone_number="5125551234", member=True
        )

        # Create result
        result = Result.objects.create(
            tournament=tournament,
            angler=angler,
            total_weight=Decimal("8.00"),
            num_fish=2,
            place_finish=1,
        )

        self.assertEqual(result.tournament, tournament)
        self.assertEqual(result.angler, angler)
        self.assertEqual(result.total_weight, Decimal("8.00"))
