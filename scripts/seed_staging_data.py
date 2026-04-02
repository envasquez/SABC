#!/usr/bin/env python3
"""Seed local/staging database with large-scale realistic test data.

Generates:
- 1 admin + 1000 members (with realistic names)
- 10 lakes with 2-4 ramps each
- Monthly tournaments from Jan 2020 to present
- Individual + team results for each tournament
- Location polls for each tournament
- News posts

Usage:
    DATABASE_URL='postgresql://...' python scripts/seed_staging_data.py
"""

import json
import os
import random
import sys
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # noqa: E402

import bcrypt  # noqa: E402

from core.db_schema import get_session  # noqa: E402
from core.db_schema.models import (  # noqa: E402
    Angler,
    Event,
    Lake,
    News,
    OfficerPosition,
    Poll,
    PollOption,
    PollVote,
    Ramp,
    Result,
    TeamResult,
    Tournament,
)

# Realistic name pools
FIRST_NAMES = [
    "James",
    "John",
    "Robert",
    "Michael",
    "David",
    "William",
    "Richard",
    "Joseph",
    "Thomas",
    "Charles",
    "Christopher",
    "Daniel",
    "Matthew",
    "Anthony",
    "Mark",
    "Donald",
    "Steven",
    "Andrew",
    "Paul",
    "Joshua",
    "Kenneth",
    "Kevin",
    "Brian",
    "George",
    "Timothy",
    "Ronald",
    "Jason",
    "Edward",
    "Jeffrey",
    "Ryan",
    "Jacob",
    "Gary",
    "Nicholas",
    "Eric",
    "Jonathan",
    "Stephen",
    "Larry",
    "Justin",
    "Scott",
    "Brandon",
    "Benjamin",
    "Samuel",
    "Raymond",
    "Gregory",
    "Frank",
    "Patrick",
    "Jack",
    "Dennis",
    "Jerry",
    "Tyler",
    "Aaron",
    "Jose",
    "Adam",
    "Nathan",
    "Zachary",
    "Henry",
    "Douglas",
    "Peter",
    "Kyle",
    "Noah",
    "Ethan",
    "Jeremy",
    "Walter",
    "Christian",
    "Keith",
    "Roger",
    "Terry",
    "Austin",
    "Sean",
    "Gerald",
    "Carl",
    "Harold",
    "Dylan",
    "Arthur",
    "Lawrence",
    "Jordan",
    "Jesse",
    "Bryan",
    "Billy",
    "Bruce",
    "Gabriel",
    "Joe",
    "Logan",
    "Albert",
    "Willie",
    "Alan",
    "Eugene",
    "Russell",
    "Randy",
    "Philip",
    "Harry",
    "Vincent",
    "Bobby",
    "Johnny",
    "Travis",
    "Wayne",
    "Caleb",
    "Hunter",
    "Cody",
    "Luke",
    "Mason",
    "Liam",
    "Colton",
    "Wyatt",
    "Blake",
    "Beau",
    "Clay",
]

LAST_NAMES = [
    "Smith",
    "Johnson",
    "Williams",
    "Brown",
    "Jones",
    "Garcia",
    "Miller",
    "Davis",
    "Rodriguez",
    "Martinez",
    "Hernandez",
    "Lopez",
    "Gonzalez",
    "Wilson",
    "Anderson",
    "Thomas",
    "Taylor",
    "Moore",
    "Jackson",
    "Martin",
    "Lee",
    "Perez",
    "Thompson",
    "White",
    "Harris",
    "Sanchez",
    "Clark",
    "Ramirez",
    "Lewis",
    "Robinson",
    "Walker",
    "Young",
    "Allen",
    "King",
    "Wright",
    "Scott",
    "Torres",
    "Nguyen",
    "Hill",
    "Flores",
    "Green",
    "Adams",
    "Nelson",
    "Baker",
    "Hall",
    "Rivera",
    "Campbell",
    "Mitchell",
    "Carter",
    "Roberts",
    "Turner",
    "Phillips",
    "Evans",
    "Edwards",
    "Collins",
    "Stewart",
    "Morris",
    "Murphy",
    "Cook",
    "Rogers",
    "Morgan",
    "Peterson",
    "Cooper",
    "Reed",
    "Bailey",
    "Bell",
    "Gomez",
    "Kelly",
    "Howard",
    "Ward",
    "Cox",
    "Diaz",
    "Richardson",
    "Wood",
    "Watson",
    "Brooks",
    "Bennett",
    "Gray",
    "James",
    "Reyes",
    "Cruz",
    "Hughes",
    "Price",
    "Myers",
    "Long",
    "Foster",
    "Sanders",
    "Ross",
    "Morales",
    "Powell",
    "Sullivan",
    "Russell",
    "Ortiz",
    "Jenkins",
    "Gutierrez",
    "Perry",
    "Butler",
    "Barnes",
    "Fisher",
    "Henderson",
    "Coleman",
    "Simmons",
    "Patterson",
    "Jordan",
    "Reynolds",
    "Hamilton",
    "Graham",
    "Kim",
    "Gonzales",
    "Alexander",
    "Ramos",
    "Wallace",
]

LAKE_DATA = [
    (
        "lake_travis",
        "Lake Travis",
        [
            (
                "Mansfield Dam",
                '<iframe src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3444!2d-97.88!3d30.39" style="border:0" allowfullscreen="" loading="lazy" referrerpolicy="no-referrer-when-downgrade"></iframe>',
            ),
            ("Arkansas Bend", ""),
            ("Pace Bend Park", ""),
        ],
    ),
    (
        "lake_austin",
        "Lake Austin",
        [
            ("Walsh Boat Landing", ""),
            ("Selma Hughes Park", ""),
        ],
    ),
    (
        "lake_lbj",
        "Lake LBJ",
        [
            ("Kingsland Public Ramp", ""),
            ("Granite Shoals Ramp", ""),
        ],
    ),
    (
        "lake_buchanan",
        "Lake Buchanan",
        [
            ("Black Rock Park", ""),
            ("Cedar Point Ramp", ""),
            ("Llano County Ramp", ""),
        ],
    ),
    (
        "lake_bastrop",
        "Lake Bastrop",
        [
            ("North Shore Park", ""),
            ("South Shore Ramp", ""),
        ],
    ),
    (
        "canyon_lake",
        "Canyon Lake",
        [
            ("Potters Creek", ""),
            ("Comal Park", ""),
            ("Canyon Park", ""),
        ],
    ),
    (
        "lake_georgetown",
        "Lake Georgetown",
        [
            ("Jim Hogg Park", ""),
            ("Russell Park", ""),
        ],
    ),
    (
        "granger_lake",
        "Granger Lake",
        [
            ("Willis Creek Park", ""),
            ("Taylor Park", ""),
        ],
    ),
    (
        "lake_belton",
        "Lake Belton",
        [
            ("Belton Lakeview Park", ""),
            ("Temple Lake Park", ""),
            ("Winkler Park", ""),
        ],
    ),
    (
        "decker_lake",
        "Walter E. Long Lake (Decker)",
        [
            ("Decker Lake Park", ""),
        ],
    ),
]

NEWS_ITEMS = [
    (
        "Welcome to the 2020 Season!",
        "We're kicking off another great year of bass fishing at South Austin Bass Club. Check the calendar for upcoming tournaments.",
    ),
    (
        "New Tournament Format",
        "Starting this season, we're using a team format for all monthly tournaments. Boater and non-boater pairings will be drawn at the ramp.",
    ),
    (
        "Lake Travis Fishing Report",
        "The bass are biting at Lake Travis! Anglers are reporting great catches on topwater early morning and crankbaits mid-day.",
    ),
    (
        "Annual Banquet Announced",
        "Save the date for our annual awards banquet. We'll be celebrating this year's Angler of the Year and other achievements.",
    ),
    (
        "Tournament Rules Update",
        "Reminder: 5 fish limit per angler, 14-inch minimum length, and all fish must be alive at weigh-in. Dead fish penalty is 0.25 lbs.",
    ),
    (
        "New Members Welcome!",
        "We've had a great influx of new members this year. Welcome to everyone who has joined the club!",
    ),
    (
        "Big Bass of the Month",
        "Congratulations to our big bass winners this month. Some truly impressive fish were brought to the scales.",
    ),
    (
        "Summer Night Tournament",
        "Don't miss our special summer night tournament! Fishing from 6pm to midnight under the stars.",
    ),
    (
        "Conservation Corner",
        "Remember to practice catch and release when possible. Healthy fisheries mean better fishing for everyone.",
    ),
    (
        "End of Year Standings",
        "Check the Club Data page for current Angler of the Year standings. The race is tighter than ever!",
    ),
]


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _generate_unique_names(count: int) -> list[str]:
    """Generate unique full names."""
    names: set[str] = set()
    while len(names) < count:
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        names.add(f"{first} {last}")
    return sorted(names)


def seed_data() -> None:
    """Populate database with large-scale test data."""
    print("🌱 Seeding database with 1000 members and tournaments from 2020...")
    print()

    admin_pw = _hash_password("admin123")
    member_pw = _hash_password("password123")

    today = date.today()

    with get_session() as session:
        existing = session.query(Angler).first()
        if existing:
            print("⚠️  Database already has data. Skipping seed.")
            print("   Run reset-db first if you want to re-seed.")
            return

        # === ADMIN ===
        print("  [1/8] Creating admin user...")
        admin = Angler(
            name="Eric Vasquez",
            email="admin@sabc.com",
            password_hash=admin_pw,
            member=True,
            is_admin=True,
            phone="+15125550001",
            year_joined=2019,
            dues_paid_through=date(today.year, 12, 31),
        )
        session.add(admin)
        session.flush()

        # === MEMBERS ===
        print("  [2/8] Creating 1000 members...")
        names = _generate_unique_names(1000)
        members: list[Angler] = []
        for i, name in enumerate(names):
            first = name.split()[0].lower()
            last = name.split()[1].lower()
            year_joined = random.randint(2018, 2026)
            # ~85% of members have current dues, ~15% lapsed
            if random.random() < 0.85:
                dues_through = date(today.year, 12, 31)
            else:
                # Lapsed — expired sometime in the past year
                dues_through = today - timedelta(days=random.randint(30, 365))

            member = Angler(
                name=name,
                email=f"{first}.{last}@sabc.test",
                password_hash=member_pw,
                member=True,
                is_admin=False,
                phone=f"+1512{random.randint(1000000, 9999999)}",
                year_joined=year_joined,
                dues_paid_through=dues_through,
            )
            members.append(member)
            session.add(member)
        session.flush()
        print(f"       Created {len(members)} members")

        # === GUEST ANGLERS (non-members who fish occasionally) ===
        print("  [2b/8] Creating 50 guest anglers...")
        guest_names = _generate_unique_names(50)
        guests: list[Angler] = []
        for name in guest_names:
            # Avoid collisions with member names
            if any(m.name == name for m in members):
                continue
            first = name.split()[0].lower()
            last = name.split()[1].lower()
            guest = Angler(
                name=name,
                email=f"{first}.{last}.guest@sabc.test",
                member=False,
                is_admin=False,
            )
            guests.append(guest)
            session.add(guest)
        session.flush()
        print(f"       Created {len(guests)} guests")

        # === LAKES & RAMPS (from production export) ===
        print("  [3/8] Creating lakes and ramps from production data...")
        lakes: list[Lake] = []
        all_ramps: list[Ramp] = []
        lake_ramp_map: dict[int, list[Ramp]] = {}

        lakes_json_path = os.path.join(os.path.dirname(__file__), "lakes_production.json")
        with open(lakes_json_path) as f:
            production_lakes = json.load(f)

        for lake_data in production_lakes:
            lake = Lake(
                yaml_key=lake_data["yaml_key"],
                display_name=lake_data["display_name"],
                google_maps_iframe=lake_data.get("google_maps_iframe"),
            )
            session.add(lake)
            session.flush()
            lakes.append(lake)
            lake_ramp_map[lake.id] = []

            for ramp_data in lake_data.get("ramps") or []:
                ramp = Ramp(
                    lake_id=lake.id,
                    name=ramp_data["name"],
                    google_maps_iframe=ramp_data.get("google_maps_iframe"),
                )
                session.add(ramp)
                session.flush()
                all_ramps.append(ramp)
                lake_ramp_map[lake.id].append(ramp)

        print(f"       Created {len(lakes)} lakes, {len(all_ramps)} ramps")

        # === OFFICER POSITIONS ===
        print("  [4/8] Creating officer positions...")
        positions = ["President", "Vice President", "Secretary", "Treasurer", "Tournament Director"]
        for year in range(2020, 2027):
            officers = random.sample(members[:50], min(len(positions), 50))
            for pos_idx, position in enumerate(positions):
                op = OfficerPosition(
                    angler_id=officers[pos_idx].id,
                    position=position,
                    year=year,
                )
                session.add(op)
        session.flush()

        # === TOURNAMENTS (2020-present) ===
        print("  [5/8] Creating monthly tournaments from Jan 2020...")
        tournament_months: list[date] = []

        # Generate tournament dates: 2nd Saturday of each month
        # Generate full years 2020 through current year (all 12 months)
        for year in range(2020, today.year + 1):
            for month in range(1, 13):
                # Find 2nd Saturday
                first_day = date(year, month, 1)
                first_saturday = first_day + timedelta(days=(5 - first_day.weekday()) % 7)
                second_saturday = first_saturday + timedelta(days=7)
                tournament_months.append(second_saturday)

        tournaments: list[tuple[Tournament, bool]] = []  # (tournament, is_past)
        month_names = [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]

        for t_date in tournament_months:
            is_past = t_date < today
            lake = random.choice(lakes)
            ramp = random.choice(lake_ramp_map[lake.id])

            event = Event(
                date=t_date,
                year=t_date.year,
                name=f"{month_names[t_date.month - 1]} {t_date.year} Tournament",
                event_type="sabc_tournament",
                start_time=time(6, 0),
                weigh_in_time=time(15, 0),
                lake_name=lake.display_name,
                ramp_name=ramp.name,
                entry_fee=Decimal("50.00"),
            )
            session.add(event)
            session.flush()

            # 2020-2023: AoY points (individual format)
            # 2024+: Team format
            is_team_format = t_date.year >= 2026
            tournament = Tournament(
                event_id=event.id,
                name=event.name,
                lake_id=lake.id,
                ramp_id=ramp.id,
                lake_name=lake.display_name,
                ramp_name=ramp.name,
                start_time=time(6, 0),
                end_time=time(15, 0),
                fish_limit=5,
                entry_fee=Decimal("50.00"),
                is_team=is_team_format,
                complete=is_past,
                created_by=admin.id,
                aoy_points=not is_team_format,
            )
            session.add(tournament)
            session.flush()

            # Create poll
            poll_starts = datetime.combine(
                t_date - timedelta(days=21), time(0, 0), tzinfo=timezone.utc
            )
            poll_closes = datetime.combine(
                t_date - timedelta(days=5), time(23, 59), tzinfo=timezone.utc
            )
            poll = Poll(
                event_id=event.id,
                title=f"Location Vote - {month_names[t_date.month - 1]} {t_date.year}",
                poll_type="tournament_location",
                starts_at=poll_starts,
                closes_at=poll_closes,
                closed=is_past,
                created_by=admin.id,
            )
            session.add(poll)
            session.flush()

            # 3-5 lake options per poll
            poll_lakes = random.sample(lakes, min(random.randint(3, 5), len(lakes)))
            poll_options: list[PollOption] = []
            for opt_idx, opt_lake in enumerate(poll_lakes):
                option = PollOption(
                    poll_id=poll.id,
                    option_text=opt_lake.display_name,
                    option_data=json.dumps({"lake_id": opt_lake.id}),
                    display_order=opt_idx,
                )
                session.add(option)
                poll_options.append(option)
            session.flush()

            # Add votes for past polls
            if is_past and poll_options:
                voters = random.sample(members, min(random.randint(15, 60), len(members)))
                winning_option = random.choice(poll_options)
                for voter in voters:
                    chosen = (
                        winning_option if random.random() < 0.4 else random.choice(poll_options)
                    )
                    vote = PollVote(
                        poll_id=poll.id,
                        option_id=chosen.id,
                        angler_id=voter.id,
                    )
                    session.add(vote)
                session.flush()
                poll.winning_option_id = winning_option.id

            tournaments.append((tournament, is_past))

        print(f"       Created {len(tournaments)} tournaments with polls")

        # === RESULTS ===
        print("  [6/8] Creating tournament results...")
        results_count = 0
        team_results_count = 0

        for tournament, is_past in tournaments:
            if not is_past:
                continue

            # 20-60 members per tournament (scales up over time) + 1-5 guests
            t_year = tournament.name.split()[-2] if len(tournament.name.split()) > 1 else "2020"
            base_participants = 20 + min((int(t_year) - 2020) * 5, 40)
            num_members = min(
                random.randint(base_participants, base_participants + 20), len(members)
            )
            num_guests = random.randint(1, min(5, len(guests)))
            member_participants = random.sample(members, num_members)
            guest_participants = random.sample(guests, num_guests)
            participants = member_participants + guest_participants

            # For team format (2024+), skip individual results — only create team results
            is_team_format = tournament.is_team

            # Generate individual results (only for non-team-format tournaments)
            result_data: list[dict] = []
            for member in participants:
                skill_factor = random.gauss(1.0, 0.3)
                base_weight = Decimal(str(random.uniform(2.0, 22.0)))
                total_weight = max(
                    base_weight * Decimal(str(max(skill_factor, 0.1))),
                    Decimal("0"),
                ).quantize(Decimal("0.01"))

                num_fish = min(max(int(5 * skill_factor), 0), 5) if total_weight > 0 else 0
                big_bass = (
                    max(total_weight * Decimal(str(random.uniform(0.2, 0.45))), Decimal("0"))
                    if num_fish > 0
                    else Decimal("0")
                ).quantize(Decimal("0.01"))

                is_buy_in = random.random() < 0.05
                is_dq = random.random() < 0.02
                dead_penalty = (
                    Decimal("0.25") * random.randint(1, 3)
                    if random.random() < 0.08
                    else Decimal("0")
                )

                if is_buy_in:
                    total_weight = Decimal("0")
                    big_bass = Decimal("0")
                    num_fish = 0

                result_data.append(
                    {
                        "member": member,
                        "total_weight": total_weight,
                        "num_fish": num_fish,
                        "big_bass": big_bass,
                        "dead_penalty": dead_penalty,
                        "is_buy_in": is_buy_in,
                        "is_dq": is_dq,
                    }
                )

            if not is_team_format:
                # Introduce ties: ~15% chance an angler copies weight from the one above
                ranked = sorted(
                    [r for r in result_data if not r["is_buy_in"] and not r["is_dq"]],
                    key=lambda r: r["total_weight"],
                    reverse=True,
                )
                for i in range(1, len(ranked)):
                    if random.random() < 0.15:
                        ranked[i]["total_weight"] = ranked[i - 1]["total_weight"]
                        ranked[i]["num_fish"] = ranked[i - 1]["num_fish"]
                        # ~50% of ties: bigger bass breaks it
                        if random.random() < 0.5:
                            winner_bb = Decimal(str(random.uniform(4.0, 7.0))).quantize(
                                Decimal("0.01")
                            )
                            loser_bb = winner_bb - Decimal(str(random.uniform(0.3, 1.5))).quantize(
                                Decimal("0.01")
                            )
                            ranked[i - 1]["big_bass"] = winner_bb
                            ranked[i]["big_bass"] = loser_bb

                # Sort by weight desc, then big bass desc (tiebreaker)
                ranked.sort(key=lambda r: (r["total_weight"], r["big_bass"]), reverse=True)

                unranked = [r for r in result_data if r["is_buy_in"] or r["is_dq"]]

                # Assign places — same weight = same place ONLY if big bass also tied
                place = 1
                for i, r in enumerate(ranked):
                    if (
                        i > 0
                        and r["total_weight"] == ranked[i - 1]["total_weight"]
                        and r["big_bass"] == ranked[i - 1]["big_bass"]
                    ):
                        pass  # true tie
                    else:
                        place = i + 1
                    result = Result(
                        tournament_id=tournament.id,
                        angler_id=r["member"].id,
                        num_fish=r["num_fish"],
                        total_weight=r["total_weight"],
                        big_bass_weight=r["big_bass"],
                        dead_fish_penalty=r["dead_penalty"],
                        buy_in=False,
                        disqualified=False,
                        place_finish=place,
                        was_member=bool(r["member"].member),
                    )
                    session.add(result)
                    results_count += 1

                for r in unranked:
                    result = Result(
                        tournament_id=tournament.id,
                        angler_id=r["member"].id,
                        num_fish=r["num_fish"],
                        total_weight=r["total_weight"],
                        big_bass_weight=r["big_bass"],
                        dead_fish_penalty=r["dead_penalty"],
                        buy_in=r["is_buy_in"],
                        disqualified=r["is_dq"],
                        place_finish=None,
                        was_member=bool(r["member"].member),
                    )
                    session.add(result)
                    results_count += 1

            session.flush()

            # Team results — pair up, generate weights, sort, assign places
            paired = participants[: len(participants) - (len(participants) % 2)]
            random.shuffle(paired)
            team_data: list[dict] = []
            for t_idx in range(0, len(paired) - 1, 2):
                team_weight = Decimal(str(random.uniform(5.0, 28.0))).quantize(Decimal("0.01"))
                team_fish = random.randint(0, 10)
                team_bb = (
                    Decimal(str(random.uniform(1.5, 8.0))).quantize(Decimal("0.01"))
                    if team_fish > 0
                    else Decimal("0")
                )
                team_data.append(
                    {
                        "a1": paired[t_idx],
                        "a2": paired[t_idx + 1],
                        "weight": team_weight,
                        "fish": team_fish,
                        "bb": team_bb,
                    }
                )

            # Sort teams by weight descending, introduce ~15% ties
            team_data.sort(key=lambda t: t["weight"], reverse=True)
            for i in range(1, len(team_data)):
                if random.random() < 0.15:
                    team_data[i]["weight"] = team_data[i - 1]["weight"]
                    team_data[i]["fish"] = team_data[i - 1]["fish"]
                    # ~50% of ties: give one team a bigger bass to break the tie
                    if random.random() < 0.5:
                        winner_bb = Decimal(str(random.uniform(5.0, 8.0))).quantize(Decimal("0.01"))
                        loser_bb = winner_bb - Decimal(str(random.uniform(0.5, 2.0))).quantize(
                            Decimal("0.01")
                        )
                        team_data[i - 1]["bb"] = winner_bb
                        team_data[i]["bb"] = loser_bb

            # Sort by weight desc, then big bass desc (tiebreaker)
            team_data.sort(key=lambda t: (t["weight"], t["bb"]), reverse=True)

            # Assign places — same weight = same place ONLY if big bass also tied
            place = 1
            for i, td in enumerate(team_data):
                if (
                    i > 0
                    and td["weight"] == team_data[i - 1]["weight"]
                    and td["bb"] == team_data[i - 1]["bb"]
                ):
                    pass  # true tie — same place
                else:
                    place = i + 1
                tr = TeamResult(
                    tournament_id=tournament.id,
                    angler1_id=td["a1"].id,
                    angler2_id=td["a2"].id,
                    num_fish=td["fish"],
                    total_weight=td["weight"],
                    big_bass_weight=td["bb"],
                    place_finish=place,
                )
                session.add(tr)
                team_results_count += 1

            session.flush()

        print(
            f"       Created {results_count} individual results, {team_results_count} team results"
        )

        # === NEWS ===
        print("  [7/8] Creating news posts...")
        for idx, (title, content) in enumerate(NEWS_ITEMS):
            (len(NEWS_ITEMS) - idx) * 3
            news = News(
                title=title,
                content=content,
                author_id=admin.id,
                published=True,
                priority=max(len(NEWS_ITEMS) - idx - 5, 0),
            )
            session.add(news)
        session.flush()

        # === FINAL COMMIT ===
        print("  [8/8] Committing all data...")

    print()
    print("✅ Database seeded successfully!")
    print()
    print("📊 Summary:")
    print("   • 1 admin (admin@sabc.com / admin123)")
    print(f"   • {len(members)} members (first.last@sabc.test / password123)")
    print(f"   • {len(lakes)} lakes, {len(all_ramps)} ramps")
    print(f"   • {len(tournaments)} tournaments ({sum(1 for _, p in tournaments if p)} completed)")
    print(f"   • {results_count} individual results")
    print(f"   • {team_results_count} team results")
    print(f"   • {len(NEWS_ITEMS)} news posts")
    print("   • Officer positions for 2020-2026")


if __name__ == "__main__":
    try:
        seed_data()
    except Exception as e:
        print(f"\n❌ Error seeding data: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
