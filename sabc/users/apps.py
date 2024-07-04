# -*- coding: utf-8 -*-
from django.apps import AppConfig


class UsersConfig(AppConfig):
    name: str = "users"

    def ready(self) -> None:
        # pylint: disable=unused-import, import-outside-toplevel
        pass
