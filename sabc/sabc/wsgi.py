# -*- coding: utf-8 -*-
from typing import Type

import os

from django.core.wsgi import get_wsgi_application
from django.core.handlers.wsgi import WSGIHandler


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sabc.settings")

application: Type[WSGIHandler] = get_wsgi_application()
