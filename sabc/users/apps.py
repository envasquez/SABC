# -*- coding: utf-8 -*-
from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = "users"

    def ready(self):
        # pylint: disable=unused-import, import-outside-toplevel
        from . import signals
