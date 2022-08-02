# -*- coding: utf-8 -*-
# Using a file level pylint disable here because of the use of the Django signals feature
# pylint: disable=import-outside-toplevel, unused-import
"""AppConfig file"""
from __future__ import unicode_literals

from django.apps import AppConfig


class UsersConfig(AppConfig):
    """User config"""

    name = "users"

    def ready(self):
        """Ready signal"""
        from . import signals
