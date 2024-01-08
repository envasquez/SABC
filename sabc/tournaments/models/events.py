# -*- coding: utf-8 -*-
import datetime

from django.db.models import (
    CharField,
    DateField,
    Model,
    QuerySet,
    SmallIntegerField,
    TextChoices,
    TimeField,
)
from django.utils import timezone
from django.db.models import Q


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
    """Return the next event, relative to today'"""
    now = timezone.now()
    year = now.year
    events = (
        Events.objects.filter(Q(year=year, date__gte=now) | Q(year=year + 1))
        .filter(type=event_type)
        .order_by("date")
    )

    if not events.exists():
        return None

    return events.first()
