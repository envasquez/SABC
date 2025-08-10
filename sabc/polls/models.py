# -*- coding: utf-8 -*-
import datetime
from time import strftime

import pytz
from django.db.models import (
    CASCADE,
    BooleanField,
    CharField,
    DateField,
    ForeignKey,
    ManyToManyField,
    Model,
    TextField,
    TimeField,
)
from django.urls import reverse
from tournaments.models.lakes import Lake
from users.models import Angler

CURRENT_YEAR = f"{strftime('%Y')}"
CURRENT_MONTH = f"{strftime('%B')}"
DEFAULT_END_TIME = datetime.datetime.time(
    datetime.datetime.strptime("07:00 pm", "%I:%M %p")
)


class LakePoll(Model):
    name = CharField(default=f"Poll: {CURRENT_MONTH} {CURRENT_YEAR}", max_length=256)
    choices = ManyToManyField(Lake)
    end_date = DateField(null=True, blank=True)
    end_time = TimeField(null=True, blank=True)
    complete = BooleanField(default=False)
    description = TextField(max_length=4096, null=True, blank=True)

    def __str__(self):
        return f"{self.name}"

    def get_absolute_url(self):
        return reverse("polls")

    def is_active(self):
        """Check if poll is currently accepting votes."""
        if self.complete or not self.end_date:
            return False

        today = datetime.date.today()
        if today > self.end_date:
            return False
        elif today == self.end_date:
            if self.end_time:
                now = datetime.datetime.now(pytz.timezone("US/Central"))
                end_datetime = datetime.datetime.combine(self.end_date, self.end_time)
                end_datetime = pytz.timezone("US/Central").localize(end_datetime)
                return now <= end_datetime
            return False
        return True

    def save(self, *args, **kwargs):
        if not self.end_time:
            self.end_time = DEFAULT_END_TIME
        if datetime.date.today() > self.end_date:  # pyright: ignore[reportOperatorIssue]
            self.complete = True
        elif datetime.date.today() == self.end_date:
            now = datetime.datetime.now(pytz.timezone("US/Central"))
            self.complete = now > self.end_time  # pyright: ignore[reportOperatorIssue]
        super().save(*args, **kwargs)


class LakeVote(Model):
    poll = ForeignKey(LakePoll, on_delete=CASCADE)
    choice = ForeignKey(Lake, on_delete=CASCADE)
    angler = ForeignKey(Angler, on_delete=CASCADE)
    timestamp = DateField(auto_now=True)

    def __str__(self):
        return f"{self.poll}: {self.choice} {self.angler}"
