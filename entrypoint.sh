#!/bin/sh
set -e
exec python sabc/manage.py runserver 0.0.0.0:8000
# python sabc/manage.py makemigrations --noinput && python sabc/manage.py migrate --noinput &&
