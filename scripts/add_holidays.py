#!/usr/bin/env python3
"""Add federal holidays to events table for years 2025-2030."""

from routes.dependencies import db
from routes.dependencies.holidays import get_federal_holidays


def add_federal_holidays(start_year: int, end_year: int) -> None:
    """Add federal holidays to events table for specified year range.

    Args:
        start_year: First year to add holidays for
        end_year: Last year to add holidays for (inclusive)
    """
    added_count = 0
    skipped_count = 0

    for year in range(start_year, end_year + 1):
        holidays = get_federal_holidays(year)

        for holiday_date, holiday_name in holidays:
            # Check if holiday already exists
            existing = db(
                "SELECT id FROM events WHERE date = :date AND event_type = 'holiday'",
                {"date": holiday_date},
            )

            if existing:
                print(f"  ⏭️  Skipped: {holiday_date} - {holiday_name} (already exists)")
                skipped_count += 1
                continue

            # Insert holiday event
            db(
                """INSERT INTO events (date, year, name, event_type, description, holiday_name)
                   VALUES (:date, :year, :name, 'holiday', :description, :holiday_name)""",
                {
                    "date": holiday_date,
                    "year": year,
                    "name": holiday_name,
                    "description": f"Federal Holiday: {holiday_name}",
                    "holiday_name": holiday_name,
                },
            )
            print(f"  ✅ Added: {holiday_date} - {holiday_name}")
            added_count += 1

    print("\n📊 Summary:")
    print(f"   Added: {added_count} holidays")
    print(f"   Skipped: {skipped_count} holidays (already existed)")
    print(f"   Total processed: {added_count + skipped_count} holidays")


if __name__ == "__main__":
    print("🎉 Adding Federal Holidays (2025-2030)\n")
    add_federal_holidays(2025, 2030)
    print("\n✨ Done!")
