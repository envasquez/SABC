# -*- coding: utf-8 -*-
import datetime

import pytz
from django.db.models import (
    CharField,
    DateField,
    Model,
    QuerySet,
    SmallIntegerField,
    TextChoices,
    TimeField,
)

DEFAULT_MEETING_START: datetime.time = datetime.datetime.time(
    datetime.datetime.strptime("7:00 pm", "%I:%M %p")
)
DEFAULT_MEETING_FINISH: datetime.time = datetime.datetime.time(
    datetime.datetime.strptime("8:00 pm", "%I:%M %p")
)
DEFAULT_TOURNAMENT_START: datetime.time = datetime.datetime.time(
    datetime.datetime.strptime("12:00 am", "%I:%M %p")
)
DEFAULT_TOURNAMENT_FINISH: datetime.time = datetime.datetime.time(
    datetime.datetime.strptime("12:00 am", "%I:%M %p")
)


class Events(Model):
    class Meta:
        ordering: tuple[str] = ("-year",)
        verbose_name_plural: str = "Events"

    class EventTypes(TextChoices):
        MEETING: str = "meeting"
        TOURNAMNET: str = "tournament"

    class Months(TextChoices):
        JANUARY: str = "january"
        FEBRUARY: str = "february"
        MARCH: str = "march"
        APRIL: str = "april"
        MAY: str = "may"
        JUNE: str = "june"
        JULY: str = "july"
        AUGUST: str = "august"
        SEPTEMBER: str = "september"
        OCTOBER: str = "october"
        NOVEMBER: str = "november"
        DECEMBER: str = "december"

    date: DateField = DateField(null=True, blank=True)
    type: CharField = CharField(
        choices=EventTypes.choices, default="tournament", max_length=25
    )
    year: SmallIntegerField = SmallIntegerField(default=datetime.date.today().year)
    month: CharField = CharField(choices=Months.choices, max_length=20)
    start: TimeField = TimeField(null=True, blank=True)
    finish: TimeField = TimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.type} {self.date} {self.start}-{self.finish}".title()

    def as_html(self) -> str:
        dmy = self.date.strftime("%d %B %Y")
        start = self.start.strftime("%I:%M %p")
        finish = self.finish.strftime("%I:%M %p")
        if self.start == self.finish:
            return f"{self.type.upper()}<br />{dmy} Time: TBD<br />"
        return f"{self.type.upper()}<br />{dmy}<br />{start}-{finish}<br />"

    def save(self, *args, **kwargs) -> None:
        if not self.start:
            if self.type == "tournament":
                self.start = DEFAULT_TOURNAMENT_START
            elif self.type == "meeting":
                self.start = DEFAULT_MEETING_START
        if not self.finish:
            if self.type == "tournament":
                self.finish = DEFAULT_TOURNAMENT_FINISH
            elif self.type == "meeting":
                self.finish = DEFAULT_MEETING_FINISH
        super().save(*args, **kwargs)


def get_next_event(event_type: str, today: datetime.date) -> Events | None:
    """Return the next event, relative to 'today'"""
    if not Events.objects.filter(type=event_type):
        return None
    events: QuerySet = Events.objects.filter(type=event_type, year=today.year).order_by(
        "date"
    )
    next_event: Events | None = None
    for idx, event in enumerate(events):
        current_month: bool = event.date.month == today.month
        current_year: bool = event.year == today.year
        now: datetime.datetime = datetime.datetime.now(pytz.timezone("US/Central"))
        if all(
            [
                current_year,
                current_month,
                now.day <= event.date.day,
                now.hour <= event.start.hour,
            ]
        ):
            next_event = event
        else:
            next_event = events[idx + 1] if idx + 1 < events.count() else None
        if (
            today.month == 12
        ):  # Last event of the year, get the first event for next year ...
            next_event = (
                Events.objects.filter(type=event_type, year=today.year + 1)
                .order_by("date")
                .first()
            )
        if next_event:
            break

    return next_event
