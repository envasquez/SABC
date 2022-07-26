# -*- coding: utf-8 -*-
# pylint: disable=all
from __future__ import unicode_literals

from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = 'users'

    def ready(self):
        from . import signals
