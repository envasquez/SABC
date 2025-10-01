"""Federal holidays calculation."""

from datetime import date, timedelta
from typing import List, Tuple


def get_federal_holidays(year: int) -> List[Tuple[str, str]]:
    """Get list of federal holidays for a given year.

    Args:
        year: The year to get holidays for

    Returns:
        List of tuples (date_string, holiday_name) sorted by date
    """
    holidays = [
        (f"{year}-01-01", "New Year's Day"),
        (f"{year}-07-04", "Independence Day"),
        (f"{year}-11-11", "Veterans Day"),
        (f"{year}-12-25", "Christmas Day"),
    ]
    jan_1 = date(year, 1, 1)
    mlk_day = jan_1 + timedelta(days=(7 - jan_1.weekday()) % 7 + 14)
    holidays.append((mlk_day.strftime("%Y-%m-%d"), "Martin Luther King Jr. Day"))
    feb_1 = date(year, 2, 1)
    presidents_day = feb_1 + timedelta(days=(7 - feb_1.weekday()) % 7 + 14)
    holidays.append((presidents_day.strftime("%Y-%m-%d"), "Presidents Day"))
    may_31 = date(year, 5, 31)
    memorial_day = may_31 - timedelta(days=(may_31.weekday() + 1) % 7)
    holidays.append((memorial_day.strftime("%Y-%m-%d"), "Memorial Day"))
    sep_1 = date(year, 9, 1)
    labor_day = sep_1 + timedelta(days=(7 - sep_1.weekday()) % 7)
    holidays.append((labor_day.strftime("%Y-%m-%d"), "Labor Day"))
    nov_1 = date(year, 11, 1)
    thanksgiving = nov_1 + timedelta(days=(3 - nov_1.weekday()) % 7 + 21)
    holidays.append((thanksgiving.strftime("%Y-%m-%d"), "Thanksgiving Day"))
    return sorted(holidays)
