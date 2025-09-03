"""
Django management command to generate team tournaments with realistic data.

Usage:
    python manage.py generate_team_tournaments
    python manage.py generate_team_tournaments --years 2023 2024
    python manage.py generate_team_tournaments --clear
    python manage.py generate_team_tournaments --paper-count 5
    python manage.py generate_team_tournaments --big-bass-percent 40
"""

import random
import math
from datetime import date, timedelta, time, datetime
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.contrib.auth.models import User

from tournaments.models.events import Events
from tournaments.models.lakes import Lake, Ramp
from tournaments.models.tournaments import Tournament
from tournaments.models.results import Result, TeamResult
from users.models import Angler
from polls.models import LakePoll, LakeVote


class Command(BaseCommand):
    help = 'Generate team tournaments with realistic data including results, team pairings, and voting'

    def calculate_sunrise_time(self, tournament_date):
        """
        Calculate approximate sunrise time for Austin, TX area.
        This is a simplified calculation for tournament scheduling.
        """
        # Austin, TX approximate coordinates: 30.2672°N, 97.7431°W
        latitude = 30.2672
        
        # Day of year
        day_of_year = tournament_date.timetuple().tm_yday
        
        # Solar declination (simplified)
        declination = 23.45 * math.sin(math.radians(360 * (284 + day_of_year) / 365))
        
        # Hour angle for sunrise
        hour_angle = math.degrees(math.acos(-math.tan(math.radians(latitude)) * 
                                           math.tan(math.radians(declination))))
        
        # Sunrise time in hours from solar noon (simplified, no time zone adjustment)
        sunrise_hour = 12 - (hour_angle / 15)
        
        # Adjust for Central Time (roughly UTC-6) and add some variation
        sunrise_hour = sunrise_hour - 6 + random.uniform(-0.3, 0.3)  # Add slight randomness
        
        # Clamp to reasonable range (5:30 AM to 7:30 AM)
        sunrise_hour = max(5.5, min(7.5, sunrise_hour))
        
        # Convert to time object
        hours = int(sunrise_hour)
        minutes = int((sunrise_hour - hours) * 60)
        
        return time(hours, minutes)

    def generate_tournament_times(self, tournament_date):
        """Generate realistic start and weigh-in times for a tournament"""
        sunrise = self.calculate_sunrise_time(tournament_date)
        
        # Start 15-45 minutes before sunrise
        start_offset_minutes = random.randint(15, 45)
        start_hour = sunrise.hour
        start_minute = sunrise.minute - start_offset_minutes
        
        # Handle minute underflow
        if start_minute < 0:
            start_minute += 60
            start_hour -= 1
        
        # Handle hour underflow (shouldn't happen with our sunrise range)
        if start_hour < 0:
            start_hour += 24
        
        start_time = time(start_hour, start_minute)
        
        # Weigh-in is typically 8 hours later
        tournament_duration_hours = 8
        weigh_in_hour = start_hour + tournament_duration_hours
        weigh_in_minute = start_minute
        
        # Handle hour overflow
        if weigh_in_hour >= 24:
            weigh_in_hour -= 24
        
        weigh_in_time = time(weigh_in_hour, weigh_in_minute)
        
        return start_time, weigh_in_time

    def create_completed_poll_for_tournament(self, tournament, selected_lake):
        """Create a completed poll that shows the voting process that selected this lake"""
        from polls.models import LakePoll, LakeVote
        
        # Get all non-paper lakes for poll choices
        all_lakes = list(Lake.objects.filter(paper=False))
        
        # Create the poll (end date should be before tournament date)
        poll_end_date = tournament.event.date - timedelta(days=random.randint(7, 14))
        
        poll = LakePoll.objects.create(
            name=f"Location Poll: {tournament.name}",
            description=f"Vote for the location of {tournament.name}",
            end_date=poll_end_date,
            complete=True  # Mark as completed
        )
        
        # Add all lakes as choices
        poll.choices.set(all_lakes)
        
        # Create realistic voting pattern
        # The selected lake should win, but with realistic competition
        voting_members = list(Angler.objects.filter(member=True)[:random.randint(15, 25)])
        
        # Distribute votes with selected lake getting plurality
        total_votes = len(voting_members)
        selected_lake_votes = random.randint(int(total_votes * 0.35), int(total_votes * 0.55))  # 35-55% of votes
        
        # Give votes to selected lake
        voters_for_selected = random.sample(voting_members, selected_lake_votes)
        for voter in voters_for_selected:
            LakeVote.objects.create(
                poll=poll,
                angler=voter,
                choice=selected_lake
            )
        
        # Distribute remaining votes among other lakes
        remaining_voters = [v for v in voting_members if v not in voters_for_selected]
        other_lakes = [lake for lake in all_lakes if lake != selected_lake]
        
        for voter in remaining_voters:
            if other_lakes:  # Make sure there are other lakes to vote for
                voted_lake = random.choice(other_lakes)
                LakeVote.objects.create(
                    poll=poll,
                    angler=voter,
                    choice=voted_lake
                )
        
        # Associate poll with tournament event (polls are now linked to events, not tournaments)
        poll.event = tournament.event
        poll.save()
        
        # Verify the poll relationship
        if not tournament.event.polls.exists():
            self.stdout.write(
                self.style.ERROR(f"ERROR: Failed to associate poll with tournament event {tournament.name}")
            )
        
        # Log voting results
        vote_count = LakeVote.objects.filter(poll=poll, choice=selected_lake).count()
        total_poll_votes = LakeVote.objects.filter(poll=poll).count()
        self.stdout.write(
            f"  -> Created completed poll: {selected_lake.name} won with {vote_count}/{total_poll_votes} votes"
        )
        
        # Double-check that the winning lake matches the tournament lake
        if tournament.lake != selected_lake:
            self.stdout.write(
                self.style.ERROR(f"ERROR: Lake mismatch! Tournament lake: {tournament.lake}, Poll winner: {selected_lake}")
            )

    def add_arguments(self, parser):
        parser.add_argument(
            '--years',
            nargs='+',
            type=int,
            default=[2023, 2024],
            help='Years to generate tournaments for (default: 2023 2024)'
        )
        parser.add_argument(
            '--months-2025',
            type=int,
            default=7,
            help='Number of months to generate for 2025 (default: 7)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all existing tournament data before generating'
        )
        parser.add_argument(
            '--paper-count',
            type=int,
            default=0,
            help='Number of paper tournaments to create randomly (default: 0 - disabled)'
        )
        parser.add_argument(
            '--big-bass-percent',
            type=int,
            default=30,
            help='Percentage of tournaments with big bass (default: 30)'
        )
        parser.add_argument(
            '--zero-catch-percent',
            type=int,
            default=18,
            help='Percentage of anglers who catch zero fish (default: 18)'
        )
        parser.add_argument(
            '--create-upcoming',
            action='store_true',
            default=True,
            help='Create upcoming tournament for next month (default: True)'
        )

    def get_nth_sunday(self, year, month, n):
        """Get the nth Sunday of a month, or the last Sunday if n > count"""
        first_day = date(year, month, 1)
        # Find first Sunday
        days_until_sunday = (6 - first_day.weekday()) % 7
        first_sunday = first_day + timedelta(days=days_until_sunday)
        
        # Calculate all Sundays in the month
        sundays = []
        current = first_sunday
        while current.month == month:
            sundays.append(current)
            current += timedelta(days=7)
        
        # Return 4th Sunday if exists, otherwise 3rd
        if len(sundays) >= 4:
            return sundays[3]  # 4th Sunday (0-indexed)
        else:
            return sundays[2] if len(sundays) >= 3 else sundays[-1]  # 3rd or last

    def create_tournament_with_results(self, year, month, big_bass_percent=30, zero_catch_percent=18):
        """Create a complete team tournament with results"""
        
        # Get the date (4th Sunday, or 3rd if no 4th)
        tournament_date = self.get_nth_sunday(year, month, 4)
        
        # Get all non-paper lakes and anglers
        lakes = list(Lake.objects.filter(paper=False))
        anglers = list(Angler.objects.filter(member=True))
        
        if not lakes or len(anglers) < 10:
            self.stdout.write(
                self.style.WARNING(f"Not enough data: {len(lakes)} lakes, {len(anglers)} anglers")
            )
            return None
        
        # Randomly select a lake
        selected_lake = random.choice(lakes)
        
        # Get or create a ramp for this lake
        ramps = list(Ramp.objects.filter(lake=selected_lake))
        if not ramps:
            # Create a default ramp
            ramp = Ramp.objects.create(
                lake=selected_lake,
                name=f"{selected_lake.name} Main Ramp"
            )
        else:
            ramp = random.choice(ramps)
        
        # Generate realistic tournament times
        start_time, weigh_in_time = self.generate_tournament_times(tournament_date)
        
        # Create the event with times
        event = Events.objects.create(
            type='tournament',
            date=tournament_date,
            year=year,
            month=month,
            start=start_time,
            finish=weigh_in_time
        )
        
        # Create tournament name
        month_names = ['January', 'February', 'March', 'April', 'May', 'June', 
                       'July', 'August', 'September', 'October', 'November', 'December']
        tournament_name = f"{month_names[month-1]} {year} Team Tournament"
        
        # Create the tournament (always regular team tournament)
        tournament = Tournament.objects.create(
            name=tournament_name,
            event=event,
            lake=selected_lake,
            ramp=ramp,
            team=True,  # This is a team tournament
            paper=False,  # Never a paper tournament
            points_count=True,  # Always counts for points
            complete=True
        )
        
        self.stdout.write(f"Created: {tournament_name} at {selected_lake.name}")
        
        # Create a completed poll that "selected" this lake
        # This simulates the voting process that would have happened before the tournament
        self.create_completed_poll_for_tournament(tournament, selected_lake)
        
        # Explicitly ensure the tournament has the selected lake
        tournament.lake = selected_lake
        tournament.save()
        
        # Verify the assignment worked
        tournament.refresh_from_db()
        if not tournament.lake:
            self.stdout.write(
                self.style.ERROR(f"ERROR: Tournament {tournament.name} still has no lake after assignment!")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"  ✓ Verified: {tournament.name} has lake {tournament.lake.name}")
            )
        
        # Create individual results
        # Shuffle anglers and create results for 60-80% of them
        random.shuffle(anglers)
        num_participants = random.randint(int(len(anglers) * 0.6), int(len(anglers) * 0.8))
        participants = anglers[:num_participants]
        
        # Determine if this tournament has a big bass
        has_big_bass = random.random() < (big_bass_percent / 100.0)
        big_bass_angler = None
        
        results = []
        for i, angler in enumerate(participants):
            # Some anglers catch zero fish
            catches_zero = random.random() < (zero_catch_percent / 100.0)
            
            if catches_zero:
                total_weight = Decimal('0.00')
                big_bass_weight = Decimal('0.00')
                num_fish = 0
            else:
                # Generate realistic weights
                num_fish = random.randint(1, 5)
                fish_weights = []
                for _ in range(num_fish):
                    # Individual fish weight between 1-4 lbs typically
                    weight = Decimal(str(round(random.uniform(1.0, 4.0), 2)))
                    fish_weights.append(weight)
                
                # If this tournament has big bass and this is the chosen angler
                if has_big_bass and not big_bass_angler and i < 5:
                    # Make one fish a big bass (5+ lbs)
                    big_bass_weight = Decimal(str(round(random.uniform(5.0, 8.0), 2)))
                    fish_weights[0] = big_bass_weight
                    big_bass_angler = angler
                else:
                    big_bass_weight = max(fish_weights) if fish_weights else Decimal('0.00')
                
                total_weight = sum(fish_weights)
            
            # Small chance of penalty
            penalty_weight = Decimal('0.00')
            if random.random() < 0.05:  # 5% chance of penalty
                penalty_weight = Decimal(str(round(random.uniform(0.5, 2.0), 2)))
            
            result = Result(
                tournament=tournament,
                angler=angler,
                num_fish=num_fish,
                total_weight=total_weight,
                big_bass_weight=big_bass_weight,
                penalty_weight=penalty_weight,
                place_finish=0,  # Will be set after sorting
                buy_in=False,
                disqualified=False
            )
            results.append(result)
        
        # Sort results by weight (accounting for penalties) and assign places
        results.sort(key=lambda r: r.total_weight - r.penalty_weight, reverse=True)
        for i, result in enumerate(results, 1):
            result.place_finish = i
        
        # Bulk create results and refresh from DB to get IDs
        Result.objects.bulk_create(results)
        
        # Re-fetch results from database to get their IDs
        saved_results = Result.objects.filter(tournament=tournament)
        
        # Create team results (pair up anglers)
        team_results = []
        
        # Create a mapping of anglers to their Result objects
        angler_to_result = {r.angler: r for r in saved_results}
        
        # Shuffle participants for random pairing
        random.shuffle(participants)
        
        for i in range(0, len(participants) - 1, 2):
            # Get the Result objects for each angler
            r1 = angler_to_result.get(participants[i])
            r2 = angler_to_result.get(participants[i + 1])
            
            if r1 and r2:
                # Calculate team weight
                team_weight = (r1.total_weight - r1.penalty_weight) + (r2.total_weight - r2.penalty_weight)
                
                team_result = TeamResult.objects.create(
                    tournament=tournament,
                    result_1=r1,
                    result_2=r2,
                    total_weight=team_weight,
                    place_finish=0  # Will be set after sorting
                )
                team_results.append(team_result)
        
        # Sort team results and assign places
        team_results.sort(key=lambda t: t.total_weight, reverse=True)
        for i, team_result in enumerate(team_results, 1):
            team_result.place_finish = i
            team_result.save()
        
        return tournament

    def create_upcoming_tournament(self, year, month):
        """Create an upcoming tournament with poll for location voting"""
        
        # Get the date (4th Sunday of the month)
        tournament_date = self.get_nth_sunday(year, month, 4)
        
        # Create the event
        event = Events.objects.create(
            type='tournament',
            date=tournament_date,
            year=year,
            month=month
        )
        
        # Get tournament number for the year
        tournament_count = Tournament.objects.filter(event__year=year).count() + 1
        
        # Create month name
        month_names = ['January', 'February', 'March', 'April', 'May', 'June', 
                       'July', 'August', 'September', 'October', 'November', 'December']
        
        # Create the tournament (no lake, as it's upcoming)
        tournament = Tournament.objects.create(
            name=f"{month_names[month-1]} {year} Event #{tournament_count}",
            event=event,
            lake=None,  # No lake for upcoming tournament
            team=False,  # Will be determined later
            complete=False
        )
        
        # The poll should be created automatically by the Event save signal
        poll = tournament.event.polls.first() if tournament.event else None
        if poll:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created upcoming tournament: {tournament.name} with poll: {poll.name}"
                )
            )
            
            # Add some sample votes to the poll
            lakes = list(Lake.objects.all())
            anglers = list(Angler.objects.filter(member=True)[:15])
            
            for angler in anglers:
                if lakes:
                    vote_lake = random.choice(lakes)
                    LakeVote.objects.create(
                        poll=poll,
                        angler=angler,
                        choice=vote_lake
                    )
        else:
            self.stdout.write(
                self.style.WARNING(f"Created upcoming tournament: {tournament.name} (no poll created)")
            )
        
        return tournament

    def handle(self, *args, **options):
        """Main command handler"""
        
        # Clear existing data if requested
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing existing tournament data...'))
            with transaction.atomic():
                TeamResult.objects.all().delete()
                Result.objects.all().delete()
                Tournament.objects.all().delete()
                Events.objects.all().delete()
                LakeVote.objects.all().delete()
                LakePoll.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing data cleared!'))
        
        with transaction.atomic():
            paper_count = 0
            total_created = 0
            
            # Calculate total tournaments to create
            years = options['years']
            months_2025 = options['months_2025']
            total_tournaments = len(years) * 12 + months_2025
            
            # Generate tournaments for specified years
            for year in years:
                self.stdout.write(self.style.SUCCESS(f'\n=== Creating {year} Tournaments ==='))
                for month in range(1, 13):
                    tournament = self.create_tournament_with_results(
                        year, month, 
                        big_bass_percent=options['big_bass_percent'],
                        zero_catch_percent=options['zero_catch_percent']
                    )
                    
                    if tournament:
                        total_created += 1
            
            # Generate tournaments for 2025 (partial year)
            if months_2025 > 0:
                self.stdout.write(self.style.SUCCESS(f'\n=== Creating 2025 Tournaments (Jan-{months_2025}) ==='))
                for month in range(1, months_2025 + 1):
                    tournament = self.create_tournament_with_results(
                        2025, month,
                        big_bass_percent=options['big_bass_percent'],
                        zero_catch_percent=options['zero_catch_percent']
                    )
                    
                    if tournament:
                        total_created += 1
            
            # Create upcoming tournament
            if options['create_upcoming']:
                self.stdout.write(self.style.SUCCESS('\n=== Creating Upcoming Tournament ==='))
                # Determine next month
                if months_2025 < 12:
                    upcoming_month = months_2025 + 1
                    upcoming_year = 2025
                else:
                    upcoming_month = 1
                    upcoming_year = 2026
                
                upcoming = self.create_upcoming_tournament(upcoming_year, upcoming_month)
            
            # Print summary
            self.stdout.write(self.style.SUCCESS('\n=== Summary ==='))
            self.stdout.write(f'Total tournaments created: {total_created}')
            self.stdout.write('All tournaments are regular team tournaments')
            if options['create_upcoming']:
                self.stdout.write('Upcoming tournaments: 1')
            
            # Verify big bass percentage
            try:
                tournaments_with_big_bass = 0
                for tournament in Tournament.objects.filter(complete=True):
                    results = Result.objects.filter(tournament=tournament, big_bass_weight__gte=5.0)
                    if results.exists():
                        tournaments_with_big_bass += 1
                
                if total_created > 0:
                    big_bass_percentage = (tournaments_with_big_bass / total_created) * 100
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Tournaments with big bass (5+ lbs): {tournaments_with_big_bass} '
                            f'({big_bass_percentage:.1f}%)'
                        )
                    )
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error verifying big bass: {e}'))
            
            # Final statistics
            self.stdout.write(self.style.SUCCESS('\n=== Database Statistics ==='))
            self.stdout.write(f'Total tournaments: {Tournament.objects.count()}')
            self.stdout.write(f'Total results: {Result.objects.count()}')
            self.stdout.write(f'Total team results: {TeamResult.objects.count()}')
            self.stdout.write(f'Zero catches: {Result.objects.filter(num_fish=0).count()}')
            
            # Final verification that all completed tournaments have lakes
            self.stdout.write(self.style.SUCCESS('\n=== FINAL VERIFICATION ==='))
            completed_without_lakes = Tournament.objects.filter(complete=True, lake__isnull=True).count()
            # Check for tournaments whose events don't have polls
            tournaments_without_polls = 0
            for tournament in Tournament.objects.filter(complete=True):
                if not tournament.event or not tournament.event.polls.exists():
                    tournaments_without_polls += 1
            completed_without_polls = tournaments_without_polls
            upcoming_with_lakes = Tournament.objects.filter(complete=False, lake__isnull=False).count()
            
            if completed_without_lakes == 0:
                self.stdout.write(self.style.SUCCESS('✅ All completed tournaments have lakes'))
            else:
                self.stdout.write(self.style.ERROR(f'❌ {completed_without_lakes} completed tournaments missing lakes'))
                
            if completed_without_polls == 0:
                self.stdout.write(self.style.SUCCESS('✅ All completed tournaments have polls'))
            else:
                self.stdout.write(self.style.ERROR(f'❌ {completed_without_polls} completed tournaments missing polls'))
                
            if upcoming_with_lakes == 0:
                self.stdout.write(self.style.SUCCESS('✅ No upcoming tournaments have lakes (correct)'))
            else:
                self.stdout.write(self.style.ERROR(f'❌ {upcoming_with_lakes} upcoming tournaments have lakes (should be 0)'))
            
            self.stdout.write(self.style.SUCCESS('\nTournament generation complete!'))