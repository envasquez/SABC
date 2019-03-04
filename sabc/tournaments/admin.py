# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from .models import Tournament, Result, PaperResult, Team, RuleSet


for model in [Tournament, Result, PaperResult, Team, RuleSet]:
    admin.site.register(model)
