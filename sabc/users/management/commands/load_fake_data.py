import os
import yaml
from datetime import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.conf import settings

from users.models import Angler, Officers
from tournaments.models.lakes import Lake, Ramp
from tournaments.models.tournaments import Tournament
from tournaments.models.events import Events
from tournaments.models.results import Result, TeamResult
from tournaments.models.payouts import PayOutMultipliers
from tournaments.models.rules import RuleSet
from polls.models import LakePoll, LakeVote


class Command(BaseCommand):
    help = "Load fake data from YAML files"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing data before loading",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write(self.style.WARNING("Clearing existing data..."))
            self.clear_data()

        self.stdout.write(self.style.SUCCESS("Loading fake data..."))

        # Load data in dependency order
        self.load_lakes()
        self.load_anglers()
        self.load_tournaments()
        self.load_polls()

        self.stdout.write(self.style.SUCCESS("Successfully loaded all fake data!"))

    def clear_data(self):
        """Clear existing data in reverse dependency order"""
        LakeVote.objects.all().delete()
        LakePoll.objects.all().delete()
        TeamResult.objects.all().delete()
        Result.objects.all().delete()
        Tournament.objects.all().delete()
        Events.objects.all().delete()
        Officers.objects.all().delete()
        Angler.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()  # Keep superuser
        Ramp.objects.all().delete()
        Lake.objects.all().delete()
        PayOutMultipliers.objects.all().delete()
        RuleSet.objects.all().delete()

    def load_yaml_file(self, filename):
        """Load and parse a YAML file"""
        file_path = os.path.join(settings.BASE_DIR, "media", "fake_data", filename)
        with open(file_path, "r") as file:
            return yaml.safe_load(file)

    def load_lakes(self):
        """Load lakes and ramps data"""
        self.stdout.write("Loading lakes...")
        data = self.load_yaml_file("lakes.yaml")

        for lake_data in data["lakes"]:
            # Create lake (name will be processed by the model's save method)
            lake = Lake.objects.create(
                name=lake_data["name"],
                paper=False,  # Default, can be overridden
                google_maps=f'<iframe src="https://maps.google.com/maps?q={lake_data.get("name", "")}&output=embed" width="100%" height="200"></iframe>',
            )

            # Create ramps for this lake
            for ramp_data in lake_data.get("ramps", []):
                Ramp.objects.create(
                    lake=lake,
                    name=ramp_data["name"],
                    google_maps=f'<iframe src="https://maps.google.com/maps?q={ramp_data.get("lat", 0)},{ramp_data.get("lng", 0)}&output=embed" width="100%" height="200"></iframe>',
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Loaded {Lake.objects.count()} lakes and {Ramp.objects.count()} ramps"
            )
        )

    def load_anglers(self):
        """Load anglers data from both YAML files"""
        self.stdout.write("Loading anglers...")

        # Create default payout multiplier and ruleset for current year
        current_year = datetime.now().year
        PayOutMultipliers.objects.get_or_create(
            year=current_year,
            defaults={
                "entry_fee": Decimal("25.00"),
                "club": Decimal("3.00"),
                "place_1": Decimal("7.00"),
                "place_2": Decimal("5.00"),
                "place_3": Decimal("4.00"),
                "charity": Decimal("2.00"),
                "big_bass": Decimal("4.00"),
            },
        )

        RuleSet.objects.get_or_create(
            year=current_year,
            defaults={
                "name": f"SABC Default Rules {current_year}",
                "dead_fish_penalty": Decimal("0.50"),  # 0.5lb penalty per dead fish
            },
        )

        # Load main anglers file
        data = self.load_yaml_file("anglers.yaml")
        self.process_anglers(data["anglers"])

        # Load additional anglers file
        more_data = self.load_yaml_file("more_anglers.yaml")
        self.process_anglers(more_data["more_anglers"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Loaded {User.objects.count()} users and {Angler.objects.count()} anglers"
            )
        )

    def process_anglers(self, anglers_data):
        """Process anglers data and create User and Angler objects"""
        for angler_data in anglers_data:
            # Create User
            user = User.objects.create_user(
                username=angler_data["username"],
                first_name=angler_data["first_name"],
                last_name=angler_data["last_name"],
                email=angler_data["email"],
                is_active=True,
            )

            # Create Angler
            angler = Angler.objects.create(
                user=user,
                member=(angler_data["angler_type"] != "guest"),
                phone_number=angler_data["phone"],
            )

            # Create Officer if needed
            if angler_data.get("angler_type") == "officer":
                officer_position = angler_data.get("officer_type", "president")
                # Map officer types to model choices
                position_map = {
                    "president": Officers.OfficerPositions.PRESIDENT,
                    "vice_president": Officers.OfficerPositions.VICE_PRESIDENT,
                    "treasurer": Officers.OfficerPositions.TREASURER,
                    "secretary": Officers.OfficerPositions.SECRETARY,
                }

                Officers.objects.create(
                    angler=angler,
                    position=position_map.get(
                        officer_position, Officers.OfficerPositions.PRESIDENT
                    ),
                    year=datetime.now().year,
                )

    def load_tournaments(self):
        """Load tournaments and results data"""
        self.stdout.write("Loading tournaments...")
        data = self.load_yaml_file("tournaments.yaml")

        for tournament_data in data["tournaments"]:
            # Get or create lake and ramp
            lake = Lake.objects.filter(
                name__icontains=tournament_data["lake"]
                .lower()
                .replace("lake", "")
                .strip()
            ).first()
            if not lake:
                self.stdout.write(
                    self.style.WARNING(f"Lake not found: {tournament_data['lake']}")
                )
                continue

            ramp = lake.ramp_set.filter(
                name__icontains=tournament_data.get("ramp", "").split()[0]
            ).first()
            if not ramp:
                ramp = lake.ramp_set.first()  # Use first available ramp

            # Create Event
            event_date = datetime.strptime(tournament_data["date"], "%Y-%m-%d").date()
            start_time = datetime.strptime(
                tournament_data["start_time"], "%H:%M"
            ).time()
            end_time = datetime.strptime(tournament_data["end_time"], "%H:%M").time()

            event = Events.objects.create(
                date=event_date,
                type="tournament",
                year=event_date.year,
                month=event_date.strftime("%B").lower(),
                start=start_time,
                finish=end_time,
            )

            # Get or create payout multiplier and rules for the year
            payout, created = PayOutMultipliers.objects.get_or_create(
                year=event_date.year,
                defaults={
                    "entry_fee": Decimal("25.00"),
                    "club": Decimal("3.00"),
                    "place_1": Decimal("7.00"),
                    "place_2": Decimal("5.00"),
                    "place_3": Decimal("4.00"),
                    "charity": Decimal("2.00"),
                    "big_bass": Decimal("4.00"),
                },
            )

            rules, created = RuleSet.objects.get_or_create(
                year=event_date.year,
                defaults={
                    "name": f"SABC Default Rules {event_date.year}",
                    "dead_fish_penalty": Decimal("0.50"),
                },
            )

            # Create Tournament
            tournament = Tournament.objects.create(
                name=tournament_data["name"],
                lake=lake,
                ramp=ramp,
                event=event,
                payout_multiplier=payout,
                rules=rules,
                points_count=tournament_data.get("points_count", True),
                team=tournament_data.get("team_tournament", False),
                paper=tournament_data.get("paper", False),
                description=tournament_data.get("description", ""),
                complete=tournament_data.get("complete", False),
            )

            # Load results if tournament is complete
            if tournament_data.get("results"):
                self.load_tournament_results(tournament, tournament_data["results"])

            # Load team results if it's a team tournament
            if tournament_data.get("teams"):
                self.load_team_results(
                    tournament,
                    tournament_data["teams"],
                    tournament_data.get("results", []),
                )

        self.stdout.write(
            self.style.SUCCESS(f"Loaded {Tournament.objects.count()} tournaments")
        )

    def load_tournament_results(self, tournament, results_data):
        """Load individual tournament results"""
        # Sort results by total weight (descending) to assign proper placement if not provided
        sorted_results = sorted(
            results_data, key=lambda x: float(x.get("total_weight", 0)), reverse=True
        )

        for index, result_data in enumerate(sorted_results):
            # Find the angler
            angler = Angler.objects.filter(user__username=result_data["angler"]).first()
            if not angler:
                self.stdout.write(
                    self.style.WARNING(f"Angler not found: {result_data['angler']}")
                )
                continue

            # Calculate dead fish count from penalty
            dead_fish_penalty = result_data.get("dead_fish_penalty", 0)
            dead_fish_count = (
                int(dead_fish_penalty / 0.5) if dead_fish_penalty > 0 else 0
            )

            # Use provided placement or calculate from weight ranking
            placement = result_data.get("placement", index + 1)

            Result.objects.create(
                angler=angler,
                tournament=tournament,
                total_weight=Decimal(str(result_data["total_weight"]))
                + Decimal(str(dead_fish_penalty)),  # Add penalty back for raw weight
                big_bass_weight=Decimal(str(result_data["big_bass"])),
                num_fish=result_data["fish_count"],
                num_fish_dead=dead_fish_count,
                penalty_weight=Decimal(str(dead_fish_penalty)),
                points=result_data.get("points", 0),
                place_finish=placement,
            )

    def load_team_results(self, tournament, teams_data, results_data):
        """Load team tournament results"""
        for team_data in teams_data:
            # Find the team members
            angler1 = Angler.objects.filter(user__username=team_data["angler1"]).first()
            angler2 = Angler.objects.filter(user__username=team_data["angler2"]).first()

            if not angler1 or not angler2:
                self.stdout.write(
                    self.style.WARNING(
                        f"Team member not found for team: {team_data['team_name']}"
                    )
                )
                continue

            # Get the individual results for team members
            result1 = Result.objects.filter(
                tournament=tournament, angler=angler1
            ).first()
            result2 = Result.objects.filter(
                tournament=tournament, angler=angler2
            ).first()

            if result1 and result2:
                TeamResult.objects.create(
                    tournament=tournament,
                    result_1=result1,
                    result_2=result2,
                    team_name=team_data["team_name"],
                )

    def load_polls(self):
        """Load polls and voting data"""
        self.stdout.write("Loading polls...")
        data = self.load_yaml_file("polls.yaml")

        for poll_data in data["polls"]:
            # Create LakePoll
            created_date = datetime.strptime(
                poll_data["created_date"], "%Y-%m-%d"
            ).date()
            end_date = datetime.strptime(poll_data["end_date"], "%Y-%m-%d").date()

            poll = LakePoll.objects.create(
                name=poll_data["title"],
                description=poll_data["description"],
                end_date=end_date,
                complete=not poll_data["is_active"],
            )

            # Add lake choices and votes
            for option in poll_data["options"]:
                lake = Lake.objects.filter(
                    name__icontains=option["lake_name"]
                    .lower()
                    .replace("lake", "")
                    .strip()
                ).first()
                if not lake:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Lake not found for poll: {option['lake_name']}"
                        )
                    )
                    continue

                poll.choices.add(lake)

                # Add votes for this option
                for voter_username in option["voters"]:
                    angler = Angler.objects.filter(
                        user__username=voter_username
                    ).first()
                    if angler:
                        LakeVote.objects.create(poll=poll, choice=lake, angler=angler)

        self.stdout.write(
            self.style.SUCCESS(
                f"Loaded {LakePoll.objects.count()} polls with {LakeVote.objects.count()} votes"
            )
        )
