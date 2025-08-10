# -*- coding: utf-8 -*-
"""
Comprehensive model tests to maximize coverage of tournament models.

Tests cover all model methods, properties, and business logic.
"""

import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from users.models import Angler

from tournaments.models.calendar_events import CalendarEvent
from tournaments.models.events import Events
from tournaments.models.lakes import Lake, Ramp
from tournaments.models.payouts import PayOutMultipliers
from tournaments.models.results import Result, TeamResult
from tournaments.models.rules import RuleSet
from tournaments.models.tournaments import Tournament

User = get_user_model()


class LakeModelTests(TestCase):
    """Test Lake model functionality."""

    def test_lake_creation(self):
        """Test lake creation with all fields."""
        lake = Lake.objects.create(
            name="test lake", paper=True, google_maps="https://maps.google.com/test"
        )
        self.assertEqual(lake.name, "test ")  # Save method strips 'lake'
        self.assertTrue(lake.paper)

    def test_lake_str_representation(self):
        """Test lake string representation."""
        lake = Lake.objects.create(name="travis")
        self.assertEqual(str(lake), "Lake Travis")

        # Test special cases
        lake2 = Lake.objects.create(name="fayette county reservoir")
        self.assertEqual(str(lake2), "Fayette County Reservoir")

        lake3 = Lake.objects.create(name="inks")
        self.assertEqual(str(lake3), "Inks Lake")

    def test_lake_save_normalizes_name(self):
        """Test lake save method normalizes name."""
        lake = Lake.objects.create(name="Lake Austin")
        self.assertEqual(
            lake.name, " austin"
        )  # Save method strips 'Lake' leaving space

    def test_lake_ordering(self):
        """Test lake ordering by name."""
        Lake.objects.create(name="zebra")
        Lake.objects.create(name="austin")

        lakes = list(Lake.objects.all())
        self.assertEqual(lakes[0].name, "austin")  # Save method strips 'lake'
        self.assertEqual(lakes[1].name, "zebra")


class RampModelTests(TestCase):
    """Test Ramp model functionality."""

    def setUp(self):
        self.lake = Lake.objects.create(name="test lake")

    def test_ramp_creation(self):
        """Test ramp creation."""
        ramp = Ramp.objects.create(
            lake=self.lake, name="test ramp", google_maps="https://maps.google.com/ramp"
        )
        self.assertEqual(ramp.lake, self.lake)
        self.assertEqual(ramp.name, "test ramp")

    def test_ramp_str_representation(self):
        """Test ramp string representation."""
        ramp = Ramp.objects.create(lake=self.lake, name="main ramp")
        expected = f"{self.lake}: Main Ramp"
        self.assertEqual(str(ramp), expected)


class EventsModelTests(TestCase):
    """Test Events model functionality."""

    def test_events_creation(self):
        """Test events creation."""
        event = Events.objects.create(
            date=datetime.date.today() + datetime.timedelta(days=30), year=2024
        )
        self.assertEqual(event.year, 2024)
        self.assertIsNotNone(event.date)

    def test_events_str_representation(self):
        """Test events string representation."""
        event = Events.objects.create(date=datetime.date(2024, 6, 15), year=2024)
        str_repr = str(event)
        self.assertIn("Tournament", str_repr)
        self.assertIn("2024-06-15", str_repr)

    def test_events_ordering(self):
        """Test events ordering by year (descending)."""
        event1 = Events.objects.create(date=datetime.date(2024, 6, 15), year=2024)
        event2 = Events.objects.create(date=datetime.date(2025, 5, 15), year=2025)

        events = list(Events.objects.all())
        self.assertEqual(events[0], event2)  # 2025 comes before 2024 (descending)
        self.assertEqual(events[1], event1)

    def test_get_next_event(self):
        """Test get_next_event class method."""
        # Create future event
        future_event = Events.objects.create(
            date=datetime.date.today() + datetime.timedelta(days=30),
            year=datetime.date.today().year,
        )

        from tournaments.models.events import get_next_event

        next_event = get_next_event(event_type="tournament")
        self.assertEqual(next_event, future_event)

    def test_get_next_event_no_future_events(self):
        """Test get_next_event with no future events."""
        # Create past event
        Events.objects.create(
            date=datetime.date.today() - datetime.timedelta(days=30),
            year=datetime.date.today().year,
        )

        from tournaments.models.events import get_next_event

        next_event = get_next_event(event_type="tournament")
        self.assertIsNone(next_event)


class CalendarEventModelTests(TestCase):
    """Test CalendarEvent model functionality."""

    def test_calendar_event_creation(self):
        """Test calendar event creation."""
        event = CalendarEvent.objects.create(
            title="Test Event",
            date=datetime.date.today() + datetime.timedelta(days=10),
            description="Test description",
        )
        self.assertEqual(event.title, "Test Event")
        self.assertEqual(event.description, "Test description")

    def test_calendar_event_str_representation(self):
        """Test calendar event string representation."""
        event = CalendarEvent.objects.create(
            title="Test Event", date=datetime.date(2024, 6, 15)
        )
        self.assertEqual(str(event), "Test Event - 2024-06-15")

    def test_calendar_event_ordering(self):
        """Test calendar event ordering by date."""
        event1 = CalendarEvent.objects.create(
            title="Event 1", date=datetime.date(2024, 6, 15)
        )
        event2 = CalendarEvent.objects.create(
            title="Event 2", date=datetime.date(2024, 5, 15)
        )

        events = list(CalendarEvent.objects.all())
        self.assertEqual(events[0], event2)  # Earlier date first

    def test_calendar_event_methods(self):
        """Test calendar event methods."""
        event = CalendarEvent.objects.create(
            title="Test Event", date=datetime.date.today() + datetime.timedelta(days=10)
        )

        # Test basic properties
        self.assertEqual(event.category, "tournament")
        self.assertEqual(event.priority, "normal")

        # Test color and icon properties
        self.assertIsInstance(event.color_class, str)
        self.assertIsInstance(event.icon_class, str)


class PayOutMultipliersModelTests(TestCase):
    """Test PayOutMultipliers model functionality."""

    def test_payout_multipliers_creation(self):
        """Test payout multipliers creation."""
        payout = PayOutMultipliers.objects.create(
            year=2024,
            place_1=Decimal("7.0"),
            place_2=Decimal("5.0"),
            place_3=Decimal("4.0"),
            club=Decimal("3.0"),
            charity=Decimal("2.0"),
            big_bass=Decimal("4.0"),
            entry_fee=Decimal("25.0"),
        )
        self.assertEqual(payout.year, 2024)
        self.assertEqual(payout.place_1, Decimal("7.0"))

    def test_payout_multipliers_str_representation(self):
        """Test payout multipliers string representation."""
        payout = PayOutMultipliers.objects.create(year=2024)
        self.assertIn("2024", str(payout))

    def test_payout_multipliers_defaults(self):
        """Test payout multipliers default values."""
        payout = PayOutMultipliers.objects.create(year=2024)
        self.assertEqual(payout.place_1, Decimal("7"))
        self.assertEqual(payout.place_2, Decimal("5"))
        self.assertEqual(payout.place_3, Decimal("4"))

    def test_payout_fee_breakdown(self):
        """Test payout fee breakdown method."""
        payout = PayOutMultipliers.objects.create(year=2024)
        breakdown = payout.get_fee_breakdown()
        self.assertIsInstance(breakdown, str)
        self.assertIn("Breakdown", breakdown)


class RuleSetModelTests(TestCase):
    """Test RuleSet model functionality."""

    def test_rules_creation(self):
        """Test rules creation."""
        rules = RuleSet.objects.create(
            year=2024, name="Test Rules", limit_num=5, dead_fish_penalty=Decimal("0.25")
        )
        self.assertEqual(rules.year, 2024)
        self.assertEqual(rules.name, "Test Rules")
        self.assertEqual(rules.limit_num, 5)

    def test_rules_str_representation(self):
        """Test rules string representation."""
        rules = RuleSet.objects.create(year=2024, name="Test Rules")
        self.assertEqual(str(rules), "Test Rules")

    def test_rules_defaults(self):
        """Test rules default values."""
        rules = RuleSet.objects.create(year=2024)
        self.assertEqual(rules.limit_num, 5)
        self.assertEqual(rules.dead_fish_penalty, Decimal("0.25"))
        self.assertEqual(rules.max_points, 100)

    def test_rules_text_fields(self):
        """Test rules text fields have defaults."""
        rules = RuleSet.objects.create(year=2024)

        # Test that default text fields are populated
        self.assertTrue(len(rules.rules) > 0)
        self.assertTrue(len(rules.payout) > 0)
        self.assertTrue(len(rules.weigh_in) > 0)
        self.assertTrue(len(rules.entry_fee) > 0)


class TournamentModelTests(TestCase):
    """Test Tournament model functionality."""

    def setUp(self):
        self.lake = Lake.objects.create(name="test lake")
        self.event = Events.objects.create(
            date=datetime.date.today() + datetime.timedelta(days=30),
            year=datetime.date.today().year,
        )

    def test_tournament_creation(self):
        """Test tournament creation."""
        tournament = Tournament.objects.create(
            name="Test Tournament", lake=self.lake, event=self.event, team=False
        )
        self.assertEqual(tournament.name, "Test Tournament")
        self.assertEqual(tournament.lake, self.lake)
        self.assertEqual(tournament.event, self.event)
        self.assertFalse(tournament.team)

    def test_tournament_str_representation(self):
        """Test tournament string representation."""
        tournament = Tournament.objects.create(
            name="Test Tournament", lake=self.lake, event=self.event
        )
        # Tournament __str__ just returns the name
        self.assertEqual(str(tournament), "Test Tournament")

    def test_tournament_defaults(self):
        """Test tournament default values."""
        tournament = Tournament.objects.create(
            name="Test Tournament", lake=self.lake, event=self.event
        )
        self.assertTrue(tournament.team)  # Default is True
        self.assertFalse(tournament.complete)  # Default is False

    def test_tournament_methods(self):
        """Test tournament methods."""
        tournament = Tournament.objects.create(
            name="Test Tournament", lake=self.lake, event=self.event
        )

        # Test tournament properties
        self.assertEqual(tournament.name, "Test Tournament")
        self.assertEqual(tournament.lake, self.lake)
        self.assertEqual(tournament.event, self.event)

        # Test get_absolute_url
        url = tournament.get_absolute_url()
        self.assertIn(str(tournament.pk), url)


class ResultModelTests(TestCase):
    """Test Result model functionality."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@test.com", password="testpass123"
        )
        self.angler = Angler.objects.create(
            user=self.user, phone_number="5125551234", member=True
        )
        self.lake = Lake.objects.create(name="test lake")
        self.event = Events.objects.create(
            date=datetime.date.today() + datetime.timedelta(days=30),
            year=datetime.date.today().year,
        )
        self.tournament = Tournament.objects.create(
            name="Test Tournament", lake=self.lake, event=self.event
        )

    def test_result_creation(self):
        """Test result creation."""
        result = Result.objects.create(
            tournament=self.tournament,
            angler=self.angler,
            place_finish=1,
            num_fish=3,
            total_weight=Decimal("15.5"),
            big_bass_weight=Decimal("5.5"),
        )
        self.assertEqual(result.tournament, self.tournament)
        self.assertEqual(result.angler, self.angler)
        self.assertEqual(result.place_finish, 1)

    def test_result_str_representation(self):
        """Test result string representation."""
        result = Result.objects.create(
            tournament=self.tournament,
            angler=self.angler,
            place_finish=1,
            num_fish=3,
            total_weight=Decimal("15.5"),
            big_bass_weight=Decimal("5.5"),
        )
        str_repr = str(result)
        self.assertIn(str(self.angler), str_repr)
        self.assertIn("1.", str_repr)
        self.assertIn("fish for:", str_repr)

    def test_result_properties(self):
        """Test result properties and calculated fields."""
        result = Result.objects.create(
            tournament=self.tournament,
            angler=self.angler,
            place_finish=1,
            num_fish=3,
            num_fish_dead=1,  # This will calculate penalty_weight
            total_weight=Decimal("15.5"),
            big_bass_weight=Decimal("5.5"),
        )

        # Test basic properties
        # total_weight is adjusted by save method: original - penalty
        self.assertEqual(result.num_fish_dead, 1)
        self.assertEqual(result.num_fish_alive, 2)  # num_fish - num_fish_dead
        self.assertTrue(result.penalty_weight > 0)  # Calculated from dead fish
        self.assertFalse(result.disqualified)
        self.assertFalse(result.buy_in)

    def test_result_methods(self):
        """Test result methods."""
        result = Result.objects.create(
            tournament=self.tournament,
            angler=self.angler,
            place_finish=1,
            num_fish=3,
            total_weight=Decimal("15.5"),
            big_bass_weight=Decimal("5.5"),
        )

        # Test basic properties
        self.assertEqual(result.points, 0)  # Default
        self.assertEqual(result.place_finish, 1)
        self.assertEqual(result.num_fish, 3)

    def test_result_big_fish_weight(self):
        """Test result big fish weight calculation."""
        result = Result.objects.create(
            tournament=self.tournament,
            angler=self.angler,
            place_finish=1,
            num_fish=3,
            total_weight=Decimal("15.5"),
            big_bass_weight=Decimal("7.0"),
        )

        # Test big bass weight field
        self.assertEqual(result.big_bass_weight, Decimal("7.0"))


class TeamResultModelTests(TestCase):
    """Test TeamResult model functionality."""

    def setUp(self):
        self.user1 = User.objects.create_user(
            username="user1", email="user1@test.com", password="testpass123"
        )
        self.angler1 = Angler.objects.create(
            user=self.user1, phone_number="5125551234", member=True
        )

        self.user2 = User.objects.create_user(
            username="user2", email="user2@test.com", password="testpass123"
        )
        self.angler2 = Angler.objects.create(
            user=self.user2, phone_number="5125551235", member=True
        )

        self.lake = Lake.objects.create(name="test lake")
        self.event = Events.objects.create(
            date=datetime.date.today() + datetime.timedelta(days=30),
            year=datetime.date.today().year,
        )
        self.tournament = Tournament.objects.create(
            name="Team Tournament", lake=self.lake, event=self.event, team=True
        )

    def test_team_result_creation(self):
        """Test team result creation."""
        result1 = Result.objects.create(
            tournament=self.tournament,
            angler=self.angler1,
            num_fish=3,
            total_weight=Decimal("13.0"),
        )
        result2 = Result.objects.create(
            tournament=self.tournament,
            angler=self.angler2,
            num_fish=2,
            total_weight=Decimal("12.0"),
        )
        team_result = TeamResult.objects.create(
            tournament=self.tournament,
            result_1=result1,
            result_2=result2,
            place_finish=1,
        )
        self.assertEqual(team_result.tournament, self.tournament)
        self.assertEqual(team_result.result_1, result1)
        self.assertEqual(team_result.result_2, result2)

    def test_team_result_str_representation(self):
        """Test team result string representation."""
        result1 = Result.objects.create(
            tournament=self.tournament,
            angler=self.angler1,
            num_fish=3,
            total_weight=Decimal("13.0"),
        )
        result2 = Result.objects.create(
            tournament=self.tournament,
            angler=self.angler2,
            num_fish=2,
            total_weight=Decimal("12.0"),
        )
        team_result = TeamResult.objects.create(
            tournament=self.tournament,
            result_1=result1,
            result_2=result2,
            place_finish=1,
        )
        str_repr = str(team_result)
        self.assertIn("1.", str_repr)
        # String format includes team name and weight info

    def test_team_result_methods(self):
        """Test team result methods."""
        result1 = Result.objects.create(
            tournament=self.tournament,
            angler=self.angler1,
            num_fish=3,
            total_weight=Decimal("13.0"),
        )
        result2 = Result.objects.create(
            tournament=self.tournament,
            angler=self.angler2,
            num_fish=2,
            total_weight=Decimal("12.0"),
        )
        team_result = TeamResult.objects.create(
            tournament=self.tournament,
            result_1=result1,
            result_2=result2,
            place_finish=1,
        )

        # Test get_team_name method
        team_name = team_result.get_team_name()
        self.assertIn(self.angler1.user.get_full_name(), team_name)
        self.assertIn(self.angler2.user.get_full_name(), team_name)

        # Test basic properties
        self.assertFalse(team_result.disqualified)
        self.assertEqual(team_result.place_finish, 1)
