#!/usr/bin/env python3
"""Create tournament events for a given year (Jan-Oct, 4th Sunday of each month).

This script creates SABC tournament events for the 4th Sunday of each month
from January through October. Events are created WITHOUT polls - polls can
be created later through the admin UI.

Usage:
    DATABASE_URL='postgresql://...' python scripts/create_yearly_events.py 2026

Arguments:
    year: The year to create events for (e.g., 2026)

Options:
    --dry-run: Show what would be created without actually creating events
"""

import argparse
import os
import sys
from calendar import Calendar
from datetime import date

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db_schema import get_session  # noqa: E402
from core.db_schema.models import Event, Tournament  # noqa: E402

# Month names for event naming
MONTH_NAMES = [
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
]


def get_fourth_sunday(year: int, month: int) -> date:
    """Get the 4th Sunday of a given month.

    Args:
        year: The year
        month: The month (1-12)

    Returns:
        The date of the 4th Sunday
    """
    cal = Calendar()
    sundays = [
        day
        for day in cal.itermonthdays2(year, month)
        if day[0] != 0 and day[1] == 6  # day[1] == 6 is Sunday
    ]
    # Get the 4th Sunday (index 3)
    fourth_sunday_day = sundays[3][0]
    return date(year, month, fourth_sunday_day)


def create_yearly_events(year: int, dry_run: bool = False) -> None:
    """Create tournament events for January through October of the given year.

    Args:
        year: The year to create events for
        dry_run: If True, only print what would be created
    """
    print(f"{'[DRY RUN] ' if dry_run else ''}Creating events for {year}...")

    events_to_create = []

    # Generate events for January through October (months 1-10)
    for month in range(1, 11):
        tournament_date = get_fourth_sunday(year, month)
        month_name = MONTH_NAMES[month - 1]
        event_name = f"{month_name} Tournament"

        events_to_create.append(
            {
                "date": tournament_date,
                "name": event_name,
                "month": month_name,
            }
        )

    # Print what will be created
    print(f"\n{'Would create' if dry_run else 'Creating'} {len(events_to_create)} events:\n")
    for event in events_to_create:
        print(
            f"  {event['date'].strftime('%Y-%m-%d')} ({event['date'].strftime('%A')}) - {event['name']}"
        )

    if dry_run:
        print("\n[DRY RUN] No events created. Remove --dry-run to create events.")
        return

    # Create events in database
    print("\nCreating events in database...")

    with get_session() as session:
        created_count = 0
        skipped_count = 0

        for event_data in events_to_create:
            # Check if event already exists for this date
            existing = (
                session.query(Event)
                .filter(Event.date == event_data["date"], Event.year == year)
                .first()
            )

            if existing:
                print(
                    f"  ⚠️  Skipping {event_data['name']} - event already exists for {event_data['date']}"
                )
                skipped_count += 1
                continue

            # Create event
            event = Event(
                date=event_data["date"],
                year=year,
                name=event_data["name"],
                event_type="sabc_tournament",
                description=f"SABC {event_data['month']} Tournament",
            )
            session.add(event)
            session.flush()

            # Create tournament record linked to event
            # For 2026+, use team format defaults
            is_new_format = year >= 2026
            tournament = Tournament(
                event_id=event.id,
                name=event_data["name"],
                fish_limit=5,
                entry_fee=50.00 if is_new_format else 25.00,
                is_team=True,
                limit_type="boat" if is_new_format else "angler",
                aoy_points=not is_new_format,  # No AoY points for 2026+
            )
            session.add(tournament)

            print(f"  ✅ Created {event_data['name']} ({event_data['date']})")
            created_count += 1

    print(f"\n✅ Done! Created {created_count} events, skipped {skipped_count} existing.")
    if created_count > 0:
        print("\n💡 Tip: Use the admin UI at /admin/polls/create to create polls for these events.")


def main() -> None:
    """Parse arguments and run the script."""
    parser = argparse.ArgumentParser(
        description="Create tournament events for a given year (Jan-Oct, 4th Sunday of each month)"
    )
    parser.add_argument("year", type=int, help="The year to create events for (e.g., 2026)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be created without actually creating events",
    )

    args = parser.parse_args()

    # Validate year
    if args.year < 2024 or args.year > 2100:
        print(f"Error: Year must be between 2024 and 2100, got {args.year}")
        sys.exit(1)

    create_yearly_events(args.year, args.dry_run)


if __name__ == "__main__":
    main()
