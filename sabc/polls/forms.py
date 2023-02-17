# -*- coding: utf-8 -*-
from typing import Type

from django.forms import ModelForm

from .models import LakePoll


class LakePollForm(ModelForm):
    class Meta:
        model: Type[LakePoll] = LakePoll
        fields: str = "__all__"
