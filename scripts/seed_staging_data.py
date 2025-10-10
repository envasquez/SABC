#!/usr/bin/env python3
"""Seed staging database with realistic test data.

This script populates the staging database with:
- Test admin user
- Test member users (10)
- Test lakes and ramps (3)
- Test events and tournaments (6 months)
- Test polls for tournament locations
- Test results for completed tournaments

Usage:
    DATABASE_URL='postgresql://...' python scripts/seed_staging_data.py
"""

import os
import sys
from datetime import datetime, timedelta
from decimal import Decimal

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # noqa: E402

from core.db_schema import get_session  # noqa: E402
from core.db_schema.models import (  # noqa: E402
    Angler,
    Event,
    Lake,
    News,
    Poll,
    PollOption,
    Ramp,
    Result,
    Tournament,
)
from core.helpers.password_validator import hash_password  # noqa: E402
from core.helpers.timezone import now_local  # noqa: E402


def seed_staging_data() -> None:
    """Populate staging database with test data."""
    print("🌱 Seeding staging database...")

    with get_session() as session:
        # Create test admin user
        print("  Creating admin user...")
        admin = Angler(
            name="Test Admin",
            email="admin@staging.sabc.test",
            password=hash_password("TestPassword123!"),
            member=True,
            is_admin=True,
            phone="512-555-0001",
        )
        session.add(admin)
        session.flush()

        # Create test members
        print("  Creating member users...")
        members = []
        for i in range(1, 11):
            member = Angler(
                name=f"Test Member {i}",
                email=f"member{i}@staging.sabc.test",
                password=hash_password("TestPassword123!"),
                member=True,
                is_admin=False,
                phone=f"512-555-{str(i).zfill(4)}",
            )
            members.append(member)
            session.add(member)
        session.flush()

        # Create test lakes
        print("  Creating lakes...")
        lakes = []
        lake_data = [
            ("Lake Travis", "Austin, TX"),
            ("Lake Austin", "Austin, TX"),
            ("Lady Bird Lake", "Austin, TX"),
        ]
        for name, location in lake_data:
            lake = Lake(name=name, location=location)
            lakes.append(lake)
            session.add(lake)
        session.flush()

        # Create test ramps
        print("  Creating boat ramps...")
        ramps = []
        ramp_data = [
            (lakes[0].id, "Mansfield Dam", "30.3916,-97.8827"),
            (lakes[0].id, "Arkansas Bend", "30.4505,-97.9486"),
            (lakes[1].id, "Red Bud Isle", "30.2991,-97.7946"),
            (lakes[2].id, "Festival Beach", "30.2487,-97.7132"),
        ]
        for lake_id, name, coords in ramp_data:
            ramp = Ramp(lake_id=lake_id, name=name, coordinates=coords)
            ramps.append(ramp)
            session.add(ramp)
        session.flush()

        # Create test events and tournaments
        print("  Creating events and tournaments...")
        current_date = now_local()
        for month_offset in range(-2, 4):  # 2 past, 4 future
            event_date = datetime(current_date.year, current_date.month, 15) + timedelta(
                days=30 * month_offset
            )

            # Skip if date is invalid
            if event_date.month < 1 or event_date.month > 12:
                continue

            event = Event(
                date=event_date,
                name=f"Test Tournament {event_date.strftime('%B %Y')}",
                event_type="tournament",
                year=event_date.year,
            )
            session.add(event)
            session.flush()

            # Select lake and ramp (rotate through them)
            lake_idx = month_offset % len(lakes)
            ramp_idx = month_offset % len(ramps)
            selected_lake = lakes[lake_idx]
            selected_ramp = ramps[ramp_idx]

            # Create tournament for event
            is_past = month_offset < 0
            tournament = Tournament(
                event_id=event.id,
                lake_id=selected_lake.id,
                ramp_id=selected_ramp.id,
                complete=is_past,
                created_by=admin.id,
            )
            session.add(tournament)
            session.flush()

            # Create poll for tournament location
            poll_starts = event_date - timedelta(days=21)
            poll_closes = event_date - timedelta(days=7)

            poll = Poll(
                event_id=event.id,
                title=f"Vote for {event_date.strftime('%B %Y')} Tournament Location",
                poll_type="tournament_location",
                starts_at=poll_starts,
                closes_at=poll_closes,
                created_by=admin.id,
            )
            session.add(poll)
            session.flush()

            # Create poll options (2 options per poll)
            for opt_idx in range(2):
                option_lake = lakes[(lake_idx + opt_idx) % len(lakes)]
                option_ramp = ramps[(ramp_idx + opt_idx) % len(ramps)]

                option = PollOption(
                    poll_id=poll.id,
                    option_text=f"{option_lake.name} - {option_ramp.name}",
                    option_data=f'{{"lake_id": {option_lake.id}, "ramp_id": {option_ramp.id}}}',
                )
                session.add(option)
            session.flush()

            # Create results for past tournaments
            if is_past:
                print(f"    Adding results for {event.name}...")
                for idx, member in enumerate(members[:8]):  # Top 8 finishers
                    # Simulate realistic weights (decreasing order)
                    total_weight = Decimal("15.50") - Decimal(str(idx * 1.5))
                    big_bass = Decimal("5.25") - Decimal(str(idx * 0.4))
                    num_fish = 5

                    result = Result(
                        tournament_id=tournament.id,
                        angler_id=member.id,
                        num_fish=num_fish,
                        total_weight=total_weight,
                        big_bass_weight=big_bass,
                        dead_fish_penalty=Decimal("0.00"),
                        points=100 - (idx * 10),  # Points decrease for lower places
                    )
                    session.add(result)
                session.flush()

        # Create test news posts
        print("  Creating news posts...")
        news_posts = [
            (
                "Welcome to SABC Staging!",
                "This is the staging environment for testing new features. All data here is for testing purposes only.",
            ),
            (
                "Tournament Season Starting Soon",
                "Get ready for another exciting season of bass fishing! Check the calendar for upcoming events.",
            ),
            (
                "New Features Coming",
                "We're working on some exciting new features. Test them here first before they go to production!",
            ),
        ]

        for idx, (title, content) in enumerate(news_posts):
            news_date = current_date - timedelta(days=(len(news_posts) - idx) * 7)
            news = News(
                title=title,
                content=content,
                date=news_date,
                author_id=admin.id,
            )
            session.add(news)

        session.commit()

    # Print summary
    print("\n✅ Staging data seeded successfully!")
    print("\n📊 Summary:")
    print("   • 1 admin user (admin@staging.sabc.test)")
    print("   • 10 member users (member1-10@staging.sabc.test)")
    print("   • 3 lakes with 4 boat ramps")
    print("   • 6 events with tournaments")
    print("   • 6 location polls")
    print("   • Results for past tournaments")
    print("   • 3 news posts")
    print("\n🔑 Test Credentials:")
    print("   Admin:    admin@staging.sabc.test / TestPassword123!")
    print("   Members:  member1-10@staging.sabc.test / TestPassword123!")
    print("\n🌐 Ready to test!")


if __name__ == "__main__":
    try:
        seed_staging_data()
    except Exception as e:
        print(f"\n❌ Error seeding data: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
