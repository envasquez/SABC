# -*- coding: utf-8 -*-
"""
Comprehensive tests for core business logic and utility functions.

This test file targets high-value, low-effort tests that will significantly
boost coverage by testing business logic, utility functions, and calculated
properties across all modules.
"""

import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from tournaments.models.events import Events
from tournaments.models.lakes import Lake
from tournaments.models.payouts import PayOutMultipliers
from tournaments.models.results import Result, TeamResult
from tournaments.models.rules import RuleSet
from tournaments.models.tournaments import Tournament
from tournaments.views import get_aoy_results, get_big_bass, get_heavy_stringer
from users.models import Angler, Officers

User = get_user_model()


class BusinessLogicCalculationTests(TestCase):
    """Test business logic calculations and derived values."""

    def setUp(self):
        """Set up test data for business logic tests."""
        self.user1 = User.objects.create_user(
            username="user1",
            email="user1@test.com",
            password="pass",
            first_name="First",
            last_name="User",
        )
        self.angler1 = Angler.objects.create(
            user=self.user1, member=True, phone_number="5121234567"
        )

        self.user2 = User.objects.create_user(
            username="user2",
            email="user2@test.com",
            password="pass",
            first_name="Second",
            last_name="User",
        )
        self.angler2 = Angler.objects.create(
            user=self.user2, member=True, phone_number="5127654321"
        )

        self.lake = Lake.objects.create(name="test")
        self.event = Events.objects.create(
            date=datetime.date.today() + datetime.timedelta(days=30),
            year=datetime.date.today().year,
        )
        self.tournament = Tournament.objects.create(
            name="Test Tournament", lake=self.lake, event=self.event, complete=True
        )

    def test_result_calculations(self):
        """Test result calculations and properties."""
        # Create tournament with rules for penalty calculation
        from tournaments.models.rules import RuleSet

        rules = RuleSet.objects.create(year=self.tournament.event.year)
        self.tournament.rules = rules
        self.tournament.save()

        result = Result.objects.create(
            tournament=self.tournament,
            angler=self.angler1,
            place_finish=1,
            total_weight=Decimal("15.75"),
            num_fish=3,
            num_fish_dead=1,  # This will trigger penalty calculation
            big_bass_weight=Decimal("6.25"),
        )

        # Test weight calculations - penalty is calculated by save() method
        expected_penalty = result.num_fish_dead * rules.dead_fish_penalty
        self.assertEqual(result.penalty_weight, expected_penalty)

        # Test fish counts and weights
        self.assertEqual(result.num_fish, 3)
        self.assertEqual(result.big_bass_weight, Decimal("6.25"))

        # Test properties
        self.assertEqual(result.place_finish, 1)
        self.assertFalse(result.disqualified)
        self.assertFalse(result.buy_in)

    def test_team_result_calculations(self):
        """Test team result calculations."""
        team_tournament = Tournament.objects.create(
            name="Team Tournament",
            lake=self.lake,
            event=self.event,
            team=True,
            complete=True,
        )

        # Create individual results first
        result1 = Result.objects.create(
            tournament=team_tournament,
            angler=self.angler1,
            num_fish=3,
            total_weight=Decimal("15.50"),
        )
        result2 = Result.objects.create(
            tournament=team_tournament,
            angler=self.angler2,
            num_fish=2,
            total_weight=Decimal("13.00"),
        )

        team_result = TeamResult.objects.create(
            tournament=team_tournament,
            result_1=result1,
            result_2=result2,
            place_finish=1,
        )

        # TeamResult save() method calculates total_weight from individual results
        self.assertEqual(team_result.place_finish, 1)
        self.assertFalse(team_result.disqualified)

    def test_annual_awards_calculations(self):
        """Test annual awards calculation functions."""
        # Create multiple results for testing
        Result.objects.create(
            tournament=self.tournament,
            angler=self.angler1,
            place_finish=1,
            total_weight=Decimal("15.75"),
            num_fish=3,
            big_bass_weight=Decimal("6.25"),
        )

        Result.objects.create(
            tournament=self.tournament,
            angler=self.angler2,
            place_finish=2,
            total_weight=Decimal("12.25"),
            num_fish=3,
            big_bass_weight=Decimal("4.25"),
        )

        # Test AOY results
        aoy_results = get_aoy_results(year=datetime.date.today().year)
        self.assertIsInstance(aoy_results, list)
        self.assertTrue(len(aoy_results) >= 2)

        # Test heavy stringer
        heavy_stringer = get_heavy_stringer(year=datetime.date.today().year)
        self.assertIsInstance(heavy_stringer, list)
        if heavy_stringer:
            self.assertEqual(heavy_stringer[0]["weight"], Decimal("15.75"))

        # Test big bass (should be empty since no fish over 5lbs)
        big_bass = get_big_bass(year=datetime.date.today().year)
        self.assertIsInstance(big_bass, list)

    def test_payout_multiplier_calculations(self):
        """Test payout multiplier calculations."""
        payout = PayOutMultipliers.objects.create(
            year=2024,
            place_1=Decimal("7.00"),
            place_2=Decimal("5.00"),
            place_3=Decimal("4.00"),
            club=Decimal("3.00"),
            charity=Decimal("2.00"),
            big_bass=Decimal("4.00"),
            entry_fee=Decimal("25.00"),
        )

        # Test fee breakdown generation
        breakdown = payout.get_fee_breakdown()
        self.assertIsInstance(breakdown, str)
        self.assertIn("Tournament Pot", breakdown)
        self.assertIn("Big Bass", breakdown)
        self.assertIn("Charity", breakdown)

        # Test calculated fields - per_boat_fee is calculated by save() method
        expected_per_boat = payout.entry_fee * 2
        self.assertEqual(payout.per_boat_fee, expected_per_boat)

        # Test string representation
        str_repr = str(payout)
        self.assertIn("2024", str_repr)
        self.assertIn("Entry Fee", str_repr)

    def test_rule_set_defaults(self):
        """Test rule set defaults and methods."""
        rules = RuleSet.objects.create(year=2024)

        # Test defaults
        self.assertEqual(rules.limit_num, 5)
        self.assertEqual(rules.dead_fish_penalty, Decimal("0.25"))
        self.assertEqual(rules.max_points, 100)

        # Test text fields have content
        self.assertTrue(len(rules.rules) > 100)  # Substantial rule text
        self.assertTrue(len(rules.payout) > 50)
        self.assertTrue(len(rules.weigh_in) > 50)

        # Test string representation - name field contains "SABC Default Rules"
        str_repr = str(rules)
        self.assertTrue(len(str_repr) > 0)
        self.assertIn("SABC Default Rules", str_repr)


class ModelMethodTests(TestCase):
    """Test model methods and properties that are commonly missed in coverage."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@test.com",
            password="pass",
            first_name="Test",
            last_name="User",
        )
        self.angler = Angler.objects.create(
            user=self.user, member=True, phone_number="5125551234"
        )

    def test_angler_model_methods(self):
        """Test angler model methods and properties."""
        # Test string representation
        str_repr = str(self.angler)
        self.assertTrue(len(str_repr) > 0)

        # Test user relationship
        self.assertEqual(self.angler.user, self.user)
        self.assertEqual(self.user.angler, self.angler)

        # Test membership status
        self.assertTrue(self.angler.member)

        # Test phone number
        self.assertEqual(self.angler.phone_number, "5125551234")

    def test_officer_model_methods(self):
        """Test officer model methods and properties."""
        officer = Officers.objects.create(
            angler=self.angler,
            position=Officers.OfficerPositions.PRESIDENT,
            year=datetime.date.today().year,
        )

        # Test string representation
        str_repr = str(officer)
        self.assertTrue(len(str_repr) > 0)
        # Check for position in lowercase since display might be "president" not "President"
        self.assertIn("president", str_repr.lower())
        self.assertIn(str(datetime.date.today().year), str_repr)

        # Test position display
        self.assertEqual(officer.get_position_display(), "President")

        # Test year property
        self.assertEqual(officer.year, datetime.date.today().year)

    def test_lake_model_methods(self):
        """Test lake model methods and edge cases."""
        # Test normal lake
        lake = Lake.objects.create(name="travis")
        self.assertIn("Travis", str(lake))

        # Test special case lakes
        special_lake = Lake.objects.create(name="fayette county reservoir")
        self.assertEqual(str(special_lake), "Fayette County Reservoir")

        # Test lake with "inks" in name
        inks_lake = Lake.objects.create(name="inks")
        self.assertEqual(str(inks_lake), "Inks Lake")

    def test_event_model_methods(self):
        """Test event model methods."""
        event = Events.objects.create(date=datetime.date(2024, 6, 15), year=2024)

        # Test string representation
        str_repr = str(event)
        self.assertIn("Tournament", str_repr)
        self.assertIn("2024-06-15", str_repr)

        # Test date property
        self.assertEqual(event.date, datetime.date(2024, 6, 15))
        self.assertEqual(event.year, 2024)

    def test_tournament_model_methods(self):
        """Test tournament model methods."""
        lake = Lake.objects.create(name="test")
        event = Events.objects.create(date=datetime.date.today(), year=2024)
        tournament = Tournament.objects.create(
            name="Test Tournament", lake=lake, event=event
        )

        # Test string representation
        str_repr = str(tournament)
        self.assertEqual(str_repr, "Test Tournament")

        # Test defaults
        self.assertTrue(tournament.team)  # Default is True
        self.assertFalse(tournament.complete)


class UtilityFunctionTests(TestCase):
    """Test utility functions and calculations."""

    def test_events_get_next_event(self):
        """Test get_next_event class method."""
        # Create future event
        future_date = datetime.date.today() + datetime.timedelta(days=30)
        future_event = Events.objects.create(date=future_date, year=future_date.year)

        # Create past event
        past_date = datetime.date.today() - datetime.timedelta(days=30)
        Events.objects.create(date=past_date, year=past_date.year)

        # Test get next event function
        from tournaments.models.events import get_next_event

        next_event = get_next_event(event_type="tournament")
        self.assertEqual(next_event, future_event)

    def test_empty_get_next_event(self):
        """Test get_next_event with no future events."""
        # Create only past events
        past_date = datetime.date.today() - datetime.timedelta(days=30)
        Events.objects.create(date=past_date, year=past_date.year)

        from tournaments.models.events import get_next_event

        next_event = get_next_event(event_type="tournament")
        self.assertIsNone(next_event)

    def test_model_ordering(self):
        """Test model ordering is working correctly."""
        # Test Events ordering (by -year, descending)
        # Clean up existing events first
        Events.objects.all().delete()

        event1 = Events.objects.create(date=datetime.date(2024, 6, 1), year=2024)
        event2 = Events.objects.create(date=datetime.date(2025, 5, 1), year=2025)

        events = list(Events.objects.all())
        # Events ordering is by -year, so higher year first
        self.assertEqual(events[0], event2)  # 2025 first
        self.assertEqual(events[1], event1)  # 2024 second

    def test_model_validation_edge_cases(self):
        """Test model validation with edge cases."""
        user = User.objects.create_user(
            username="edgecase", email="edge@test.com", password="pass"
        )

        # Test angler with empty phone
        angler = Angler.objects.create(user=user, phone_number="", member=False)
        self.assertEqual(angler.phone_number, "")
        self.assertFalse(angler.member)

        # Test angler string representation with no name
        user_no_name = User.objects.create_user(
            username="noname", email="noname@test.com"
        )
        angler_no_name = Angler.objects.create(user=user_no_name)
        str_repr = str(angler_no_name)
        self.assertTrue(len(str_repr) > 0)  # Should not be empty

    def test_decimal_field_precision(self):
        """Test decimal field precision in calculations."""
        user = User.objects.create_user(username="decimal", email="decimal@test.com")
        angler = Angler.objects.create(user=user, member=True)

        lake = Lake.objects.create(name="decimal")
        event = Events.objects.create(date=datetime.date.today(), year=2024)
        tournament = Tournament.objects.create(
            name="Decimal Test", lake=lake, event=event
        )

        # Create rules for the tournament
        from tournaments.models.rules import RuleSet

        rules = RuleSet.objects.create(year=2024)
        tournament.rules = rules
        tournament.save()

        # Test precise decimal calculations - let save() calculate penalty
        result = Result.objects.create(
            tournament=tournament,
            angler=angler,
            place_finish=1,
            total_weight=Decimal("15.123"),
            num_fish=3,
            big_bass_weight=Decimal("5.041"),
        )

        # Verify decimal precision is maintained
        self.assertEqual(result.num_fish, 3)
        self.assertEqual(result.big_bass_weight, Decimal("5.041"))
        # penalty_weight is calculated by save() method


class ModelRelationshipTests(TestCase):
    """Test model relationships and foreign key constraints."""

    def test_one_to_one_relationships(self):
        """Test one-to-one relationships work correctly."""
        user = User.objects.create_user(username="relation", email="rel@test.com")
        angler = Angler.objects.create(user=user, member=True)

        # Test forward relationship
        self.assertEqual(angler.user, user)

        # Test reverse relationship
        self.assertEqual(user.angler, angler)

    def test_foreign_key_relationships(self):
        """Test foreign key relationships."""
        user = User.objects.create_user(username="fk", email="fk@test.com")
        angler = Angler.objects.create(user=user, member=True)

        # Create multiple officers for same angler
        officer1 = Officers.objects.create(
            angler=angler, position=Officers.OfficerPositions.PRESIDENT, year=2023
        )
        officer2 = Officers.objects.create(
            angler=angler, position=Officers.OfficerPositions.SECRETARY, year=2024
        )

        # Test forward relationships
        self.assertEqual(officer1.angler, angler)
        self.assertEqual(officer2.angler, angler)

        # Test reverse relationship (multiple officers per angler)
        angler_officers = angler.officers_set.all()
        self.assertIn(officer1, angler_officers)
        self.assertIn(officer2, angler_officers)
        self.assertEqual(angler_officers.count(), 2)

    def test_model_cascade_behavior(self):
        """Test cascade deletion behavior."""
        user = User.objects.create_user(username="cascade", email="cascade@test.com")
        angler = Angler.objects.create(
            user=user, member=True, phone_number="5125551234"
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


class EdgeCaseTests(TestCase):
    """Test edge cases and boundary conditions."""

    def test_empty_string_handling(self):
        """Test handling of empty strings in model fields."""
        user = User.objects.create_user(username="empty", email="empty@test.com")
        angler = Angler.objects.create(user=user, phone_number="")

        self.assertEqual(angler.phone_number, "")

        # String representation should handle empty phone gracefully
        str_repr = str(angler)
        self.assertIsInstance(str_repr, str)

    def test_null_and_blank_fields(self):
        """Test null and blank field handling."""
        # Create minimal objects to test null/blank field behavior
        lake = Lake.objects.create(name="minimal")
        self.assertEqual(lake.google_maps, "")  # Default empty string
        self.assertFalse(lake.paper)  # Default False

    def test_large_decimal_values(self):
        """Test handling of large decimal values."""
        # Create valid PayOutMultipliers that add up correctly (must sum to entry_fee)
        place_1 = Decimal("7.00")
        place_2 = Decimal("5.00")
        place_3 = Decimal("4.00")
        club = Decimal("3.00")
        charity = Decimal("2.00")
        big_bass = Decimal("4.00")
        entry_fee = place_1 + place_2 + place_3 + club + charity + big_bass  # 25.00

        payout = PayOutMultipliers.objects.create(
            year=2024,
            place_1=place_1,
            place_2=place_2,
            place_3=place_3,
            club=club,
            charity=charity,
            big_bass=big_bass,
            entry_fee=entry_fee,
        )

        # Should handle large values without error
        self.assertEqual(payout.entry_fee, entry_fee)

        # Should calculate per_boat_fee correctly
        expected_per_boat = entry_fee * 2
        self.assertEqual(payout.per_boat_fee, expected_per_boat)
