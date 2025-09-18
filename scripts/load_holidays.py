#!/usr/bin/env python3
"""
Load federal holidays into the database for specified years.
This script populates the events table with holiday entries.
"""

import logging
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import db
from core.validators import get_federal_holidays

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_holidays_for_year(year: int, dry_run: bool = False) -> int:
    """
    Load holidays for a specific year into the events table.

    Args:
        year: The year to generate holidays for
        dry_run: If True, only show what would be inserted without actually doing it

    Returns:
        Number of holidays inserted
    """
    holidays = get_federal_holidays(year)
    inserted = 0
    skipped = 0

    logger.info(
        f"{'[DRY RUN] ' if dry_run else ''}Loading {len(holidays)} holidays for year {year}"
    )

    for holiday_date, holiday_name in holidays:
        try:
            # Check if this date already has an event
            existing = db(
                "SELECT id, name, event_type FROM events WHERE date = :date", {"date": holiday_date}
            )

            if existing:
                logger.info(
                    f"  Skipping {holiday_date}: Already has event '{existing[0][1]}' (type: {existing[0][2]})"
                )
                skipped += 1
                continue

            if dry_run:
                logger.info(f"  Would insert: {holiday_date} - {holiday_name}")
                inserted += 1
            else:
                # Insert the holiday
                db(
                    """INSERT INTO events (date, year, name, event_type, holiday_name)
                       VALUES (:date, :year, :name, 'holiday', :holiday_name)""",
                    {
                        "date": holiday_date,
                        "year": year,
                        "name": holiday_name,
                        "holiday_name": holiday_name,
                    },
                )
                logger.info(f"  Inserted: {holiday_date} - {holiday_name}")
                inserted += 1

        except Exception as e:
            logger.error(f"  Error inserting {holiday_date} - {holiday_name}: {e}")

    logger.info(
        f"{'[DRY RUN] ' if dry_run else ''}Summary: {inserted} holidays {'would be ' if dry_run else ''}inserted, {skipped} skipped"
    )
    return inserted


def main():
    """Main entry point for the script."""
    import argparse

    parser = argparse.ArgumentParser(description="Load federal holidays into the database")
    parser.add_argument(
        "years", nargs="+", type=int, help="Year(s) to load holidays for (e.g., 2025 or 2025 2026)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be inserted without actually inserting",
    )
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL", "postgresql://postgres:dev123@localhost:5432/sabc"),
        help="Database connection URL",
    )

    args = parser.parse_args()

    # Override database URL if provided
    os.environ["DATABASE_URL"] = args.database_url

    logger.info(
        f"Connecting to database: {args.database_url.split('@')[1] if '@' in args.database_url else args.database_url}"
    )

    total_inserted = 0

    for year in args.years:
        current_year = datetime.now().year
        if year < current_year - 10 or year > current_year + 10:
            logger.warning(f"Year {year} seems unusual (current year is {current_year}). Skipping.")
            continue

        try:
            inserted = load_holidays_for_year(year, dry_run=args.dry_run)
            total_inserted += inserted
        except Exception as e:
            logger.error(f"Failed to load holidays for year {year}: {e}")
            return 1

    logger.info(
        f"\n{'[DRY RUN] ' if args.dry_run else ''}Total: {total_inserted} holidays {'would be ' if args.dry_run else ''}inserted across {len(args.years)} year(s)"
    )

    if args.dry_run:
        logger.info("\nThis was a dry run. Use without --dry-run to actually insert holidays.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
