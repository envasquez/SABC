# -*- coding: utf-8 -*-
from django.forms import ModelForm

from .models import LakePoll


class LakePollForm(ModelForm):
    class Meta:
        model = LakePoll
        fields = "__all__"
