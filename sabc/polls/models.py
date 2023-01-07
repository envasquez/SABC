# -*- coding: utf-8 -*-
from time import strftime

from django.apps import apps
from django.db.models import (
    Model,
    CASCADE,
    DateField,
    CharField,
    TextField,
    ForeignKey,
    ManyToManyField,
)

# Lake = apps.get_model("tournaments", "Lake")
# Angler = apps.get_model("users", "Angler")
from users.models import Angler
from tournaments.models.lakes import Lake

CURRENT_YEAR = f"{strftime('%Y')}"
CURRENT_MONTH = f"{strftime('%B')}"


class LakePoll(Model):
    name = CharField(default=f"Lake Poll: {CURRENT_MONTH} {CURRENT_YEAR}", max_length=256)
    choices = ManyToManyField(Lake)
    description = TextField(max_length=4096, null=True, blank=True)

    def __str__(self):
        return self.name


class LakeVote(Model):
    poll = ForeignKey(LakePoll, on_delete=CASCADE)
    choice = ForeignKey(Lake, on_delete=CASCADE)
    angler = ForeignKey(Angler, on_delete=CASCADE)
    timestamp = DateField(auto_now=True)

    def __str__(self):
        return f"{self.poll}: {self.choice} {self.angler}"
