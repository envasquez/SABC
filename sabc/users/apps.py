# -*- coding: utf-8 -*-
from django.apps import AppConfig


class UsersConfig(AppConfig):
    """User config"""

    name = "users"

    def ready(self):
        """Ready signal"""
        from . import signals
