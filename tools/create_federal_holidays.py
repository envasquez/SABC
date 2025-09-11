#!/usr/bin/env python3
"""
Create federal holidays for 2025-2065 and insert into calendar_events table.
Federal holidays as per U.S. federal law.
"""

import sqlite3
from datetime import date, timedelta
from typing import List, Tuple


def get_nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """Get the nth occurrence of a weekday in a given month/year."""
    first_day = date(year, month, 1)
    # Find first occurrence of the weekday
    days_ahead = weekday - first_day.weekday()
    if days_ahead < 0:
        days_ahead += 7
    first_occurrence = first_day + timedelta(days=days_ahead)
    return first_occurrence + timedelta(weeks=n - 1)


def get_last_weekday(year: int, month: int, weekday: int) -> date:
    """Get the last occurrence of a weekday in a given month/year."""
    # Start from the last day of the month and work backwards
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)

    days_back = (last_day.weekday() - weekday) % 7
    return last_day - timedelta(days=days_back)


def calculate_federal_holidays(year: int) -> List[Tuple[str, date, str]]:
    """Calculate all federal holidays for a given year."""
    holidays = []

    # New Year's Day - January 1
    holidays.append(
        (
            "New Year's Day",
            date(year, 1, 1),
            "Federal holiday celebrating the beginning of the new year.",
        )
    )

    # Martin Luther King Jr. Day - 3rd Monday in January
    mlk_day = get_nth_weekday(year, 1, 0, 3)  # 0 = Monday
    holidays.append(
        (
            "Martin Luther King Jr. Day",
            mlk_day,
            "Federal holiday honoring civil rights leader Martin Luther King Jr.",
        )
    )

    # Presidents' Day - 3rd Monday in February
    presidents_day = get_nth_weekday(year, 2, 0, 3)
    holidays.append(
        ("Presidents' Day", presidents_day, "Federal holiday honoring all U.S. presidents.")
    )

    # Memorial Day - Last Monday in May
    memorial_day = get_last_weekday(year, 5, 0)
    holidays.append(
        (
            "Memorial Day",
            memorial_day,
            "Federal holiday honoring military personnel who died in service.",
        )
    )

    # Juneteenth - June 19
    holidays.append(
        (
            "Juneteenth National Independence Day",
            date(year, 6, 19),
            "Federal holiday commemorating the emancipation of enslaved African Americans.",
        )
    )

    # Independence Day - July 4
    holidays.append(
        (
            "Independence Day",
            date(year, 7, 4),
            "Federal holiday celebrating the Declaration of Independence.",
        )
    )

    # Labor Day - 1st Monday in September
    labor_day = get_nth_weekday(year, 9, 0, 1)
    holidays.append(
        ("Labor Day", labor_day, "Federal holiday celebrating the contributions of workers.")
    )

    # Columbus Day - 2nd Monday in October
    columbus_day = get_nth_weekday(year, 10, 0, 2)
    holidays.append(
        (
            "Columbus Day",
            columbus_day,
            "Federal holiday commemorating Christopher Columbus's arrival in the Americas.",
        )
    )

    # Veterans Day - November 11
    holidays.append(
        ("Veterans Day", date(year, 11, 11), "Federal holiday honoring military veterans.")
    )

    # Thanksgiving Day - 4th Thursday in November
    thanksgiving = get_nth_weekday(year, 11, 3, 4)  # 3 = Thursday
    holidays.append(
        (
            "Thanksgiving Day",
            thanksgiving,
            "Federal holiday for giving thanks and celebrating the harvest.",
        )
    )

    # Christmas Day - December 25
    holidays.append(
        (
            "Christmas Day",
            date(year, 12, 25),
            "Federal holiday celebrating the birth of Jesus Christ.",
        )
    )

    return holidays


def main():
    """Generate and insert federal holidays for 2025-2065."""
    conn = sqlite3.connect("sabc.db")
    cursor = conn.cursor()

    all_holidays = []

    # Generate holidays for each year from 2025 to 2065
    for year in range(2025, 2066):
        year_holidays = calculate_federal_holidays(year)
        all_holidays.extend(year_holidays)

    # Insert holidays into events table (not calendar_events)
    insert_query = """
        INSERT INTO events (date, year, name, event_type, description, holiday_name)
        VALUES (?, ?, ?, 'federal_holiday', ?, ?)
    """

    for title, event_date, description in all_holidays:
        cursor.execute(
            insert_query, (event_date.isoformat(), event_date.year, title, description, title)
        )

    conn.commit()
    print(f"Successfully inserted {len(all_holidays)} federal holidays from 2025-2065")

    # Show summary
    cursor.execute("SELECT COUNT(*) FROM events WHERE event_type = 'federal_holiday'")
    total_count = cursor.fetchone()[0]
    print(f"Total holidays in database: {total_count}")

    conn.close()


if __name__ == "__main__":
    main()
