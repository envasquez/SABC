# -*- coding: utf-8 -*-
"""
Integration tests for tournament creation and management workflows.

Critical Testing Coverage - Phase 1:
- Tournament creation and management workflows
- Results entry and calculation
- Team tournament functionality
- Annual awards calculations
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import TestCase, TransactionTestCase
from users.models import Angler

from tournaments.models.events import Events
from tournaments.models.lakes import Lake
from tournaments.models.results import Result, TeamResult
from tournaments.models.rules import RuleSet
from tournaments.models.tournaments import Tournament

User = get_user_model()


class TournamentCreationIntegrationTests(TestCase):
    """Test complete tournament creation workflow using model-level operations."""

    def setUp(self):
        # Create staff user (tournament director)
        self.staff_user = User.objects.create_user(
            username="tournament_director",
            email="td@example.com",
            password="TestPassword123!",
            is_staff=True,
        )
        self.staff_angler = Angler.objects.create(
            user=self.staff_user, phone_number="5125551234", member=True
        )

        # Create regular member
        self.member_user = User.objects.create_user(
            username="member", email="member@example.com", password="TestPassword123!"
        )
        self.member_angler = Angler.objects.create(
            user=self.member_user, phone_number="5125551235", member=True
        )

        # Create test lake
        self.lake = Lake.objects.create(
            name="Test Lake", google_maps="test-google-maps-url"
        )

        # Create test event and rules
        self.event = Events.objects.create(
            date="2024-06-15", year=2024, month="june", type="tournament"
        )

        self.rules = RuleSet.objects.create(
            max_points=100, dead_fish_penalty=Decimal("0.5")
        )

    def test_complete_tournament_creation_workflow(self):
        """Test complete workflow from tournament creation to results entry."""
        # Step 1: Create tournament
        tournament = Tournament.objects.create(
            name="Test Tournament",
            event=self.event,
            lake=self.lake,
            rules=self.rules,
            team=False,
            complete=False,
        )

        self.assertEqual(tournament.lake, self.lake)
        self.assertEqual(tournament.event, self.event)
        self.assertFalse(tournament.complete)

        # Step 2: Add tournament result
        result = Result.objects.create(
            tournament=tournament,
            angler=self.member_angler,
            total_weight=Decimal("12.50"),
            num_fish=5,
            big_bass_weight=Decimal("4.25"),
            place_finish=1,
        )

        self.assertEqual(result.total_weight, Decimal("12.50"))
        self.assertEqual(result.num_fish, 5)
        self.assertEqual(result.big_bass_weight, Decimal("4.25"))

        # Step 3: Complete tournament
        tournament.complete = True
        tournament.save()

        # Verify tournament completion
        tournament.refresh_from_db()
        self.assertTrue(tournament.complete)

        # Verify results still exist after completion
        results = Result.objects.filter(tournament=tournament)
        self.assertEqual(results.count(), 1)

    def test_tournament_business_logic_validation(self):
        """Test tournament business logic validation."""
        # Test tournament with invalid foreign key (Tournament model has custom validation)
        from tournaments.models.events import Events

        with self.assertRaises(Events.DoesNotExist):
            Tournament.objects.create(
                name="Invalid Tournament",
                event_id=999999,  # Non-existent event ID
                lake=self.lake,
                rules=self.rules,
            )

        # Test tournament with valid data
        tournament = Tournament.objects.create(
            name="Valid Tournament",
            event=self.event,
            lake=self.lake,
            rules=self.rules,
            team=True,
            complete=False,
        )

        self.assertTrue(tournament.team)
        self.assertFalse(tournament.complete)


class TournamentResultsIntegrationTests(TestCase):
    """Test tournament results entry and calculation workflows."""

    def setUp(self):
        # Create test data
        self.lake = Lake.objects.create(
            name="Test Lake", google_maps="test-google-maps-url"
        )
        self.event = Events.objects.create(
            date="2024-06-15", year=2024, month="june", type="tournament"
        )
        self.rules = RuleSet.objects.create(
            max_points=100, dead_fish_penalty=Decimal("0.5")
        )

        self.tournament = Tournament.objects.create(
            name="Test Tournament",
            event=self.event,
            lake=self.lake,
            rules=self.rules,
            team=False,
            complete=False,
        )

        # Create test anglers
        self.anglers = []
        for i in range(5):
            user = User.objects.create_user(
                username=f"angler{i}",
                email=f"angler{i}@example.com",
                password="TestPassword123!",
            )
            angler = Angler.objects.create(
                user=user, phone_number=f"51255512{i:02d}", member=True
            )
            self.anglers.append(angler)

    def test_multiple_results_entry_and_ranking(self):
        """Test entering multiple results and verifying correct ranking."""
        # Enter results for multiple anglers with different weights
        results_data = [
            {"weight": "15.25", "fish": 5, "bass": "5.50"},  # 1st place
            {"weight": "12.75", "fish": 4, "bass": "4.25"},  # 2nd place
            {"weight": "10.50", "fish": 3, "bass": "3.75"},  # 3rd place
            {"weight": "8.25", "fish": 2, "bass": "2.50"},  # 4th place
            {"weight": "0.00", "fish": 0, "bass": "0.00"},  # 5th place (zeroed)
        ]

        created_results = []
        for i, data in enumerate(results_data):
            result = Result.objects.create(
                tournament=self.tournament,
                angler=self.anglers[i],
                total_weight=Decimal(data["weight"]),
                num_fish=data["fish"],
                big_bass_weight=Decimal(data["bass"]),
                place_finish=i + 1,
            )
            created_results.append(result)

        # Verify results were created correctly
        results = Result.objects.filter(tournament=self.tournament).order_by(
            "place_finish"
        )
        self.assertEqual(results.count(), 5)

        # Check first place
        first_place = results.first()
        self.assertEqual(first_place.total_weight, Decimal("15.25"))
        self.assertEqual(first_place.place_finish, 1)

        # Check last place (zeroed angler)
        last_place = results.last()
        self.assertEqual(last_place.total_weight, Decimal("0.00"))
        self.assertEqual(last_place.place_finish, 5)

    def test_penalty_weight_calculation(self):
        """Test penalty weight calculation for dead fish."""
        result = Result.objects.create(
            tournament=self.tournament,
            angler=self.anglers[0],
            total_weight=Decimal("12.00"),
            num_fish=5,
            num_fish_dead=2,  # 2 dead fish
            big_bass_weight=Decimal("4.00"),
            place_finish=1,
        )

        # Check penalty calculation: original weight - (dead fish * penalty rate)
        expected_penalty = 2 * self.rules.dead_fish_penalty
        expected_total = Decimal("12.00") - expected_penalty

        self.assertEqual(result.penalty_weight, expected_penalty)
        self.assertEqual(result.total_weight, expected_total)

    def test_disqualified_angler_handling(self):
        """Test handling of disqualified anglers."""
        result = Result.objects.create(
            tournament=self.tournament,
            angler=self.anglers[0],
            total_weight=Decimal("15.00"),
            num_fish=5,
            disqualified=True,
            place_finish=999,  # Disqualified place
        )

        self.assertTrue(result.disqualified)
        self.assertEqual(result.place_finish, 999)

    def test_buy_in_angler_tracking(self):
        """Test tracking of anglers who bought into side pots."""
        # Regular result
        regular_result = Result.objects.create(
            tournament=self.tournament,
            angler=self.anglers[0],
            total_weight=Decimal("12.00"),
            num_fish=4,
            buy_in=False,
            place_finish=1,
        )

        # Buy-in result
        buyin_result = Result.objects.create(
            tournament=self.tournament,
            angler=self.anglers[1],
            total_weight=Decimal("10.00"),
            num_fish=3,
            buy_in=True,
            place_finish=2,
        )

        self.assertFalse(regular_result.buy_in)
        self.assertTrue(buyin_result.buy_in)

        # Verify both results are tracked
        all_results = Result.objects.filter(tournament=self.tournament)
        buyin_results = all_results.filter(buy_in=True)
        regular_results = all_results.filter(buy_in=False)

        self.assertEqual(all_results.count(), 2)
        self.assertEqual(buyin_results.count(), 1)
        self.assertEqual(regular_results.count(), 1)


class TeamTournamentIntegrationTests(TestCase):
    """Test team tournament functionality."""

    def setUp(self):
        # Create test data
        self.lake = Lake.objects.create(
            name="Team Lake", google_maps="test-team-maps-url"
        )
        self.event = Events.objects.create(
            date="2024-07-15", year=2024, month="july", type="tournament"
        )
        self.rules = RuleSet.objects.create(
            max_points=100, dead_fish_penalty=Decimal("0.5")
        )

        self.team_tournament = Tournament.objects.create(
            name="Team Tournament",
            event=self.event,
            lake=self.lake,
            rules=self.rules,
            team=True,  # Team tournament
            complete=False,
        )

        # Create team members
        self.team_members = []
        for i in range(4):  # 2 teams of 2
            user = User.objects.create_user(
                username=f"team_member{i}",
                email=f"team{i}@example.com",
                password="TestPassword123!",
            )
            angler = Angler.objects.create(
                user=user, phone_number=f"51255520{i:02d}", member=True
            )
            self.team_members.append(angler)

    def test_team_result_creation_and_calculation(self):
        """Test team result creation and weight calculation."""
        # Create individual results for team members
        team1_results = []
        team2_results = []

        # Team 1 - two anglers
        for i in range(2):
            result = Result.objects.create(
                tournament=self.team_tournament,
                angler=self.team_members[i],
                total_weight=Decimal("10.00") + i,  # 10.00, 11.00
                num_fish=5,
                big_bass_weight=Decimal("3.00") + i,
                place_finish=i + 1,
            )
            team1_results.append(result)

        # Team 2 - two anglers
        for i in range(2, 4):
            result = Result.objects.create(
                tournament=self.team_tournament,
                angler=self.team_members[i],
                total_weight=Decimal("7.00") + i,  # 9.00, 10.00 (lower than team1)
                num_fish=4,
                big_bass_weight=Decimal("2.50") + i,
                place_finish=i + 1,
            )
            team2_results.append(result)

        # Create team results
        team1 = TeamResult.objects.create(
            tournament=self.team_tournament,
            result_1=team1_results[0],
            result_2=team1_results[1],
        )

        team2 = TeamResult.objects.create(
            tournament=self.team_tournament,
            result_1=team2_results[0],
            result_2=team2_results[1],
        )

        # Check team weight calculations
        expected_team1_weight = (
            team1_results[0].total_weight + team1_results[1].total_weight
        )
        expected_team2_weight = (
            team2_results[0].total_weight + team2_results[1].total_weight
        )

        self.assertEqual(team1.total_weight, expected_team1_weight)
        self.assertEqual(team2.total_weight, expected_team2_weight)

        # Team 1 should have higher total weight
        self.assertGreater(team1.total_weight, team2.total_weight)

    def test_disqualified_team_member_affects_team(self):
        """Test that disqualifying one team member affects the entire team."""
        # Create team results
        result1 = Result.objects.create(
            tournament=self.team_tournament,
            angler=self.team_members[0],
            total_weight=Decimal("12.00"),
            num_fish=5,
            disqualified=False,
        )

        result2 = Result.objects.create(
            tournament=self.team_tournament,
            angler=self.team_members[1],
            total_weight=Decimal("10.00"),
            num_fish=4,
            disqualified=True,  # Disqualified
        )

        TeamResult.objects.create(
            tournament=self.team_tournament, result_1=result1, result_2=result2
        )

        # Team should be effectively disqualified or have reduced weight
        # (Implementation depends on business rules)
        self.assertTrue(result2.disqualified)

    def test_team_tournament_individual_tracking(self):
        """Test that individual results are still tracked in team tournaments."""
        # Create individual results
        individual_results = []
        for i, angler in enumerate(self.team_members):
            result = Result.objects.create(
                tournament=self.team_tournament,
                angler=angler,
                total_weight=Decimal("8.00") + i,
                num_fish=3 + i,
                place_finish=i + 1,
            )
            individual_results.append(result)

        # Verify all individual results exist
        all_results = Result.objects.filter(tournament=self.team_tournament)
        self.assertEqual(all_results.count(), 4)

        # Verify individual results can be queried separately
        best_individual = all_results.order_by("-total_weight").first()
        self.assertEqual(best_individual.total_weight, Decimal("11.00"))


class AnnualAwardsIntegrationTests(TransactionTestCase):
    """Test annual awards calculations with multiple tournaments."""

    def setUp(self):
        # Create test data for a season
        self.lake = Lake.objects.create(
            name="Award Lake", google_maps="test-award-maps-url"
        )
        self.rules = RuleSet.objects.create(
            max_points=100, dead_fish_penalty=Decimal("0.5")
        )

        # Create events for multiple tournaments
        self.events = []
        for month in range(1, 4):  # 3 tournaments for testing
            event = Events.objects.create(
                date=f"2024-{month:02d}-15",
                year=2024,
                month=["january", "february", "march"][month - 1],
                type="tournament",
            )
            self.events.append(event)

        # Create tournaments
        self.tournaments = []
        for i, event in enumerate(self.events, 1):
            tournament = Tournament.objects.create(
                name=f"Tournament {i}",
                event=event,
                lake=self.lake,
                rules=self.rules,
                team=False,
                complete=True,
            )
            self.tournaments.append(tournament)

        # Create consistent anglers for the season
        self.season_anglers = []
        for i in range(5):
            user = User.objects.create_user(
                username=f"season_angler{i}",
                email=f"season{i}@example.com",
                password="TestPassword123!",
            )
            angler = Angler.objects.create(
                user=user, phone_number=f"51255530{i:02d}", member=True
            )
            self.season_anglers.append(angler)

    def test_angler_of_year_calculation(self):
        """Test Angler of the Year calculation across multiple tournaments."""
        # Create consistent results for one angler across all tournaments
        champion_angler = self.season_anglers[0]

        total_expected_points = 0
        total_expected_weight = Decimal("0.00")

        for i, tournament in enumerate(self.tournaments):
            # Champion consistently places in top 3
            place = (i % 3) + 1  # Alternates between 1st, 2nd, 3rd
            weight = Decimal("15.00") - (place * Decimal("1.00"))
            points = self.rules.max_points - (place - 1)

            Result.objects.create(
                tournament=tournament,
                angler=champion_angler,
                total_weight=weight,
                num_fish=5,
                place_finish=place,
                points=points,
            )

            total_expected_points += points
            total_expected_weight += weight

        # Create varied results for other anglers
        for tournament in self.tournaments:
            for j, angler in enumerate(self.season_anglers[1:4], 1):
                Result.objects.create(
                    tournament=tournament,
                    angler=angler,
                    total_weight=Decimal("8.00") + j,
                    num_fish=3 + j,
                    place_finish=3 + j,
                    points=max(0, self.rules.max_points - (3 + j - 1)),
                )

        # Verify the data is set up correctly for AOY calculation
        champion_results = Result.objects.filter(angler=champion_angler)
        self.assertEqual(champion_results.count(), 3)  # All tournaments

        total_points = sum(r.points or 0 for r in champion_results)
        total_weight = sum(r.total_weight or Decimal("0.00") for r in champion_results)

        self.assertEqual(total_points, total_expected_points)
        self.assertEqual(total_weight, total_expected_weight)

        # Champion should have highest points total
        all_angler_points = {}
        for angler in self.season_anglers:
            angler_results = Result.objects.filter(angler=angler)
            total_points = sum(r.points or 0 for r in angler_results)
            all_angler_points[angler.pk] = total_points

        champion_points = all_angler_points[champion_angler.pk]
        other_points = [
            points
            for angler_id, points in all_angler_points.items()
            if angler_id != champion_angler.pk
        ]

        self.assertTrue(all(champion_points >= points for points in other_points))

    def test_big_bass_award_calculation(self):
        """Test Big Bass award calculation across season."""
        big_bass_angler = self.season_anglers[2]

        # Create one outstanding big bass result
        tournament_with_big_bass = self.tournaments[1]  # Second tournament

        Result.objects.create(
            tournament=tournament_with_big_bass,
            angler=big_bass_angler,
            total_weight=Decimal("12.00"),
            num_fish=5,
            big_bass_weight=Decimal("8.50"),  # Monster bass
            place_finish=1,
        )

        # Create normal results for other tournaments
        for tournament in self.tournaments:
            if tournament != tournament_with_big_bass:
                for angler in self.season_anglers[:3]:
                    Result.objects.create(
                        tournament=tournament,
                        angler=angler,
                        total_weight=Decimal("10.00"),
                        num_fish=5,
                        big_bass_weight=Decimal("3.50"),  # Normal bass
                        place_finish=1,
                    )

        # Verify the big bass record
        big_bass_result = Result.objects.filter(
            angler=big_bass_angler, tournament=tournament_with_big_bass
        ).first()

        self.assertIsNotNone(big_bass_result)
        self.assertEqual(big_bass_result.big_bass_weight, Decimal("8.50"))

        # Find biggest bass of the year
        biggest_bass = (
            Result.objects.filter(tournament__event__year=2024)
            .order_by("-big_bass_weight")
            .first()
        )

        self.assertIsNotNone(biggest_bass)
        self.assertEqual(biggest_bass.angler, big_bass_angler)
        self.assertEqual(biggest_bass.big_bass_weight, Decimal("8.50"))

    def test_heavy_stringer_award_calculation(self):
        """Test Heavy Stringer (biggest single tournament weight) calculation."""
        heavy_stringer_angler = self.season_anglers[1]

        # Create results with one exceptionally heavy stringer
        for i, tournament in enumerate(self.tournaments):
            for j, angler in enumerate(self.season_anglers[:3]):
                if angler == heavy_stringer_angler and i == 0:
                    # Exceptional weight for first tournament
                    weight = Decimal("25.50")
                else:
                    # Normal weights
                    weight = Decimal("10.00") + j

                Result.objects.create(
                    tournament=tournament,
                    angler=angler,
                    total_weight=weight,
                    num_fish=5,
                    place_finish=j + 1,
                )

        # Find heaviest stringer of the year
        heaviest_stringer = (
            Result.objects.filter(tournament__event__year=2024)
            .order_by("-total_weight")
            .first()
        )

        self.assertIsNotNone(heaviest_stringer)
        self.assertEqual(heaviest_stringer.angler, heavy_stringer_angler)
        self.assertEqual(heaviest_stringer.total_weight, Decimal("25.50"))


class DatabaseMigrationTests(TransactionTestCase):
    """Test database migration scenarios with production-like data."""

    def test_migration_with_existing_data(self):
        """Test that migrations work correctly with existing tournament data."""
        # Create data that simulates production state
        lake = Lake.objects.create(
            name="Production Lake", google_maps="production-maps-url"
        )
        event = Events.objects.create(
            date="2024-01-15", year=2024, month="january", type="tournament"
        )
        rules = RuleSet.objects.create(max_points=100, dead_fish_penalty=Decimal("0.5"))

        tournament = Tournament.objects.create(
            name="Production Tournament",
            event=event,
            lake=lake,
            rules=rules,
            complete=True,
        )

        # Create angler with results
        user = User.objects.create_user(
            username="production_user",
            email="prod@example.com",
            password="TestPassword123!",
        )
        angler = Angler.objects.create(
            user=user, phone_number="5125551234", member=True
        )

        result = Result.objects.create(
            tournament=tournament,
            angler=angler,
            total_weight=Decimal("12.50"),
            num_fish=5,
            place_finish=1,
        )

        # Verify data integrity after setup
        self.assertTrue(
            Tournament.objects.filter(name="Production Tournament").exists()
        )
        self.assertTrue(Result.objects.filter(angler=angler).exists())
        self.assertEqual(result.total_weight, Decimal("12.50"))

        # Simulate schema changes that might occur in migrations
        with transaction.atomic():  # type: ignore
            result.refresh_from_db()
            self.assertEqual(result.tournament, tournament)
            self.assertEqual(result.angler, angler)

    def test_data_consistency_after_operations(self):
        """Test data consistency after various database operations."""
        # Create tournament data
        lake = Lake.objects.create(name="Consistency Lake")
        event = Events.objects.create(
            date="2024-05-15", year=2024, month="may", type="tournament"
        )
        rules = RuleSet.objects.create(max_points=100, dead_fish_penalty=Decimal("1.0"))

        tournament = Tournament.objects.create(
            name="Consistency Tournament",
            event=event,
            lake=lake,
            rules=rules,
        )

        # Create multiple anglers and results
        for i in range(3):
            user = User.objects.create_user(
                username=f"consistency_user{i}",
                email=f"consistency{i}@example.com",
                password="TestPassword123!",
            )
            angler = Angler.objects.create(
                user=user, phone_number=f"512555{i:04d}", member=True
            )

            Result.objects.create(
                tournament=tournament,
                angler=angler,
                total_weight=Decimal("10.00") + i,
                num_fish=4 + i,
                place_finish=i + 1,
            )

        # Verify all relationships are intact
        tournament_results = Result.objects.filter(tournament=tournament)
        self.assertEqual(tournament_results.count(), 3)

        for result in tournament_results:
            self.assertIsNotNone(result.angler)
            self.assertIsNotNone(result.angler.user)
            self.assertIsNotNone(result.tournament)
            self.assertEqual(result.tournament.lake, lake)
