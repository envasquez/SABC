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


def get_next_event(event_type: str) -> Events | None:
    """Return the next event, relative to 'today'"""
    now: datetime.datetime = datetime.datetime.now(pytz.timezone("US/Central"))
    year: int = now.year
    if (
        now.month == 12 and now.day > 15
    ):  # We never fish past this date ... goto next year
        year += 1

    events: QuerySet = Events.objects.filter(type=event_type, year=year)
    if not events:
        return None

    current_event: Events = events[now.month - 1]  # Offset for 0th element
    if current_event.date.month == now.month:
        if now.day <= current_event.date.day:
            return current_event

    return events[now.month]
