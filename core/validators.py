import re
from datetime import date, datetime, timedelta

from core.database import db


def validate_event_data(
    date_str, name, event_type, start_time=None, weigh_in_time=None, entry_fee=None
):
    errors = []
    warnings = []

    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    if date_obj.date() < datetime.now().date():
        warnings.append(f"Creating event for past date: {date_str}")

    existing = db("SELECT id, name FROM events WHERE date = :date", {"date": date_str})
    if existing:
        existing_name = existing[0][1]
        warnings.append(f"Date {date_str} already has event: {existing_name}")

    if not name or len(name.strip()) < 3:
        errors.append("Event name must be at least 3 characters")

    if event_type == "sabc_tournament":
        if start_time:
            if not re.match(r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$", start_time):
                errors.append("Invalid start time format. Use HH:MM (24-hour)")

        if weigh_in_time:
            if not re.match(r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$", weigh_in_time):
                errors.append("Invalid weigh-in time format. Use HH:MM (24-hour)")

        if start_time and weigh_in_time:
            start = datetime.strptime(start_time, "%H:%M").time()
            weigh_in = datetime.strptime(weigh_in_time, "%H:%M").time()
            if weigh_in <= start:
                errors.append("Weigh-in time must be after start time")

        if entry_fee is not None:
            if entry_fee < 0:
                errors.append("Entry fee cannot be negative")
            elif entry_fee > 200:
                warnings.append(f"Entry fee ${entry_fee} is unusually high for SABC tournament")

    elif event_type == "federal_holiday":
        if start_time or weigh_in_time or entry_fee:
            warnings.append("Federal holidays don't typically need tournament details")

    return {"errors": errors, "warnings": warnings}


def get_federal_holidays(year):
    holidays = []
    holidays.append((f"{year}-01-01", "New Year's Day"))
    holidays.append((f"{year}-07-04", "Independence Day"))
    holidays.append((f"{year}-11-11", "Veterans Day"))
    holidays.append((f"{year}-12-25", "Christmas Day"))

    jan_1 = date(year, 1, 1)
    days_to_monday = (7 - jan_1.weekday()) % 7
    first_monday = jan_1 + timedelta(days=days_to_monday)
    mlk_day = first_monday + timedelta(days=14)
    holidays.append((mlk_day.strftime("%Y-%m-%d"), "Martin Luther King Jr. Day"))

    feb_1 = date(year, 2, 1)
    days_to_monday = (7 - feb_1.weekday()) % 7
    first_monday = feb_1 + timedelta(days=days_to_monday)
    presidents_day = first_monday + timedelta(days=14)
    holidays.append((presidents_day.strftime("%Y-%m-%d"), "Presidents Day"))

    may_31 = date(year, 5, 31)
    days_back = (may_31.weekday() + 1) % 7
    memorial_day = may_31 - timedelta(days=days_back)
    holidays.append((memorial_day.strftime("%Y-%m-%d"), "Memorial Day"))

    sep_1 = date(year, 9, 1)
    days_to_monday = (7 - sep_1.weekday()) % 7
    labor_day = sep_1 + timedelta(days=days_to_monday)
    holidays.append((labor_day.strftime("%Y-%m-%d"), "Labor Day"))

    nov_1 = date(year, 11, 1)
    days_to_thursday = (3 - nov_1.weekday()) % 7
    first_thursday = nov_1 + timedelta(days=days_to_thursday)
    thanksgiving = first_thursday + timedelta(days=21)
    holidays.append((thanksgiving.strftime("%Y-%m-%d"), "Thanksgiving Day"))

    return sorted(holidays)
