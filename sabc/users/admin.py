# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.apps import apps

from django.contrib import admin

from users.models import Profile

admin.site.register(Profile)
