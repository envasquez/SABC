#!/usr/bin/env python
# pylint: disable-all
"""Django's managment untility entrypoint"""
import os
import sys


DEFAULT_SETTINGS_MODULE = "sabc.settings"


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", DEFAULT_SETTINGS_MODULE)
    try:
        from django.core.management import execute_from_command_line
    except ImportError:
        # The above import may fail for some other reason. Ensure that the
        # issue is really that Django is missing to avoid masking other
        # exceptions on Python 2.
        try:
            import django
        except ImportError as err:
            raise ImportError(
                "Couldn't import Django. Are you sure it's installed and "
                "available on your PYTHONPATH environment variable? Did you "
                "forget to activate a virtual environment?"
            )
        raise

    execute_from_command_line(sys.argv)
