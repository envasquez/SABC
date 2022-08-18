# -*- coding: utf-8 -*-
"""App registration file"""
from __future__ import unicode_literals

from django.contrib import admin

from .models import Tournament, Result, TeamResult, RuleSet


for model in [Tournament, Result, TeamResult, RuleSet]:
    admin.site.register(model)
