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

CURRENT_YEAR: str = f"{strftime('%Y')}"
CURRENT_MONTH: str = f"{strftime('%B')}"
DEFAULT_END_TIME: datetime.time = datetime.datetime.time(
    datetime.datetime.strptime("07:00 pm", "%I:%M %p")
)


class LakePoll(Model):
    name: CharField = CharField(
        default=f"Poll: {CURRENT_MONTH} {CURRENT_YEAR}", max_length=256
    )
    choices: ManyToManyField = ManyToManyField(Lake)
    end_date: DateField = DateField(null=True, blank=True)
    end_time: TimeField = TimeField(null=True, blank=True)
    complete: BooleanField = BooleanField(default=False)
    description: TextField = TextField(max_length=4096, null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.name}"

    def get_absolute_url(self) -> str:
        return reverse("polls")

    def save(self, *args, **kwargs) -> None:
        if not self.end_time:
            self.end_time = DEFAULT_END_TIME
        if datetime.date.today() > self.end_date:
            self.complete = True
        elif datetime.date.today() == self.end_date:
            self.complete = datetime.datetime.now(pytz.timezone("US/Central")) > self.end_time
        super().save(*args, **kwargs)


class LakeVote(Model):
    poll: ForeignKey = ForeignKey(LakePoll, on_delete=CASCADE)
    choice: ForeignKey = ForeignKey(Lake, on_delete=CASCADE)
    angler: ForeignKey = ForeignKey(Angler, on_delete=CASCADE)
    timestamp: DateField = DateField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.poll}: {self.choice} {self.angler}"
