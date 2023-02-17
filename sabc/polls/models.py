# -*- coding: utf-8 -*-
from time import strftime

from django.db.models import (
    CASCADE,
    CharField,
    DateField,
    ForeignKey,
    ManyToManyField,
    Model,
    TextField,
)
from django.urls import reverse
from tournaments.models.lakes import Lake
from users.models import Angler

CURRENT_YEAR: str = f"{strftime('%Y')}"
CURRENT_MONTH: str = f"{strftime('%B')}"


class LakePoll(Model):
    name: CharField = CharField(default=f"Poll: {CURRENT_MONTH} {CURRENT_YEAR}", max_length=256)
    choices: ManyToManyField = ManyToManyField(Lake)
    description: TextField = TextField(max_length=4096, null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.name}"

    def get_absolute_url(self) -> str:
        return reverse("polls")


class LakeVote(Model):
    poll: ForeignKey = ForeignKey(LakePoll, on_delete=CASCADE)
    choice: ForeignKey = ForeignKey(Lake, on_delete=CASCADE)
    angler: ForeignKey = ForeignKey(Angler, on_delete=CASCADE)
    timestamp: DateField = DateField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.poll}: {self.choice} {self.angler}"
