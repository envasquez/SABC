# -*- coding: utf-8 -*-

from django.db import models
from django.utils import timezone


class CalendarEvent(models.Model):
    """Extended event model for calendar display including holidays, external tournaments, and lake events"""

    class EventCategory(models.TextChoices):
        TOURNAMENT = "tournament", "SABC Tournament"
        HOLIDAY = "holiday", "Holiday"
        EXTERNAL_TOURNAMENT = "external", "External Tournament"
        LAKE_EVENT = "lake", "Lake Event"
        CLUB_MEETING = "meeting", "Club Meeting"
        MAINTENANCE = "maintenance", "Lake Maintenance"
        CLOSURE = "closure", "Lake Closure"

    class EventPriority(models.TextChoices):
        LOW = "low", "Low"
        NORMAL = "normal", "Normal"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    title = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    date = models.DateField()
    start_time = models.TimeField(blank=True, null=True)
    end_time = models.TimeField(blank=True, null=True)
    category = models.CharField(
        max_length=20, choices=EventCategory.choices, default=EventCategory.TOURNAMENT
    )
    priority = models.CharField(
        max_length=10, choices=EventPriority.choices, default=EventPriority.NORMAL
    )
    lake = models.ForeignKey(
        "tournaments.Lake",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        help_text="Associated lake (if applicable)",
    )
    external_url = models.URLField(
        blank=True, null=True, help_text="Link to external event info"
    )

    # For recurring events like holidays
    is_recurring = models.BooleanField(default=False)
    recurring_type = models.CharField(
        max_length=20,
        choices=[
            ("yearly", "Yearly"),
            ("monthly", "Monthly"),
        ],
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["date", "start_time"]
        verbose_name = "Calendar Event"
        verbose_name_plural = "Calendar Events"

    def __str__(self):
        return f"{self.title} - {self.date}"

    @property
    def color_class(self):
        """Return CSS class for event category color coding"""
        color_map = {
            "tournament": "sabc-tournament",
            "holiday": "sabc-holiday",
            "external": "sabc-external",
            "lake": "sabc-lake-event",
            "meeting": "sabc-meeting",
            "maintenance": "sabc-maintenance",
            "closure": "sabc-closure",
        }
        return color_map.get(self.category, "sabc-default")  # type: ignore

    @property
    def icon_class(self):
        """Return Bootstrap icon class for event category"""
        icon_map = {
            "tournament": "bi-trophy",
            "holiday": "bi-calendar-heart",
            "external": "bi-calendar-plus",
            "lake": "bi-water",
            "meeting": "bi-people",
            "maintenance": "bi-tools",
            "closure": "bi-x-circle",
        }
        return icon_map.get(self.category, "bi-calendar-event")  # type: ignore

    @classmethod
    def get_events_for_year(cls, year=None):
        """Get all events for a specific year"""
        if year is None:
            year = timezone.now().year
        return cls.objects.filter(date__year=year)

    @classmethod
    def get_events_for_month(cls, year, month):
        """Get events for a specific month"""
        return cls.objects.filter(date__year=year, date__month=month)

    @classmethod
    def get_upcoming_events(cls, limit=10):
        """Get upcoming events from today"""
        today = timezone.now().date()
        return cls.objects.filter(date__gte=today)[:limit]


def create_default_holidays(year):
    """Helper function to create common holidays for a year"""
    holidays = [
        {"title": "New Year's Day", "date": f"{year}-01-01", "category": "holiday"},
        {
            "title": "Martin Luther King Day",
            "date": f"{year}-01-15",
            "category": "holiday",
        },  # Approximate
        {
            "title": "Presidents Day",
            "date": f"{year}-02-19",
            "category": "holiday",
        },  # Approximate
        {
            "title": "Memorial Day",
            "date": f"{year}-05-27",
            "category": "holiday",
        },  # Approximate
        {"title": "Independence Day", "date": f"{year}-07-04", "category": "holiday"},
        {
            "title": "Labor Day",
            "date": f"{year}-09-02",
            "category": "holiday",
        },  # Approximate
        {
            "title": "Thanksgiving",
            "date": f"{year}-11-28",
            "category": "holiday",
        },  # Approximate
        {"title": "Christmas Day", "date": f"{year}-12-25", "category": "holiday"},
    ]

    for holiday_data in holidays:
        CalendarEvent.objects.get_or_create(
            title=holiday_data["title"],
            date=holiday_data["date"],
            defaults={
                "category": holiday_data["category"],
                "is_recurring": True,
                "recurring_type": "yearly",
                "priority": "normal",
            },
        )
