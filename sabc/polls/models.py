# -*- coding: utf-8 -*-
from typing import Type

from time import strftime

from django.db.models import (
    Model,
    CASCADE,
    DateField,
    CharField,
    TextField,
    ForeignKey,
    ManyToManyField,
)

from users.models import Angler
from tournaments.models.lakes import Lake

CURRENT_YEAR: str = f"{strftime('%Y')}"
CURRENT_MONTH: str = f"{strftime('%B')}"


class LakePoll(Model):
    name: Type[CharField] = CharField(
        default=f"Poll: {CURRENT_MONTH} {CURRENT_YEAR}", max_length=256
    )
    choices: Type[ManyToManyField] = ManyToManyField(Lake)
    description: Type[TextField] = TextField(max_length=4096, null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.name}"


class LakeVote(Model):
    poll: Type[ForeignKey] = ForeignKey(LakePoll, on_delete=CASCADE)
    choice: Type[ForeignKey] = ForeignKey(Lake, on_delete=CASCADE)
    angler: Type[ForeignKey] = ForeignKey(Angler, on_delete=CASCADE)
    timestamp: Type[DateField] = DateField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.poll}: {self.choice} {self.angler}"
