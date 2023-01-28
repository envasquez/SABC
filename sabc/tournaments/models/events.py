# -*- coding: utf-8 -*-
import calendar
import datetime

from django.db.models import (
    CharField,
    DateField,
    Model,
    SmallIntegerField,
    TextChoices,
    TimeField,
)

DEFAULT_MEETING_START: datetime.time = datetime.datetime.time(datetime.datetime.strptime("7:00 pm", "%I:%M %p"))
DEFAULT_MEETING_FINISH: datetime.time = datetime.datetime.time(datetime.datetime.strptime("8:00 pm", "%I:%M %p"))
DEFAULT_TOURNAMENT_START: datetime.time = datetime.datetime.time(datetime.datetime.strptime("6:00 am", "%I:%M %p"))
DEFAULT_TOURNAMENT_FINISH: datetime.time = datetime.datetime.time(datetime.datetime.strptime("3:00 pm", "%I:%M %p"))


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
    type: CharField = CharField(choices=EventTypes.choices, default="tournament", max_length=25)
    year: SmallIntegerField = SmallIntegerField(default=datetime.date.today().year)
    month: CharField = CharField(
        choices=Months.choices, default=datetime.date.today().strftime("%B").lower(), max_length=20
    )
    start: TimeField = TimeField(null=True, blank=True)
    finish: TimeField = TimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.type} {self.date} {self.start}-{self.finish}".title()

    def as_html(self, date_only=True):
        dmy = self.date.strftime("%d %B %Y")
        start = self.start.strftime("%I %p")
        finish = self.finish.strftime("%I %p")
        if date_only:
            return f"{self.type.title()} {dmy}<br />"
        return f"{self.type.title()} {dmy}<br />{start}-{finish}<br />"

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


def get_next_event(event_type):
    today = datetime.date.today()
    year = today.year
    month = today.month
    try:
        event = Events.objects.get(type=event_type, month=calendar.month_name[month], year=year)
    except Exception:
        return None
    if today.day < event.date.day:
        return event
    month += 1
    if month == 12:
        year += year
        month = 1
    return Events.objects.get(type=event_type, month=calendar.month_name[month], year=year)
