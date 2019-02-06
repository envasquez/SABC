# -*- coding: utf-8 -*-
"""Tournaments"""
# pylint: disable=import-error
from __future__ import unicode_literals


from django.contrib import admin

from .models import Event, Tournament

admin.site.register([Event, Tournament])
