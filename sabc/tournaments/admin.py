# -*- coding: utf-8 -*-
"""Tournaments"""
# pylint: disable=import-error
from __future__ import unicode_literals

from django.contrib import admin

from .models import Tournament, Result, PaperResult, Team, Rules


for model in [Tournament, Result, PaperResult, Team, Rules]:
    admin.site.register(model)
