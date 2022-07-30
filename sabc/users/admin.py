# -*- coding: utf-8 -*-
# pylint: disable=all
from __future__ import unicode_literals

from django.apps import apps

from django.contrib import admin

from users.models import Angler

admin.site.register(Angler)
