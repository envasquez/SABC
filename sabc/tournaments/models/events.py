# -*- coding: utf-8 -*-
import datetime

from django.db.models import (
    CharField,
    DateField,
    Model,
    Q,
    SmallIntegerField,
    TextChoices,
    TimeField,
)
from django.utils import timezone

DEFAULT_MEETING_START = datetime.datetime.time(
    datetime.datetime.strptime("7:00 pm", "%I:%M %p")
)
DEFAULT_MEETING_FINISH = datetime.datetime.time(
    datetime.datetime.strptime("8:00 pm", "%I:%M %p")
)
DEFAULT_TOURNAMENT_START = datetime.datetime.time(
    datetime.datetime.strptime("12:00 am", "%I:%M %p")
)
DEFAULT_TOURNAMENT_FINISH = datetime.datetime.time(
    datetime.datetime.strptime("12:00 am", "%I:%M %p")
)


class Events(Model):
    class Meta:
        ordering = ("-year",)
        verbose_name_plural = "Events"

    class EventTypes(TextChoices):
        MEETING = "meeting"
        TOURNAMNET = "tournament"

    class Months(TextChoices):
        JANUARY = "january"
        FEBRUARY = "february"
        MARCH = "march"
        APRIL = "april"
        MAY = "may"
        JUNE = "june"
        JULY = "july"
        AUGUST = "august"
        SEPTEMBER = "september"
        OCTOBER = "october"
        NOVEMBER = "november"
        DECEMBER = "december"

    date = DateField(null=True, blank=True)
    type = CharField(choices=EventTypes.choices, default="tournament", max_length=25)
    year = SmallIntegerField(default=datetime.date.today().year)
    month = CharField(choices=Months.choices, max_length=20)
    start = TimeField(null=True, blank=True)
    finish = TimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.type} {self.date} {self.start}-{self.finish}".title()

    def as_html(self):
        dmy = self.date.strftime("%d %B %Y")
        start = self.start.strftime("%I:%M %p")
        finish = self.finish.strftime("%I:%M %p")
        if self.start == self.finish:
            return f"{self.type.upper()}<br />{dmy} Time: TBD<br />"
        return f"{self.type.upper()}<br />{dmy}<br />{start}-{finish}<br />"

    def save(self, *args, **kwargs):
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


def get_next_event(event_type):
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
