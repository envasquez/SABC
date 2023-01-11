# -*- coding: utf-8 -*-
from django.apps import AppConfig


class PollsConfig(AppConfig):
    default_auto_field: str = "django.db.models.BigAutoField"
    name: str = "polls"
